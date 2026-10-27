#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');

const help = `Check explicit public visibility in selected TypeScript files without edits.
Usage: node check_conventions.cjs --explicit-public [--project PATH] [--typescript FILE] FILE...
Use only when explicit public is an applicable project convention.
Requires the project's existing TypeScript; no dependencies are installed.
Exit: 0 = no findings, 1 = convention findings, 2 = input/parser/runtime failure.
Directories are rejected; pass the reviewed file set, including models and helpers.
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

function main(argv) {
  if (argv.includes('--help') || argv.includes('-h')) { process.stdout.write(help); return 0; }
  const options = { files: [], explicitPublic: false };
  for (let index = 0; index < argv.length; index++) {
    const argument = argv[index];
    if (argument === '--explicit-public') options.explicitPublic = true;
    else if (argument === '--project' || argument === '--typescript') {
      const value = argv[++index];
      if (!value || value.startsWith('--')) throw new Error('Missing value for ' + argument);
      options[argument.slice(2)] = value;
    } else if (argument.startsWith('-')) throw new Error('Unknown option: ' + argument);
    else options.files.push(argument);
  }
  if (!options.explicitPublic || !options.files.length) throw new Error('Specify --explicit-public and reviewed TypeScript files');
  const ts = loadTypeScript(options);
  const findings = [];
  for (const filename of options.files) {
    const absolute = path.resolve(filename);
    if (!/\.[cm]?tsx?$/.test(filename) || !fs.statSync(absolute).isFile()) throw new Error('Expected a TypeScript file: ' + filename);
    findings.push(...checkSource(ts, fs.readFileSync(absolute, 'utf8'), absolute));
  }
  process.stdout.write(JSON.stringify({ status: findings.length ? 'findings' : 'pass', files: options.files.length,
    typescript: ts.version, findings }, null, 2) + '\n');
  return findings.length ? 1 : 0;
}

module.exports = { loadTypeScript, checkSource, main };
if (require.main === module) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(error.message + '\n'); process.exitCode = 2; }
}
