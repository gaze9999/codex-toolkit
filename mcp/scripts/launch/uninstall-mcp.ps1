$SetupRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$ErrorActionPreference = 'Stop'
$python = $env:CODEX_SETUP_PYTHON
$arguments = @($args)
$forward = @()
for ($index = 0; $index -lt $arguments.Count; $index++) {
    $value = [string]$arguments[$index]
    if ($value -in @('--python','-Python')) {
        if ($index + 1 -ge $arguments.Count) { throw 'Missing Python path' }
        $index++
        $python = [string]$arguments[$index]
    } else { $forward += $value }
}
$candidates = @()
if ($python) { $candidates += $python }
else {
    foreach ($name in @('python','python3','py')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') { $candidates += $command.Source }
    }
    $pythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    if (Test-Path -LiteralPath $pythonRoot) {
        $candidates += @(Get-ChildItem -LiteralPath $pythonRoot -Filter 'Python3*' -Directory | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName 'python.exe' })
    }
}
$runtime = $null
foreach ($candidate in $candidates | Select-Object -Unique) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    try {
        & $candidate -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $runtime = $candidate; break }
    } catch { continue }
}
if (-not $runtime) { Write-Error 'Select an existing Python 3.11+ using --python or CODEX_SETUP_PYTHON, no packages were installed or removed'; exit 2 }
if ($forward.Count -gt 0 -and -not ([string]$forward[0]).StartsWith('-')) { $forward = @('--tool',$forward[0]) + @($forward | Select-Object -Skip 1) }
if ($forward.Count -eq 0) { $forward = @('--guided') }
& $runtime -B (Join-Path $SetupRoot 'mcp/scripts/uninstall_mcp.py') @forward
exit $LASTEXITCODE
