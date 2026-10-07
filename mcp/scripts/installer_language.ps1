function New-InstallerUi([string]$Root, [string]$Language = 'auto') {
    $data = Get-Content -LiteralPath (Join-Path $Root 'mcp/tools/installer.messages.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($data.schema_version -ne 1) { throw 'Unsupported installer language schema' }
    $encoding = [Text.Encoding]::GetEncoding([Console]::OutputEncoding.CodePage, [Text.EncoderFallback]::ExceptionFallback, [Text.DecoderFallback]::ExceptionFallback)
    $supported = $true
    try { [void]$encoding.GetBytes(($data.translations.'zh-TW'.PSObject.Properties.Value -join '')) } catch { $supported = $false }
    $ui = [pscustomobject]@{ Data = $data; SupportsChinese = $supported; Language = 'en' }
    Set-InstallerLanguage $ui $Language
    return $ui
}

function Set-InstallerLanguage($Ui, [string]$Language) {
    if ($Language -notin @('auto', 'zh-TW', 'en')) { throw 'Language must be auto, zh-TW or en' }
    $Ui.Language = if ($Language -ne 'en' -and $Ui.SupportsChinese) { 'zh-TW' } else { 'en' }
    if ($Language -eq 'zh-TW' -and -not $Ui.SupportsChinese) { Write-Host 'Chinese output is unavailable in this encoding; using English' }
}

function Get-InstallerText($Ui, [string]$Template, [object[]]$Values = @()) {
    $translations = $Ui.Data.translations.PSObject.Properties[$Ui.Language]
    if ($translations) {
        $translated = $translations.Value.PSObject.Properties[$Template]
        if ($translated) { $Template = $translated.Value }
    }
    return [string]::Format($Template, $Values)
}

function Get-InstallerLabel($Ui, [string]$Kind, [string]$Value, [string]$Fallback = 'Other') {
    $labels = $Ui.Data.labels.PSObject.Properties[$Ui.Language]
    if ($labels) {
        $category = $labels.Value.PSObject.Properties[$Kind]
        if ($category) {
            $translated = $category.Value.PSObject.Properties[$Value]
            if ($translated) { return [string]$translated.Value }
        }
    }
    if ($Ui.Language -eq 'en' -and $Value -match '[^\x00-\x7F]') { return $Fallback }
    return $Value
}

function Open-InstallerGuide($Ui, [string]$Root, [string]$Tool) {
    $path = Join-Path $Root 'docs/setup/installer-guide.html'
    Write-Host (Get-InstallerText $Ui 'Opening the Chinese setup guide: {0}' @($path))
    try {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Guide missing' }
        $url = ([Uri]([IO.Path]::GetFullPath($path))).AbsoluteUri + '#tool=' + [Uri]::EscapeDataString($Tool)
        Start-Process -FilePath $url -ErrorAction Stop
    } catch {
        Write-Warning (Get-InstallerText $Ui 'Could not open the guide automatically. Open it manually: {0}' @($path))
    }
}
