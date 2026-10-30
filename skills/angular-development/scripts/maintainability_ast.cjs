'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { loadTypeScript, checkSource, formatSource } = require('./check_conventions.cjs');

async function analyze(input) {
  const rows = [], files = new Map(), root = fs.realpathSync(input.root);
  const relative = file => path.relative(root, file).split(path.sep).join('/');
  const emit = (ruleId, status, file, node, evidence, verification, method = 'TypeScript AST', severity = 'info') => {
    const source = files.get(file);
    const line = node && source ? source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1 : null;
    rows.push({ ruleId, status, severity, confidence: status === 'WARN' || status === 'MANUAL' ? 'candidate' : 'high',
      scope: 'selected-files', depth: input.depth, path: file ? relative(file) : null, line,
      method, evidence, sourceVersion: ts ? 'TypeScript ' + ts.version : 'maintenance 0.1.0',
      impact: status === 'WARN' ? 'Review candidate; no measured behavior or performance claim' : 'Bounded check only',
      verification, autoFix: false });
  };
  let ts;
  try {
    ts = loadTypeScript({ typescript: input.typescript });
    const major = Number(ts.version.split('.')[0]);
    if (major < 4 || major > 6 || typeof ts.createProgram !== 'function') throw new Error('Unsupported API');
  } catch {
    emit('TOOL.TYPESCRIPT', 'ERROR', null, null, 'Compatible installed TypeScript 4.x-6.x JS API unavailable', 'Supply approved compatible dependency', 'dependency loader', 'error');
  }
  const typescriptFiles = input.files.filter(f => /\.[cm]?tsx?$/.test(f));
  for (const file of typescriptFiles) {
    if (!ts) { emit('TS.SYNTAX', 'SKIP', file, null, 'Blocked by TOOL.TYPESCRIPT', 'Restore dependency'); continue; }
    try {
      const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true);
      files.set(file, source);
      if (source.parseDiagnostics.length) {
        emit('TS.SYNTAX', 'FAIL', file, null, 'Parser diagnostic codes: ' + source.parseDiagnostics.map(d => d.code).join(','), 'Review syntax against exact file hash', 'TypeScript parser', 'error');
        continue;
      }
      emit('TS.SYNTAX', 'PASS', file, null, 'Parsed selected bytes', 'Does not establish type/template correctness');
      if (source.isDeclarationFile) { emit('TS.DECLARATION', 'SKIP', file, null, 'Declaration-only file', 'Retain public API ownership'); continue; }
      const imports = new Map();
      for (const statement of source.statements) {
        if (!ts.isImportDeclaration(statement)) continue;
        const key = statement.moduleSpecifier.text;
        if (imports.has(key)) emit('IMPORT.DUPLICATE', 'WARN', file, statement, 'Multiple import declarations from one module', 'Check side effects, type/value split and import attributes before merging');
        imports.set(key, true);
      }
      if (input.profile.explicitPublic) {
        const findings = checkSource(ts, source.text, file);
        for (const finding of findings) {
          emit('MEMBER.VISIBILITY', 'FAIL', file, null, 'Explicit project convention missing on ' + finding.kind, 'Review access modifier without reordering initialization', 'existing check_conventions', 'warning');
          rows.at(-1).line = finding.line;
        }
        if (!findings.length) emit('MEMBER.VISIBILITY', 'PASS', file, null, 'Explicit profile convention satisfied', 'No member-order inference', 'existing check_conventions');
      }
      if (input.profile.format) {
        const different = formatSource(ts, source.text, file, input.profile.format) !== source.text;
        emit('FORMAT.EFFECTIVE', different ? 'WARN' : 'PASS', file, null, different ? 'Formatter changes bytes' : 'Formatter result equals input; no-op edits ignored', 'Use the same reviewed settings; no edits applied', 'existing TypeScript formatter');
      }
      const visit = node => {
        if (node.kind === ts.SyntaxKind.AnyKeyword) emit('TYPE.EXPLICIT_ANY', 'WARN', file, node, 'Explicit any type node', 'Check boundary origin and compatible narrowing');
        if (ts.isAsExpression(node) || ts.isTypeAssertionExpression(node) || ts.isNonNullExpression(node))
          emit('TYPE.ASSERTION', 'WARN', file, node, 'Assertion node (including legitimate const assertions)', 'Retain const assertions and proven invariants; verify unsafe narrowing separately');
        if (ts.isTypeReferenceNode(node) && ts.isIdentifier(node.typeName) && node.typeName.text === 'Record')
          emit('TYPE.RECORD', 'MANUAL', file, node, 'Record type reference', 'Distinguish fixed union keys, dynamic dictionary and external unknown input');
        if (ts.isMethodDeclaration(node) && node.body?.statements.length === 1) {
          const statement = node.body.statements[0];
          const expression = ts.isReturnStatement(statement) || ts.isExpressionStatement(statement) ? statement.expression : null;
          if (expression && ts.isCallExpression(expression)) emit('CHAIN.FORWARD', 'WARN', file, node, 'Single-call method body', 'Trace callers, public API, receiver, cancellation, validation and errors; no fixed-depth limit');
        }
        if (ts.isCallExpression(node)) {
          const callee = node.expression;
          const name = ts.isPropertyAccessExpression(callee) ? callee.name.text : ts.isIdentifier(callee) ? callee.text : '';
          if (['subscribe', 'effect', 'addEventListener'].includes(name))
            emit('ASYNC.LIFETIME', 'WARN', file, node, 'Subscription/effect/event API-shaped call', 'Resolve actual symbol, teardown, cancellation, stale response and loading paths');
          if (['patchValue', 'reset', 'getRawValue', 'setValue', 'disable', 'enable'].includes(name))
            emit('FORM.STATE', 'MANUAL', file, node, 'Form-state API-shaped call', 'Resolve symbol and owner; compare disabled projection, emitEvent, dirty/save/submit/corrected states');
          if (['bypassSecurityTrustHtml', 'bypassSecurityTrustUrl', 'bypassSecurityTrustResourceUrl', 'eval', 'exec', 'execSync', 'spawn', 'fetch'].includes(name))
            emit('SECURITY.SINK', 'WARN', file, node, 'Security-sensitive API-shaped call; not a vulnerability finding', 'Use existing security owner for symbol/source-to-sink validation, authorization and external-transfer review');
        }
        ts.forEachChild(node, visit);
      };
      visit(source);
    } catch {
      emit('TOOL.FILE', 'ERROR', file, null, 'File analysis failed; source text and raw exception withheld', 'Inspect dependency compatibility and local file', 'file boundary', 'error');
    }
  }
  if (ts && input.depth !== 'static' && typescriptFiles.length) {
    try {
      const converted = ts.convertCompilerOptionsFromJson(input.profile.compilerOptions || {}, root);
      if (converted.errors.length) throw new Error('Invalid compiler options');
      const allowed = new Set([...typescriptFiles, ...input.dependencies].map(f => fs.realpathSync(f)));
      const libRoot = path.dirname(fs.realpathSync(input.typescript));
      const options = { ...converted.options, noEmit: true, incremental: false, composite: false,
        noUnusedLocals: true, noUnusedParameters: true, noImplicitAny: true, types: [] };
      const host = ts.createCompilerHost(options), originalRead = host.readFile, originalExists = host.fileExists;
      const permitted = name => {
        try {
          const real = fs.realpathSync(name);
          return allowed.has(real) || (path.dirname(real) === libRoot && /^lib\..*\.d\.ts$/.test(path.basename(real)));
        } catch { return false; }
      };
      host.fileExists = name => permitted(name) && originalExists(name);
      host.readFile = name => permitted(name) ? originalRead(name) : undefined;
      host.writeFile = () => { throw new Error('Read-only'); };
      const program = ts.createProgram([...allowed], options, host);
      const checker = program.getTypeChecker();
      const edges = new Map();
      for (const file of typescriptFiles) {
        const source = program.getSourceFile(file);
        const targets = [];
        for (const statement of source?.statements || []) {
          if (!(ts.isImportDeclaration(statement) || ts.isExportDeclaration(statement)) || !statement.moduleSpecifier) continue;
          const resolved = ts.resolveModuleName(statement.moduleSpecifier.text, file, options, host).resolvedModule;
          const target = resolved ? fs.realpathSync(resolved.resolvedFileName) : null;
          if (target && input.files.includes(target)) targets.push(target);
        }
        edges.set(file, targets);
      }
      const active = new Set(), visited = new Set();
      const trace = file => {
        if (active.has(file)) {
          emit('IMPORT.CYCLE', 'WARN', file, null, 'Cycle in selected import/export graph, including type edges',
            'Distinguish type-only/barrel edges and runtime initialization; dependencies outside selection remain uncovered', 'bounded module resolver');
          return;
        }
        if (visited.has(file)) return;
        active.add(file);
        for (const target of edges.get(file) || []) trace(target);
        active.delete(file); visited.add(file);
      };
      for (const file of edges.keys()) trace(file);
      const diagnostics = [...program.getOptionsDiagnostics(), ...program.getGlobalDiagnostics(), ...program.getSyntacticDiagnostics(), ...program.getSemanticDiagnostics()];
      const unresolved = diagnostics.some(d => [2307, 2688, 6053, 2318].includes(d.code));
      emit('TYPE.COVERAGE', unresolved ? 'SKIP' : 'PASS', null, null,
        unresolved ? 'Missing approved dependencies; semantic coverage incomplete' : 'Bounded compiler context resolved',
        'Only explicit files/dependencies and TypeScript standard libraries are read; Angular template types are separate', 'bounded compiler host');
      for (const diagnostic of diagnostics) {
        const file = diagnostic.file ? fs.realpathSync(diagnostic.file.fileName) : null;
        if (file && !input.files.includes(file)) continue;
        const unused = [6133, 6192, 6196].includes(diagnostic.code);
        emit(unused ? 'IMPORT.UNUSED_CANDIDATE' : 'TYPE.DIAGNOSTIC', unused ? 'WARN' : unresolved ? 'MANUAL' : 'FAIL', file || null, null,
          'Compiler diagnostic TS' + diagnostic.code + '; message withheld to avoid source/literal disclosure',
          unused ? 'Verify template/decorator/dynamic/public consumers before removal; not necessarily an import' : 'Review diagnostic in original project context', 'TypeScript compiler', unused ? 'warning' : 'error');
        if (file && diagnostic.start !== undefined) rows.at(-1).line = diagnostic.file.getLineAndCharacterOfPosition(diagnostic.start).line + 1;
      }
      for (const file of typescriptFiles) {
        const source = program.getSourceFile(file);
        if (!source || source.parseDiagnostics.length) continue;
        const visit = node => {
          if (ts.isElementAccessExpression(node) && node.argumentExpression && ts.isStringLiteral(node.argumentExpression)) {
            const key = node.argumentExpression.text;
            const type = checker.getTypeAtLocation(node.expression);
            const declared = !(type.flags & (ts.TypeFlags.Any | ts.TypeFlags.Unknown)) && checker.getPropertyOfType(type, key);
            if (declared && /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(key)) emit('TYPE.DOT_CANDIDATE', 'WARN', file, node,
              'String key has a declared property in current compiler context', 'Confirm noPropertyAccessFromIndexSignature, API mapping and receiver semantics; numeric/dynamic/index-only keys excluded', 'TypeScript type checker');
          }
          if ((ts.isParameter(node) || ts.isVariableDeclaration(node) || ts.isPropertyDeclaration(node)) && !node.type
              && (checker.getTypeAtLocation(node).flags & ts.TypeFlags.Any))
            emit('TYPE.INFERRED_ANY', 'WARN', file, node, 'Declaration infers any in bounded context', 'Resolve dependency errors and contextual types before changing annotation', 'TypeScript type checker');
          ts.forEachChild(node, visit);
        };
        visit(source);
      }
    } catch {
      emit('TOOL.SEMANTIC', 'ERROR', null, null, 'Semantic adapter unavailable or invalid compiler options', 'Correct approved inputs; static checks remain independent', 'compiler boundary', 'error');
    }
  } else emit('TYPE.COVERAGE', 'SKIP', null, null, 'Semantic depth not run or no compatible TS input', 'Select semantic depth with explicit dependencies', 'depth selection');

  let angular;
  if (input.angularCompiler) {
    try { angular = await import(pathToFileURL(input.angularCompiler).href); }
    catch { emit('TOOL.ANGULAR', 'ERROR', null, null, 'Angular parser load failed', 'Use compatible approved compiler entry', 'dependency loader', 'error'); }
  }
  for (const file of input.files.filter(f => f.endsWith('.html'))) {
    if (!angular?.parseTemplate) { emit('HTML.PARSE', 'SKIP', file, null, 'Blocked: approved Angular compiler unavailable', 'Supply parser explicitly; plain text is not template semantics', 'Angular parser'); continue; }
    try {
      const parsed = angular.parseTemplate(fs.readFileSync(file, 'utf8'), relative(file), { preserveWhitespaces: true });
      emit('HTML.PARSE', parsed.errors?.length ? 'FAIL' : 'PASS', file, null, parsed.errors?.length ? 'Template parser errors; source text withheld' : 'Template parsed with Angular ' + angular.VERSION.full,
        'Parsing does not check context/binding types; run project Angular compiler separately', 'Angular template parser');
      if (parsed.errors?.length) continue;
      const seen = new Set();
      const walk = (node, inheritedLine = null) => {
        if (!node || typeof node !== 'object' || seen.has(node)) return;
        seen.add(node);
        const templateLine = node.sourceSpan?.start?.line !== undefined ? node.sourceSpan.start.line + 1 : inheritedLine;
        if (node.constructor?.name === 'Call') {
          const any = node.receiver?.name === '$any';
          emit(any ? 'HTML.ANY' : 'PERF.TEMPLATE_CALL', 'WARN', file, null,
            any ? 'Template $any call' : 'Template call, possibly an event handler or cheap accessor',
            any ? 'Check template context types with project compiler' : 'Classify event vs binding and measure reevaluation before optimization', 'Angular template AST');
          rows.at(-1).line = templateLine;
        }
        for (const [key, value] of Object.entries(node)) {
          if (['sourceSpan', 'nameSpan', 'valueSpan', 'handlerSpan', 'keySpan', 'i18n'].includes(key)) continue;
          if (Array.isArray(value)) value.forEach(child => walk(child, templateLine));
          else if (value && typeof value === 'object') walk(value, templateLine);
        }
      };
      parsed.nodes.forEach(node => walk(node));
    } catch { emit('TOOL.HTML', 'ERROR', file, null, 'Template analysis failed', 'Inspect compatible compiler locally', 'template boundary', 'error'); }
  }
  const manual = {
    'CHAIN.RESPONSIBILITY': 'Trace event/service/request/projection owners, duplicate validation, cycles and type-only/barrel edges; chain depth is not an error',
    'ORPHAN.CONSUMERS': 'Check methods/exports/fields/getters/outputs/components/directives/pipes against HTML, lifecycle, decorators, reflection, dynamic entry and public API; no automatic deletion',
    'MEMBER.ORDER': 'Use applicable member-order owner; preserve constructor parameter properties, initializer and decorator timing',
    'COMMENT.INTENT': 'Check stale/redundant comments and necessary reasons against actual behavior and confirmed sources',
    'NAME.MAPPING': 'Check operation/boolean responsibility and confirmed API mapping; do not infer equivalent fields',
    'TYPE.DESIGN': 'Review unknown narrowing, interface/type structure, union/const/enum and exhaustive branches; compiler absence of errors is insufficient',
    'HTML.RESPONSIBILITY': 'Check typed ng-template context, component/directive responsibility, duplicate conditions and track key/DOM identity with actual Angular compiler',
    'MODAL.LIFECYCLE': 'Compare duplicate dialogs and state owner, close/reopen/reset/pristine/readonly behavior',
    'FACTORY.EQUIVALENCE': 'Compare typed control creation, validators/error keys/defaults and fresh instances; no generic factory engine',
    'FORM.OWNERSHIP': 'Compare state owners, disabled value/getRawValue/payload, messages/triggers and patch/reset/emitEvent',
    'ASYNC.OWNERSHIP': 'Trace subscriptions/effects, duplicate requests, teardown, cancellation/staleness and all loading exits',
    'CSS.CONSUMERS': 'Check dynamic classes, Host, overlays, encapsulation and stylesheet consumers before declaring styles unused',
    'SECURITY.OWNER': 'Reuse existing security scan/validation owner for secrets, path boundaries, data egress, HTML/command input and authorization; candidate detection is not a security audit',
  };
  for (const [id, evidence] of Object.entries(manual)) emit(id, 'MANUAL', null, null, evidence, 'Attach scoped source/evidence and current project decisions', 'review checklist');
  emit('PERF.RUNTIME', 'SKIP', null, null, 'No runtime, browser, network, application command or target code executed',
    'After scoped authorization record environment/versions/data, cold/warm state, samples/baseline, requests, rendering/DOM, subscriptions and bundle measurements', 'runtime boundary');
  if (!input.files.length) emit('SCOPE.EMPTY', 'SKIP', null, null, 'Selection contains no supported files', 'Choose a nonempty explicit scope', 'selection');
  return { results: rows, versions: { typescript: ts?.version || null, angular: angular?.VERSION?.full || null },
    coverage: { selectedFiles: input.files.length, typeScriptFiles: typescriptFiles.length, dependencyFiles: input.dependencies.length,
      templateTypeCheck: false, runtimeExecuted: false, fixesApplied: false, securityAudit: false } };
}
module.exports = { analyze };
if (require.main === module) {
  let data = '';
  process.stdin.setEncoding('utf8'); process.stdin.on('data', chunk => { data += chunk; });
  process.stdin.on('end', async () => {
    try { process.stdout.write(JSON.stringify(await analyze(JSON.parse(data)))); }
    catch { process.stderr.write('Maintenance worker failed\n'); process.exitCode = 2; }
  });
}
