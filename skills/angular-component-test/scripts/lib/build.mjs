// Build a component test page: copy the suite, AOT-compile it with the Angular project's ngc, bundle the output with the project's esbuild.
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync, symlinkSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const SUITE_LIMIT = 2 * 1024 * 1024;
const SKIP = new Set(['node_modules', '.git', '.DS_Store']);
export const PROJECT_ALIAS = '@project/*';
export const HARNESS_MODULE = '@component-test/harness';

/** Copy suite sources into the work folder and return each file with its SHA-256 for the report. */
export function copySuite(suite, target, hash) {
  const files = [];
  let bytes = 0;
  const visit = (dir, rel) => {
    for (const name of readdirSync(dir).sort()) {
      if (SKIP.has(name)) continue;
      const full = path.join(dir, name), info = statSync(full), next = rel ? `${rel}/${name}` : name;
      if (info.isDirectory()) { visit(full, next); continue; }
      bytes += info.size;
      if (bytes > SUITE_LIMIT) throw new Error(`suite 超過 ${SUITE_LIMIT} bytes`);
      files.push({ name: next, sha256: hash(readFileSync(full)) });
    }
  };
  visit(suite, '');
  cpSync(suite, target, { recursive: true, filter: source => !SKIP.has(path.basename(source)) });
  return files;
}

