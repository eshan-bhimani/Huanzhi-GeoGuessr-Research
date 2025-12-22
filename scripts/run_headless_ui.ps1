param(
  [int]$UiPort = 5505,
  [string]$BackendBase = "http://127.0.0.1:8000",
  [double]$Lat,
  [double]$Lng,
  [double]$Heading = 120,
  [double]$Pitch,
  [double]$Fov,
  [string]$Session = "",
  [string]$ChromeBin = $env:CHROME_BIN,
  [switch]$NoSandbox
)

if (-not $PSBoundParameters.ContainsKey("Lat") -or -not $PSBoundParameters.ContainsKey("Lng")) {
  Write-Error "Lat and Lng are required. Example: .\run_headless_ui.ps1 -UiPort 5505 -BackendBase http://127.0.0.1:9000 -Lat 37.7749 -Lng -122.4194 -Heading 120"
  exit 1
}

function Encode([string]$value) {
  return [uri]::EscapeDataString($value)
}

$apiBaseEnc = Encode $BackendBase
$query = "autostart=1&lat=$Lat&lng=$Lng&heading=$Heading&apiBase=$apiBaseEnc"

if ($PSBoundParameters.ContainsKey("Pitch")) {
  $query += "&pitch=$Pitch"
}
if ($PSBoundParameters.ContainsKey("Fov")) {
  $query += "&fov=$Fov"
}
if ($Session) {
  $query += "&session=$(Encode $Session)"
}

$url = "http://127.0.0.1:$UiPort/index.html?$query"

$chromeCandidates = @()
if ($ChromeBin) { $chromeCandidates += $ChromeBin }
$chromeCandidates += @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "$env:ProgramFiles\Chromium\Application\chrome.exe",
  "$env:ProgramFiles(x86)\Chromium\Application\chrome.exe"
)

$chromePath = $null
foreach ($candidate in $chromeCandidates) {
  if ($candidate -and (Test-Path $candidate)) {
    $chromePath = $candidate
    break
  }
}

if (-not $chromePath) {
  $cmd = Get-Command chrome, chrome.exe, chromium, chromium.exe, msedge, msedge.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($cmd) { $chromePath = $cmd.Source }
}

if (-not $chromePath) {
  Write-Error "Chrome/Chromium not found. Set CHROME_BIN or install Chrome."
  exit 1
}

$userDataDir = Join-Path $env:TEMP "chrome-profile"
$args = @(
  "--headless=new",
  "--disable-gpu",
  "--disable-dev-shm-usage",
  "--window-size=1280,720",
  "--user-data-dir=$userDataDir"
)

if ($NoSandbox.IsPresent -or $env:NO_SANDBOX -eq "1") {
  $args += "--no-sandbox"
}

$args += $url

Write-Host "Opening: $url"
& $chromePath @args
