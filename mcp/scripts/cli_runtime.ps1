function Find-SetupPython([string]$Selected, [string]$ManagedRoot) {
    $candidates = @()
    if ($Selected) { $candidates += $Selected }
    else {
        # Existing manager environments remain compatible CLI runtimes.
        $candidates += Join-Path $env:LOCALAPPDATA 'codex-setup\tools\manager\Scripts\python.exe'
        $packagesRoot = Join-Path $env:LOCALAPPDATA 'Packages'
        if (Test-Path -LiteralPath $packagesRoot) {
            $candidates += @(Get-ChildItem -LiteralPath $packagesRoot -Filter 'OpenAI.Codex_*' -Directory | ForEach-Object {
                Join-Path $_.FullName 'LocalCache\Local\codex-setup\tools\manager\Scripts\python.exe'
            })
        }
        foreach ($name in @('python','python3','py')) {
            $command = Get-Command $name -ErrorAction SilentlyContinue
            if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') { $candidates += $command.Source }
        }
        foreach ($pythonRoot in @((Join-Path $env:LOCALAPPDATA 'Programs\Python'), (Join-Path $ManagedRoot 'python'))) {
            if (Test-Path -LiteralPath $pythonRoot) {
                $candidates += @(Get-ChildItem -LiteralPath $pythonRoot -Directory | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName 'python.exe' })
            }
        }
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $resolved = & $candidate -I -X utf8 -B -c 'import sys, tomllib, ssl; sys.exit(2) if sys.version_info < (3,11) else print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $resolved -and (Test-Path -LiteralPath ([string]$resolved) -PathType Leaf)) { return [string]$resolved }
        } catch { continue }
    }
    return $null
}
