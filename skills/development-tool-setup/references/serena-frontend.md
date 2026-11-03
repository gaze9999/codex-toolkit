# Optional Serena frontend language servers

Read when Serena is selected for frontend symbols/references or its language support needs diagnosis. Resolve the installed Serena version, intended checkout, project configuration, runtime and authorized setup scope first. Ordinary coding and maintenance tasks can use existing compiler APIs, editor navigation or bounded search.

## Choose the language server

Checked 2026-11-03 against Serena 1.7.0's project template and installed language-server enum. Use `language_servers` in the selected project's `.serena/project.yml` or its supported local override, preserving existing project settings.

| Project or files | Selected entry | Prerequisites and scope |
|---|---|---|
| JavaScript / TypeScript, including React JS/TS | `typescript` | Node.js and npm; the same server covers JS and TS |
| Angular TS and templates | `angular` | Experimental; Node.js/npm and project dependencies with resolvable `@angular/core`; replaces overlapping `typescript`/`html` entries |
| Plain HTML | `html` | Experimental; Node.js/npm; in-file symbols, without meaningful cross-file HTML references |
| CSS / SCSS / Sass | `scss` | Experimental; Node.js/npm and some-sass-language-server; one entry covers the three formats |
| Vue 3 with TypeScript | `vue` | Node.js/npm and compatible project dependencies |
| Svelte | `svelte` | Node.js/npm; select its framework adapter for the project |

Minimal JS/TS selection:

```yaml
language_servers: [typescript]
```

For an authorized Angular-and-stylesheet setup, select `angular` and `scss`. In a mixed-language repository, preserve required existing servers and check file precedence; the first matching server handles a file. Select only the languages needed for the question.

## Apply and verify the selected scope

1. Read existing project/local settings and confirm the checkout. Reuse installed compatible dependencies and preserve project compiler versions and lockfiles.
2. Include language-server prerequisites in the approved setup scope before activation: Serena can download managed dependencies on first use. Configuration authorizes neither an unrelated package installation nor a project upgrade.
3. After approved setup, inspect the active project and started language servers, then perform one bounded symbol lookup and, when needed, a reference lookup in the authorized files. Configuration presence, an empty result or another language's readiness does not establish frontend support.
4. If the optional server is unavailable, retain its missing evidence and continue independent local checks. Keep required project gates pending until resolved, preserve client-owned sessions and clean up only owned temporary resources.

Keep the personal connection-prompt override with its private configuration owner; preserve the upstream manual, tools and permissions. Source configuration, installed dependencies, client reload and actual frontend lookup are separate acceptance states.

Sources: [Serena 1.7.0 project template](https://github.com/oraios/serena/blob/v1.7.0/src/serena/resources/project.template.yml), [language support](https://oraios.github.io/serena/01-about/020_programming-languages.html), [configuration](https://oraios.github.io/serena/02-usage/050_configuration.html)
