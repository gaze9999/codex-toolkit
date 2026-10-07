$SetupRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$ErrorActionPreference = 'Stop'
# Accept the same long options as the Python/shell entry, plus existing PowerShell names.
$params = @{ Guided = $true }
$noGuide = $false
$profile = 'all'
$list = $false
. (Join-Path $SetupRoot 'mcp/scripts/installer_language.ps1')
$ui = New-InstallerUi $SetupRoot
$aliases = @{ tool='Tool'; python='Python'; profile='Profile'; apply='Apply'; yes='Yes'; login='Login'; list='List'; update='Update'; serverurl='ServerUrl'; tokenenvvar='TokenEnvVar'; mcpexecutable='McpExecutable'; readroot='ReadRoot'; feedspath='FeedsPath'; wheeldir='WheelDir'; nopause='NoGuide'; noguide='NoGuide'; lang='Language'; language='Language' }
$switches = @('Apply','Yes','Login','List','Update','NoGuide')
$arguments = @($args)
for ($index = 0; $index -lt $arguments.Count; $index++) {
    $argument = [string]$arguments[$index]
    if ($argument.StartsWith('-')) {
        $key = $argument.TrimStart('-').Replace('-', '').ToLowerInvariant()
        if (-not $aliases.ContainsKey($key)) { Write-Error (Get-InstallerText $ui 'Unknown option: {0}' @($argument)); exit 2 }
        $name = $aliases[$key]
        if ($name -in $switches) { $value = $true }
        else {
            if ($index + 1 -ge $arguments.Count) { Write-Error (Get-InstallerText $ui 'Missing value: {0}' @($argument)); exit 2 }
            $index++
            $value = [string]$arguments[$index]
        }
        if ($name -eq 'Profile') { $profile = $value }
        elseif ($name -eq 'List') { $list = $true }
        elseif ($name -eq 'NoGuide') { $noGuide = $true; $params.NoGuide = $true }
        elseif ($name -eq 'ReadRoot') { $params[$name] = @($params[$name] | Where-Object { $null -ne $_ }) + @($value) }
        elseif ($params.ContainsKey($name)) { Write-Error (Get-InstallerText $ui 'Repeated option: {0}' @($argument)); exit 2 }
        else { $params[$name] = $value }
    } elseif (-not $params.ContainsKey('Tool')) { $params.Tool = $argument }
    else { Write-Error (Get-InstallerText $ui 'Select exactly one tool'); exit 2 }
}
if ($params.Language) { Set-InstallerLanguage $ui $params.Language }
$manifest = Get-Content -LiteralPath (Join-Path $SetupRoot 'mcp/tools/development-tools.requirements.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$selectedProfile = $manifest.profiles.PSObject.Properties[$profile]
if (-not $selectedProfile) { Write-Error (Get-InstallerText $ui 'Unknown profile: {0}' @($profile)); exit 2 }
$groupsForProfile = @($selectedProfile.Value.groups)
$catalog = @($manifest.tools.PSObject.Properties | Where-Object { $groupsForProfile.Count -eq 0 -or $_.Value.group -in $groupsForProfile })
if ($list) {
    foreach ($entry in $catalog) {
        $title = Get-InstallerLabel $ui 'title' $(if ($entry.Value.title) { $entry.Value.title } else { $entry.Name }) $entry.Name
        Write-Output "$(Get-InstallerLabel $ui 'group' $entry.Value.group) / $($entry.Name) - $title ($($entry.Value.kind))"
    }
    exit 0
}
function Read-MenuChoice([int]$Count, [string]$Prompt, [switch]$LanguageOption, [switch]$Category) {
    while ($true) {
        $selected = Read-Host $Prompt
        if ($LanguageOption -and $selected.Trim().ToLowerInvariant() -eq 'l') { return -1 }
        if (-not $selected -or $Category -and $selected.Trim().ToLowerInvariant() -eq 'q') { return $(if ($Category) { -2 } else { 0 }) }
        if ($selected.Trim() -eq '0') { return 0 }
        $choice = 0
        if ([int]::TryParse($selected, [ref]$choice) -and $choice -ge 1 -and $choice -le $Count) { return $choice }
        Write-Host (Get-InstallerText $ui 'Enter a number from the list')
    }
}
if (-not $params.Tool) {
    if ([Console]::IsInputRedirected) { Write-Error (Get-InstallerText $ui 'Use an interactive terminal or select one tool explicitly'); exit 2 }
    $groups = @($catalog | ForEach-Object { $_.Value.group } | Select-Object -Unique)
    while (-not $params.Tool) {
        Write-Host ("`n" + (Get-InstallerText $ui 'Select a tool category (profile: {0}):' @((Get-InstallerLabel $ui 'profile' $profile))))
        Write-Host ('  0. ' + (Get-InstallerText $ui 'Show all tools in this profile'))
        for ($index = 0; $index -lt $groups.Count; $index++) { Write-Host "  $($index + 1). $(Get-InstallerLabel $ui 'group' $groups[$index])" }
        Write-Host ('  L. ' + (Get-InstallerText $ui 'Language'))
        Write-Host ('  Q. ' + (Get-InstallerText $ui 'Exit'))
        $choice = Read-MenuChoice $groups.Count (Get-InstallerText $ui 'Category number (0 = All, L = Language, Q / Enter = Exit): ') -LanguageOption -Category
        if ($choice -eq -1) {
            Write-Host ('  1. ' + (Get-InstallerLabel $ui 'language' 'zh-TW'))
            Write-Host ('  2. ' + (Get-InstallerLabel $ui 'language' 'en'))
            Write-Host ('  0. ' + (Get-InstallerText $ui 'Back'))
            $languageChoice = Read-MenuChoice 2 (Get-InstallerText $ui 'Language number (0 / Enter = Back): ')
            if ($languageChoice -gt 0) { Set-InstallerLanguage $ui @('zh-TW','en')[$languageChoice - 1] }
            continue
        }
        if ($choice -eq -2) { exit 0 }
        $entries = if ($choice -eq 0) { @($catalog) } else { @($catalog | Where-Object { $_.Value.group -eq $groups[$choice - 1] }) }
        for ($index = 0; $index -lt $entries.Count; $index++) {
            $entry = $entries[$index]
            $title = Get-InstallerLabel $ui 'title' $(if ($entry.Value.title) { $entry.Value.title } else { $entry.Name }) $entry.Name
            $mode = if ($entry.Value.interfaces.mcp) { $entry.Value.interfaces.mcp } else { $entry.Value }
            $platforms = if ($mode.platforms) { $mode.platforms } else { $entry.Value.platforms }
            $state = if ('windows' -notin $platforms) { 'unsupported on Windows' } elseif ($mode.manual_setup) { 'manual setup required' } elseif ($mode.custom_endpoint) { 'server URL required' } else { 'check / install' }
            Write-Host "  $($index + 1). $title [$($entry.Name)] - $(Get-InstallerText $ui $state)"
        }
        Write-Host ('  0. ' + (Get-InstallerText $ui 'Back to categories'))
        $choice = Read-MenuChoice $entries.Count (Get-InstallerText $ui 'Tool number (0 / Enter = Back): ')
        if ($choice -gt 0) { $params.Tool = $entries[$choice - 1].Name }
    }
}
$spec = $manifest.tools.PSObject.Properties[[string]$params.Tool]
if (-not $spec) { Write-Error (Get-InstallerText $ui 'Select a tool from the current catalog'); exit 2 }
$params.Language = $ui.Language
$params.Interface = if ($spec.Value.mcp -or $spec.Value.interfaces.mcp -or $spec.Value.manual_setup) { 'mcp' } else { 'native' }
& (Join-Path $SetupRoot 'mcp/scripts/launch/install-development-tool.ps1') @params
exit $LASTEXITCODE
