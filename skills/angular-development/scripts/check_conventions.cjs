#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');

const help = `Check explicit public visibility in selected TypeScript files without edits.
Usage: node check_conventions.cjs --explicit-public [--project PATH] [--typescript FILE] FILE...
Use only when explicit public is an applicable project convention.
Requires the project's existing TypeScript; no dependencies are installed.
Exit: 0 = no findings, 1 = convention findings, 2 = input/parser/runtime failure.
Directories are rejected for explicit files. For scoped Git discovery use:
  --git-root PATH --scope RELATIVE_PATH [--staged] [--unstaged] [--untracked]
Git modes are opt-in and check current working-tree bytes, not index blobs.
Optional --format checks TypeScript defaults with --indent-size N --semicolons insert|remove|ignore.
Use --report FILE to write a separate JSON evidence file (never a source file).
Checks remain read-only; member ordering and type/template checks are not inferred.
`;

function loadTypeScript({ project = process.cwd(), typescript } = {}) {
  return typescript
    ? require(path.resolve(typescript))
    : createRequire(path.join(path.resolve(project), 'package.json'))('typescript');
}

function checkSource(ts, text, filename) {
  const source = ts.createSourceFile(filename, text, ts.ScriptTarget.Latest, true);
  if (source.parseDiagnostics.length) {
    throw new Error(filename + ': ' + ts.flattenDiagnosticMessageText(source.parseDiagnostics[0].messageText, '\n'));
  }
  if (source.isDeclarationFile) return [];
  const findings = [];
  const access = new Set([ts.SyntaxKind.PublicKeyword, ts.SyntaxKind.PrivateKeyword, ts.SyntaxKind.ProtectedKeyword]);
  const hasAccess = node => node.modifiers?.some(modifier => access.has(modifier.kind));
  const record = (node, kind) => {
    if (hasAccess(node) || (node.name && ts.isPrivateIdentifier(node.name))) return;
    const position = (node.name || node).getStart(source);
    const { line, character } = source.getLineAndCharacterOfPosition(position);
    findings.push({ file: filename, line: line + 1, column: character + 1, kind,
      name: node.name?.getText(source) || 'constructor' });
  };
  const visit = node => {
    if (ts.isClassDeclaration(node) || ts.isClassExpression(node)) {
      for (const member of node.members) {
        if (ts.isConstructorDeclaration(member)) {
          record(member, 'constructor');
          for (const parameter of member.parameters) {
            if (ts.isParameterPropertyDeclaration(parameter, member)) record(parameter, 'parameter-property');
          }
        } else if (ts.isPropertyDeclaration(member) || ts.isMethodDeclaration(member)
          || ts.isGetAccessorDeclaration(member) || ts.isSetAccessorDeclaration(member)) {
          record(member, 'member');
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return findings;
}

function gitFiles(options) {
  const root = fs.realpathSync(path.resolve(options.gitRoot));
  const scope = options.scope;
  if (!scope || path.isAbsolute(scope) || scope.split(/[\\/]/).includes('..') || scope.startsWith(':'))
    throw new Error('Specify a literal repository-relative --scope');
  const git = args => execFileSync('git', ['-C', root, '--literal-pathspecs', ...args], { encoding: 'utf8' });
  if (fs.realpathSync(git(['rev-parse', '--show-toplevel']).trim()) !== root)
    throw new Error('--git-root must be the repository root');
  const selected = [];
  const add = args => selected.push(...git(args).split('\0').filter(Boolean));
  if (options.staged) add(['diff', '--cached', '--name-only', '-z', '--diff-filter=ACMRT', '--', scope]);
  if (options.unstaged) add(['diff', '--name-only', '-z', '--diff-filter=ACMRT', '--', scope]);
  if (options.untracked) add(['ls-files', '--others', '--exclude-standard', '-z', '--', scope]);
  return [...new Set(selected)].sort().map(file => path.join(root, file));
}

function formatSource(ts, text, filename, options) {
  const newline = text.includes('\r\n') ? '\r\n' : '\n';
  const settings = { ...ts.getDefaultFormatCodeSettings(newline), indentSize: options.indentSize,
    tabSize: options.indentSize, convertTabsToSpaces: true, newLineCharacter: newline,
    semicolons: options.semicolons };
  const host = { getCompilationSettings: () => ({}), getScriptFileNames: () => [filename],
    getScriptVersion: () => '0', getScriptSnapshot: name => name === filename ? ts.ScriptSnapshot.fromString(text) : undefined,
    getCurrentDirectory: () => path.dirname(filename), getDefaultLibFileName: () => '',
    fileExists: () => false, readFile: () => undefined };
  const service = ts.createLanguageService(host);
  try {
    return service.getFormattingEditsForDocument(filename, settings).map((edit, index) => ({ edit, index }))
      .sort((a, b) => b.edit.span.start - a.edit.span.start || b.index - a.index)
      .reduce((value, { edit }) => value.slice(0, edit.span.start) + edit.newText + value.slice(edit.span.start + edit.span.length), text);
  } finally { service.dispose(); }
}

function main(argv) {
  if (argv.includes('--help') || argv.includes('-h')) { process.stdout.write(help); return 0; }
  const options = { files: [], explicitPublic: false };
  const flags = { '--explicit-public': 'explicitPublic', '--format': 'format', '--staged': 'staged', '--unstaged': 'unstaged', '--untracked': 'untracked' };
  const values = { '--project': 'project', '--typescript': 'typescript', '--git-root': 'gitRoot', '--scope': 'scope', '--report': 'report', '--indent-size': 'indentSize', '--semicolons': 'semicolons' };
  for (let index = 0; index < argv.length; index++) {
    const argument = argv[index];
    if (flags[argument]) options[flags[argument]] = true;
    else if (values[argument]) {
      const value = argv[++index];
      if (!value || value.startsWith('--')) throw new Error('Missing value for ' + argument);
      options[values[argument]] = value;
    } else if (argument.startsWith('-')) throw new Error('Unknown option: ' + argument);
    else options.files.push(argument);
  }
  if (!options.explicitPublic && !options.format) throw new Error('Specify an applicable --explicit-public or --format check');
  const gitMode = options.staged || options.unstaged || options.untracked;
  if ((options.gitRoot || options.scope || gitMode) && !(options.gitRoot && options.scope && gitMode))
    throw new Error('Git selection requires --git-root, --scope and at least one Git mode');
  if (gitMode && options.files.length) throw new Error('Use explicit files or Git discovery, not both');
  if (!gitMode && !options.files.length) throw new Error('Specify reviewed TypeScript files');
  if (options.format) {
    options.indentSize = Number(options.indentSize);
    if (!Number.isSafeInteger(options.indentSize) || options.indentSize < 1 || !['insert', 'remove', 'ignore'].includes(options.semicolons))
      throw new Error('Formatting requires --indent-size N and --semicolons insert|remove|ignore');
  }
  const selected = gitMode ? gitFiles(options) : options.files.map(file => path.resolve(file));
  const skipped = [], files = [];
  for (const file of selected) {
    if (!/\.[cm]?tsx?$/.test(file)) {
      if (!gitMode) throw new Error('Expected a TypeScript file: ' + file);
      skipped.push({ file, reason: 'unsupported-extension' }); continue;
    }
    if (!fs.existsSync(file) && gitMode) { skipped.push({ file, reason: 'absent-working-tree-file' }); continue; }
    if (!fs.statSync(file).isFile()) throw new Error('Expected a TypeScript file: ' + file);
    const real = fs.realpathSync(file);
    if (gitMode) {
      const relative = path.relative(fs.realpathSync(options.gitRoot), real);
      if (relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)) throw new Error('Selected file escapes Git root');
    }
    if (!files.includes(real)) files.push(real);
  }
  if (options.report) {
    const report = path.resolve(options.report);
    if (!/\.json$/i.test(report) || fs.existsSync(report) || files.includes(report)) throw new Error('Report must be a new separate .json file');
  }
  const ts = loadTypeScript(options), findings = [], formatting = [], inputs = [];
  for (const file of files) {
    const bytes = fs.readFileSync(file), text = bytes.toString('utf8');
    const visibility = checkSource(ts, text, file); // Includes syntax validation even for format-only checks
    if (options.explicitPublic) findings.push(...visibility);
    if (options.format && formatSource(ts, text, file, options) !== text) formatting.push({ file });
    inputs.push({ file, sha256: createHash('sha256').update(bytes).digest('hex') });
  }
  const failed = findings.length || formatting.length;
  const result = { status: files.length ? (failed ? 'findings' : 'pass') : 'no-files', files: files.length,
    typescript: ts.version, findings, formatting, inputs, skipped,
    selection: { mode: gitMode ? 'git' : 'explicit', scope: options.scope || null,
      staged: !!options.staged, unstaged: !!options.unstaged, untracked: !!options.untracked, content: 'working-tree' },
    checks: { syntax: files.length ? 'pass' : 'not-run', explicitPublic: options.explicitPublic && files.length ? (findings.length ? 'findings' : 'pass') : 'not-run',
      formatting: options.format && files.length ? (formatting.length ? 'findings' : 'pass') : 'not-run',
      memberOrder: 'not-run', typeAndTemplate: 'not-run', diffWhitespace: 'not-run' },
    formatOptions: options.format ? { base: 'typescript-defaults', indentSize: options.indentSize, convertTabsToSpaces: true, semicolons: options.semicolons, newline: 'preserve-per-file' } : null };
  const json = JSON.stringify(result, null, 2) + '\n';
  if (options.report) fs.writeFileSync(path.resolve(options.report), json, { flag: 'wx' });
  process.stdout.write(json);
  return failed ? 1 : 0;
}

module.exports = { loadTypeScript, checkSource, gitFiles, formatSource, main };

if (require.main === module) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(error.message + '\n'); process.exitCode = 2; }
}