/** Read the project tsconfig through the project's TypeScript and return its path aliases with absolute targets. */
export function projectPaths(project, tsconfig) {
  const ts = createRequire(path.join(project, 'package.json'))('typescript');
  const parsed = ts.getParsedCommandLineOfConfigFile(tsconfig, {}, { ...ts.sys, onUnRecoverableConfigFileDiagnostic: diagnostic => {
    throw new Error(ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n'));
  } });
  const base = parsed.options.baseUrl ?? parsed.options.pathsBasePath ?? path.dirname(tsconfig);
  const paths = Object.fromEntries(Object.entries(parsed.options.paths ?? {}).map(([key, targets]) => [key, targets.map(target => path.resolve(base, target))]));
  return { paths };
}

/** Match a module specifier against path aliases, returning candidate source files in alias order. */
export function aliasTargets(paths, specifier) {
  for (const [key, targets] of Object.entries(paths)) {
    if (!key.includes('*')) { if (key === specifier) return targets; continue; }
    const [head, tail] = key.split('*');
    if (specifier.startsWith(head) && specifier.endsWith(tail) && specifier.length >= head.length + tail.length) {
      const middle = specifier.slice(head.length, specifier.length - tail.length);
      return targets.map(target => target.replace('*', middle));
    }
  }
  return null;
}

/** Map a source path to its emitted file under the AOT output folder. */
export function emitted(out, source) {
  const full = path.resolve(source), root = path.parse(full).root;
  const relative = path.relative(root, full.replace(/\.(ts|tsx|mts)$/, ''));
  for (const candidate of [`${relative}.js`, path.join(relative, 'index.js')]) {
    const file = path.join(out, candidate);
    if (existsSync(file)) return file;
  }
  return null;
}

/** The project's own esbuild, or the copy its Angular builder depends on when a strict package manager does not hoist it. */
export function loadEsbuild(project) {
  const requireProject = createRequire(path.join(project, 'package.json'));
  for (const owner of [null, '@angular/build', '@angular-devkit/build-angular']) {
    try {
      return owner ? createRequire(requireProject.resolve(`${owner}/package.json`))('esbuild') : requireProject('esbuild');
    } catch { /* try the next owner */ }
  }
  throw new Error('找不到 esbuild, Angular 專案需要安裝 esbuild、@angular/build 或 @angular-devkit/build-angular');
}

/** Write main.ts and tsconfig.json, compile with ngc and bundle; throws with compiler output on failure. */
export async function buildPage({ project, tsconfig, work, entry, harness }) {
  const out = path.join(work, 'out');
  const roots = new Set([work, project].map(dir => path.parse(path.resolve(dir)).root));
  if (roots.size > 1) throw new Error('工作資料夾與 --project 必須在同一個磁碟');
  const esbuild = loadEsbuild(project);
  symlinkSync(path.join(project, 'node_modules'), path.join(work, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
  const zone = existsSync(path.join(project, 'node_modules/zone.js/package.json'));
  const main = path.join(work, 'main.ts');
  writeFileSync(main, [
    ...(zone ? ["import 'zone.js';"] : []),
    "import '@angular/compiler';",
    `import './suite/${entry.replace(/\.ts$/, '')}';`,
    '',
  ].join('\n'));
  const aliases = projectPaths(project, tsconfig);
  const paths = { ...aliases.paths, [PROJECT_ALIAS]: [path.join(project, '*')], [HARNESS_MODULE]: [path.join(harness, 'index.ts')] };
  const config = path.join(work, 'tsconfig.json');
  writeFileSync(config, JSON.stringify({
    extends: tsconfig,
    /** Alias targets are absolute, so no baseUrl is written; TypeScript 6 rejects a new one and a project baseUrl is inherited. */
    compilerOptions: { outDir: out, rootDir: path.parse(work).root, paths, types: [], declaration: false, sourceMap: false, noEmitOnError: true },
    files: [main],
    include: [path.join(path.dirname(tsconfig), 'src/**/*.d.ts')],
    angularCompilerOptions: { compilationMode: 'full' },
  }, null, 2));
  const requireProject = createRequire(path.join(project, 'package.json'));
  const compilerCli = path.dirname(requireProject.resolve('@angular/compiler-cli/package.json'));
  const ngc = path.join(compilerCli, JSON.parse(readFileSync(path.join(compilerCli, 'package.json'), 'utf8')).bin.ngc);
  const compiled = spawnSync(process.execPath, [ngc, '-p', config], { cwd: work, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024, timeout: 600000 });
  if (compiled.status !== 0) throw new Error(`ngc 編譯失敗\n${`${compiled.stdout ?? ''}${compiled.stderr ?? ''}${compiled.error?.message ?? ''}`.trim().slice(0, 8000)}`);
  const bundle = path.join(work, 'bundle.js');
  const result = await esbuild.build({
    entryPoints: [emitted(out, main)], bundle: true, platform: 'browser', format: 'iife', outfile: bundle,
    define: { global: 'globalThis' }, nodePaths: [path.join(project, 'node_modules')], logLevel: 'silent', metafile: true,
    plugins: [{ name: 'aot-output', setup(build) {
      const resolve = sources => {
        for (const source of sources) {
          const file = emitted(out, source);
          if (file) return { path: file };
        }
        return null;
      };
      /** Aliases and absolute imports point at AOT output so no uncompiled TypeScript source is bundled. */
      build.onResolve({ filter: /^[^./]/ }, args => {
        const targets = aliasTargets(paths, args.path);
        if (!targets) return null;
        /** A JavaScript alias target has no AOT output and is bundled as is; anything else falls back to node_modules. */
        return resolve(targets) ?? targets.filter(target => /\.(c|m)?js$/.test(target) && existsSync(target)).map(target => ({ path: target }))[0] ?? null;
      });
      build.onResolve({ filter: /^(\/|[A-Za-z]:[\\/])/ }, args => {
        if (path.resolve(args.path).startsWith(out + path.sep)) return null;
        return resolve([args.path]) ?? { errors: [{ text: `找不到 ${args.path} 的 AOT 產物` }] };
      });
    } }],
  });
  const sources = Object.keys(result.metafile.inputs).filter(file => /\.tsx?$/.test(file) && !file.endsWith('.d.ts'));
  if (sources.length) throw new Error(`打包含有未經 AOT 編譯的原始碼: ${sources.slice(0, 5).join(', ')}`);
  const page = path.join(work, 'index.html');
  writeFileSync(page, '<!doctype html><html><head><meta charset="utf-8"></head><body><script src="bundle.js"></script></body></html>');
  mkdirSync(path.join(work, 'profile'), { recursive: true });
  return { page, bundle };
}
