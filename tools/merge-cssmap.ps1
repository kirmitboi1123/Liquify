# usage: powershell -ExecutionPolicy Bypass -File merge-cssmap.ps1 [-Additions FILE] [-CssMap FILE]
# Adds the entries from the additions file that Spicetify's css-map lacks (Spicetify's entry wins
# on a conflict) and writes the result as UTF-8 without a BOM (Spicetify rejects a BOM). Before the
# first change to a given css-map it saves the original next to it as css-map.<sha256 prefix>.json.bak.
# Exit code 0 = unchanged, 10 = changed, 1 = error. Windows twin of merge_cssmap.py, no Python needed.
param(
    [string]$Additions = (Join-Path $PSScriptRoot 'css-map-additions-1.3.5.3058.json'),
    [string]$CssMap = (Join-Path $env:LOCALAPPDATA 'spicetify\css-map.json')
)
$ErrorActionPreference = 'Stop'
try {
    if (-not (Test-Path $CssMap)) { throw "css-map not found: $CssMap (install Spicetify and run it once first)" }
    # JavaScriptSerializer, not ConvertFrom-Json: class hashes are case-sensitive and PowerShell 5.1's
    # ConvertFrom-Json treats keys that differ only in case as duplicates.
    Add-Type -AssemblyName System.Web.Extensions
    $json = New-Object System.Web.Script.Serialization.JavaScriptSerializer
    $json.MaxJsonLength = 50MB
    $raw = [IO.File]::ReadAllBytes($CssMap)
    $map = $json.DeserializeObject([IO.File]::ReadAllText($CssMap))
    $add = $json.DeserializeObject([IO.File]::ReadAllText($Additions))
    $missing = @($add.Keys | Where-Object { -not $map.ContainsKey($_) })
    if ($missing.Count -eq 0) {
        Write-Output "css-map: 0 added ($($map.Count) entries)"
        exit 0
    }
    $sha = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($raw)).Replace('-', '').ToLower()
    $backup = Join-Path (Split-Path $CssMap) ("css-map.{0}.json.bak" -f $sha.Substring(0, 12))
    if (-not (Test-Path $backup)) { [IO.File]::WriteAllBytes($backup, $raw) }
    foreach ($k in $missing) { $map[$k] = $add[$k] }
    [IO.File]::WriteAllText($CssMap, $json.Serialize($map), (New-Object System.Text.UTF8Encoding $false))
    Write-Output "css-map: $($missing.Count) added ($($map.Count) entries), original saved as $(Split-Path $backup -Leaf)"
    exit 10
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
    exit 1
}
