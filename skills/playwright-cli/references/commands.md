# CLI commands and evidence

Resolve a real installed `playwright-cli` executable. On Windows, a setup-managed npm prefix contains `playwright-cli.cmd`; if PATH does not resolve it, call that verified absolute path rather than invoking an unpinned download. The setup checker also looks in its managed prefix. Keep package versions and installation recipes in the maintained setup catalog.

The examples use `ui-check-unique` as a placeholder: replace it with this task's unique session name and keep the same working directory. Replace the URL with the approved target and refs with those read from its snapshot.

```text
playwright-cli --version
playwright-cli --help open
playwright-cli -s=ui-check-unique open http://127.0.0.1:3000 --browser=msedge
playwright-cli -s=ui-check-unique snapshot --filename=before.yaml
```

Read `before.yaml` before selecting an element. For an observed textbox and button:

```text
playwright-cli -s=ui-check-unique fill e4 "Example message"
playwright-cli -s=ui-check-unique snapshot --filename=filled.yaml
playwright-cli -s=ui-check-unique click e5
playwright-cli -s=ui-check-unique snapshot --filename=after.yaml
playwright-cli -s=ui-check-unique console warning
playwright-cli -s=ui-check-unique requests
playwright-cli -s=ui-check-unique screenshot --filename=after.png
playwright-cli -s=ui-check-unique close
```

Read every relevant output and the saved snapshot/image; change the next action when observations require it. If `requests` is absent in an older installation, inspect its help for the corresponding command instead of substituting a guessed flag. Request details may contain credentials and private bodies; inspect only the request needed for verification and redact before sharing.

## Choose evidence for the acceptance criterion

| Need | Evidence |
| --- | --- |
| A button or validation state changed | Fresh snapshot plus affected visible/keyboard behavior |
| Layout or focus is wrong | Screenshot plus relevant DOM and interaction observation |
| UI serializes or submits data | Relevant request status/body and response, then resulting UI |
| A browser error is suspected | Console error, request failure and the triggering action |
| A performance regression is suspected | Supported trace/measurement at the same route/state, beyond a screenshot |

CLI browser actions may succeed while navigation, script execution or requests fail. Separate CLI transport failure, application behavior, mock data and environment errors. Retain the originating command's exit code alongside observed page errors.

## Recovery and optional capabilities

- If a reference becomes stale, take a fresh snapshot and read it. If the named session is unavailable, check the original launch result and the same workspace's session state before reopening it.
- If a browser is missing, check `open --help` and existing channels. Browser installation is an explicit setup action; a CLI installation does not establish browser availability.
- For a supported project test attachment, verify the local Playwright version and debug help first, keep the test process alive while interacting, and read its final result. A saved login state is different from the running test's fixtures, mocks and debugger state.
- Persistent profiles, `state-save` and detailed network artifacts can contain credentials. Save only within the authorized local scope and do not add them to Git.
- Use `close-all`, `kill-all`, deletion or shared daemon cleanup only when that wider scope has been explicitly authorized. Named-session cleanup preserves concurrent work.

Official references: [CLI and sessions](https://github.com/microsoft/playwright-cli), [upstream Skill](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/SKILL.md)
