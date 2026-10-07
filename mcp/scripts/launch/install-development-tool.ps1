param(
    [Parameter(Mandatory = $true)]
    [string]$Tool,
    [ValidateSet('native', 'mcp')]
    [string]$Interface = 'native',
    [switch]$Apply,
    [switch]$Yes,
    [switch]$Guided,
    [Alias('NoPause')]
    [switch]$NoGuide,
    [ValidateSet('auto','zh-TW','en')]
    [string]$Language = 'auto',
    [switch]$Login,
    [switch]$Update,
    [string]$Python,
    [ValidateSet('chromium', 'chrome', 'msedge', 'firefox', 'webkit')]
    [string]$Browser,
    [string]$ServerUrl,
    [string]$TokenEnvVar,
    [string]$McpExecutable,
    [string[]]$ReadRoot,
    [string]$FeedsPath,
    [string]$WheelDir
)
$ErrorActionPreference = 'Stop'
$SetupRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. (Join-Path $SetupRoot 'mcp/scripts/installer_language.ps1')
$ui = New-InstallerUi $SetupRoot $Language
$guideDelegated = $false
try {
    $manifest = Get-Content -LiteralPath (Join-Path $SetupRoot 'mcp/tools/development-tools.requirements.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $spec = $manifest.tools.$Tool
    if (-not $spec) { Write-Error (Get-InstallerText $ui 'Select one tool name from tools/development-tools.requirements.json'); exit 2 }
    if ($Interface -eq 'mcp' -and $spec.interfaces.mcp) {
        $mode = $spec.interfaces.mcp
        $platforms = if ($mode.platforms) { $mode.platforms } else { $spec.platforms }
    } else {
        if ($Interface -eq 'mcp' -and -not $spec.mcp -and -not $spec.manual_setup) { Write-Error (Get-InstallerText $ui 'This tool has no configured MCP interface'); exit 2 }
        $mode = $spec
        $platforms = $spec.platforms
    }
    if ('windows' -notin $platforms) {
        Write-Host (Get-InstallerText $ui '{0} does not support Windows; no runtime or tool was installed' @($Tool))
        exit 2
    }
    if ($mode.manual_setup) {
        Write-Host (Get-InstallerText $ui 'Required setup: {0}' @($mode.manual_setup))
        $requirements = if ($mode.PSObject.Properties['service_requirements']) { $mode.service_requirements } else { $spec.service_requirements }
        $checks = if ($mode.PSObject.Properties['manual_checks']) { $mode.manual_checks } else { $spec.manual_checks }
        foreach ($item in $requirements) { Write-Host (Get-InstallerText $ui 'Service requirement: {0}' @($item)) }
        foreach ($item in $checks) { Write-Host (Get-InstallerText $ui 'Verify: {0}' @($item)) }
        Write-Host (Get-InstallerText $ui 'Setup guide: {0}' @((Join-Path $SetupRoot 'docs\tools\catalog.md')))
        exit 1
    }

    function Find-SetupPython {
        $candidates = @()
        if ($Python) { $candidates += $Python }
        else {
            foreach ($name in @('python', 'python3', 'py')) {
                $command = Get-Command $name -ErrorAction SilentlyContinue
                if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') { $candidates += $command.Source }
            }
            $pythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
            if (Test-Path -LiteralPath $pythonRoot) {
                $candidates += @(Get-ChildItem -LiteralPath $pythonRoot -Filter 'Python3*' -Directory | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName 'python.exe' })
            }
        }
        foreach ($candidate in $candidates | Select-Object -Unique) {
            if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
            try {
                & $candidate -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>$null
                if ($LASTEXITCODE -eq 0) { return $candidate }
            } catch { continue }
        }
        return $null
    }

    $runtime = Find-SetupPython
    if (-not $runtime) {
        if ($Python) { Write-Error (Get-InstallerText $ui 'The selected Python must be a working Python 3.11+ executable'); exit 2 }
        $package = $manifest.python.windows_package
        $bootstrapConfirmed = $false
        Write-Host (Get-InstallerText $ui 'Missing Python 3.11+. Source: {0}; package: {1}; scope: current user; purpose: run the selected {2} installer' @($manifest.python.source, $package, $Tool))
        if ($Guided -and -not $Apply) {
            if ((Read-Host (Get-InstallerText $ui 'Install the listed Python runtime, then preview the selected tool? [y/N]')) -notin @('y', 'yes')) { exit 0 }
            $Apply = $true
            $bootstrapConfirmed = $true
        }
        if (-not $Apply) { Write-Host (Get-InstallerText $ui 'Rerun with -Apply to confirm Python and the selected tool installation'); exit 1 }
        if (-not $Yes -and -not $bootstrapConfirmed -and (Read-Host (Get-InstallerText $ui 'Install Python for this selected tool? [y/N]')) -notin @('y', 'yes')) { exit 0 }
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Write-Error (Get-InstallerText $ui 'WinGet is missing; install Python 3.11+ from the approved Python source first'); exit 2 }
        & winget install --id $package --exact --source winget --scope user --accept-source-agreements --accept-package-agreements --disable-interactivity
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $runtime = Find-SetupPython
        if (-not $runtime) { Write-Error (Get-InstallerText $ui 'Python was installed but is not visible; reopen the terminal and rerun the same selected tool'); exit 2 }
    }
    $toolArgs = @('-B', (Join-Path $SetupRoot 'mcp/scripts/install_development_tool.py'), '--tool', $Tool, '--interface', $Interface, '--lang', $ui.Language)
    if ($Apply) { $toolArgs += '--apply' }
    if ($Yes) { $toolArgs += '--yes' }
    if ($Guided) { $toolArgs += '--guided' }
    if ($NoGuide) { $toolArgs += '--no-guide' }
    if ($Login) { $toolArgs += '--login' }
    if ($Update) { $toolArgs += '--update' }
    if ($Browser) { $toolArgs += @('--browser', $Browser) }
    if ($ServerUrl) { $toolArgs += @('--server-url', $ServerUrl) }
    if ($TokenEnvVar) { $toolArgs += @('--token-env-var', $TokenEnvVar) }
    if ($McpExecutable) { $toolArgs += @('--mcp-executable', $McpExecutable) }
    if ($FeedsPath) { $toolArgs += @('--feeds-path', $FeedsPath) }
    if ($WheelDir) { $toolArgs += @('--wheel-dir', $WheelDir) }
    foreach ($root in $ReadRoot) { $toolArgs += @('--read-root', $root) }
    $guideDelegated = $true
    & $runtime @toolArgs
    exit $LASTEXITCODE
} finally {
    if (-not $guideDelegated -and $Guided -and -not $Yes -and -not $NoGuide -and -not [Console]::IsInputRedirected) {
        Open-InstallerGuide $ui $SetupRoot $Tool
    }
}
