$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$arguments = @($args)
if ($arguments.Count -eq 0 -or $arguments[0] -in @('--help','-h','--list')) {
    Write-Output 'Usage: launch-cli.cmd / launch-cli.ps1 ACTION [OPTIONS]'
    Write-Output '  agents       List governance sources; global / desktop / subagent-profile selects one'
    Write-Output '  skills       List Skills; NAME [--apply] previews or synchronizes one'
    Write-Output '  plugins      List source/configured Plugins; NAME previews mappings; install through Codex'
    Write-Output '  mcp TOOL     Preview one MCP setup, --list shows the catalog'
    Write-Output '  tool TOOL    Preview one native/CLI tool setup'
    Write-Output '  bootstrap    Preview baseline MCP setup'
    Write-Output '  check        Check selected development tools'
    Write-Output '  update       Check or preview one tool update'
    Write-Output '  uninstall    Preview removal of one MCP registration'
    Write-Output '  desktop      Render portable Desktop settings'
    Write-Output '  audit        Audit Skill metadata, references and helpers'
    Write-Output 'Run ACTION --help for Python commands, or see docs/setup/cli.md'
    exit 0
}
$action = [string]$arguments[0]
$forward = @($arguments | Select-Object -Skip 1)
$bundledPython = Join-Path $PSScriptRoot 'runtime/python.exe'
$selectedPython = if (Test-Path -LiteralPath $bundledPython -PathType Leaf) { $bundledPython } else { $env:CODEX_SETUP_PYTHON }
$launchers = @{ mcp='install-mcp.ps1'; tool='install-development-tool.ps1'; uninstall='uninstall-mcp.ps1' }
if ($launchers.ContainsKey($action) -and $forward -notcontains '--help' -and $forward -notcontains '-h') {
    if ($action -in @('mcp','tool') -and $selectedPython -and $forward -notcontains '--python' -and $forward -notcontains '-Python') {
        $forward += @('--python',$selectedPython)
    }
    if ($action -eq 'tool') {
        $normalized = @($forward | ForEach-Object { if ($_ -like '--*') { '-' + ([string]$_).Substring(2).Replace('-','') } else { $_ } })
        & (Get-Process -Id $PID).Path -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File (Join-Path $PSScriptRoot 'mcp/scripts/launch/install-development-tool.ps1') @normalized
        exit $LASTEXITCODE
    }
    & (Join-Path $PSScriptRoot ('mcp/scripts/launch/'+$launchers[$action])) @forward
    exit $LASTEXITCODE
}
$scripts = @{ mcp='install_development_tool.py'; tool='install_development_tool.py'; uninstall='uninstall_mcp.py'; bootstrap='bootstrap_mcp.py'; check='check_development_tools.py'; update='update_development_tool.py'; agents='manage_categories.py'; skills='manage_categories.py'; plugins='manage_categories.py'; desktop='render_desktop_settings.py'; audit='audit_skills.py' }
if (-not $scripts.ContainsKey($action)) { [Console]::Error.WriteLine("Unknown action: $action, use --help"); exit 2 }
if ($action -in @('agents','skills','plugins')) { $forward = @($action) + $forward }
try {
    . (Join-Path $PSScriptRoot 'mcp/scripts/cli_runtime.ps1')
    $runtime = Find-SetupPython $selectedPython (Join-Path $env:LOCALAPPDATA 'codex-setup/tools/manager-bootstrap')
    if (-not $runtime) { throw 'Select an existing Python 3.11+ using CODEX_SETUP_PYTHON' }
    & $runtime -X utf8 -B (Join-Path $PSScriptRoot ('mcp/scripts/'+$scripts[$action])) @forward
    exit $LASTEXITCODE
} catch { Write-Error $_; exit 2 }
