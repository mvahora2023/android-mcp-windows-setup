# setup-android-mcp.ps1
# Idempotent setup script for android-mcp on Windows.
# Run this after any npm update, new machine setup, or if android-mcp stops working.
# Usage: powershell -ExecutionPolicy Bypass -File setup-android-mcp.ps1

$ErrorActionPreference = "Continue"

$PYTHON        = "C:\Users\makin\AppData\Local\Python\bin\python.exe"
$PIP           = "C:\Users\makin\AppData\Local\Python\bin\pip.exe"
$ADB           = "C:\Users\makin\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$BRIDGE_BACKUP = "C:\Users\makin\.claude\scripts\uiautomator2_bridge.py"
$CLAUDE_JSON   = "C:\Users\makin\.claude.json"

$MCP_ENV_PATH = "C:\Users\makin\AppData\Local\Android\Sdk\platform-tools;" +
    "C:\Users\makin\AppData\Local\Python\bin;" +
    "C:\Users\makin\AppData\Local\Python\pythoncore-3.14-64\Scripts;" +
    "C:\Users\makin\AppData\Roaming\npm;" +
    "C:\Program Files\nodejs;" +
    "C:\Windows\system32;" +
    "C:\Windows;" +
    "C:\Windows\System32\Wbem;" +
    "C:\Windows\System32\WindowsPowerShell\v1.0"

function Write-Step($msg) { Write-Host "" ; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-FAIL($msg) { Write-Host "    [FAIL] $msg" -ForegroundColor Red }
function Write-WARN($msg) { Write-Host "    [WARN] $msg" -ForegroundColor Yellow }
function Write-INFO($msg) { Write-Host "    $msg" -ForegroundColor Gray }

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
Write-Step "Checking prerequisites"

if (-not (Test-Path $PYTHON)) {
    Write-FAIL "Python not found at $PYTHON"
    exit 1
}
$pyVer = & $PYTHON --version 2>&1
Write-OK "Python: $pyVer"

if (-not (Test-Path $ADB)) {
    Write-FAIL "ADB not found at $ADB"
    exit 1
}
Write-OK "ADB found at $ADB"

$nodeVer = node --version 2>$null
if (-not $nodeVer) {
    Write-FAIL "Node.js not found"
    exit 1
}
Write-OK "Node.js: $nodeVer"

# ---------------------------------------------------------------------------
# 2. Install / reinstall android-mcp globally
# ---------------------------------------------------------------------------
Write-Step "Installing android-mcp globally via npm"
$npmOut = npm install -g android-mcp 2>&1
$npmOut | ForEach-Object { Write-INFO $_ }
if ($LASTEXITCODE -eq 0) {
    Write-OK "android-mcp installed"
} else {
    Write-FAIL "npm install failed (exit $LASTEXITCODE)"
    exit 1
}

# ---------------------------------------------------------------------------
# 3. Restore bridge script (npm install may overwrite it)
# ---------------------------------------------------------------------------
Write-Step "Restoring uiautomator2 bridge script"

$npmPrefix = (npm prefix -g 2>$null).Trim()
$bridgeDest = "$npmPrefix\node_modules\android-mcp\src\python\uiautomator2_bridge.py"
$bridgeDir  = Split-Path $bridgeDest

if (-not (Test-Path $BRIDGE_BACKUP)) {
    Write-FAIL "Backup not found at $BRIDGE_BACKUP"
    exit 1
}

if (-not (Test-Path $bridgeDir)) {
    New-Item -ItemType Directory -Path $bridgeDir -Force | Out-Null
    Write-INFO "Created directory: $bridgeDir"
}

Copy-Item -Path $BRIDGE_BACKUP -Destination $bridgeDest -Force
Write-OK "Bridge restored -> $bridgeDest"

# ---------------------------------------------------------------------------
# 4. Install / verify uiautomator2
# ---------------------------------------------------------------------------
Write-Step "Installing/verifying uiautomator2"

& $PIP install --quiet uiautomator2 2>&1 | ForEach-Object { Write-INFO $_ }
$u2check = & $PYTHON -c "import uiautomator2; print('ok')" 2>&1
if ($u2check -eq "ok") {
    Write-OK "uiautomator2 importable"
} else {
    Write-FAIL "uiautomator2 import failed: $u2check"
    exit 1
}

# ---------------------------------------------------------------------------
# 5. Verify / patch ~/.claude.json MCP entry
# ---------------------------------------------------------------------------
Write-Step "Verifying MCP config in .claude.json"

if (-not (Test-Path $CLAUDE_JSON)) {
    Write-FAIL "$CLAUDE_JSON not found"
    exit 1
}

$raw    = Get-Content $CLAUDE_JSON -Raw
$config = $raw | ConvertFrom-Json
$needsWrite = $false

if (-not $config.PSObject.Properties["mcpServers"]) {
    $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue (New-Object PSObject)
    $needsWrite = $true
}

$mcp = $config.mcpServers

if (-not $mcp.PSObject.Properties["android-automation"]) {
    $envObj = New-Object PSObject
    $envObj | Add-Member -NotePropertyName "ANDROID_HOME" -NotePropertyValue "C:\Users\makin\AppData\Local\Android\Sdk"
    $envObj | Add-Member -NotePropertyName "PATH" -NotePropertyValue $MCP_ENV_PATH

    $entry = New-Object PSObject
    $entry | Add-Member -NotePropertyName "command" -NotePropertyValue "android-mcp"
    $entry | Add-Member -NotePropertyName "args"    -NotePropertyValue @()
    $entry | Add-Member -NotePropertyName "env"     -NotePropertyValue $envObj

    $mcp | Add-Member -NotePropertyName "android-automation" -NotePropertyValue $entry
    $needsWrite = $true
    Write-INFO "android-automation entry was missing - added"
} else {
    $currentPath = $mcp."android-automation".env.PATH
    if ($currentPath -ne $MCP_ENV_PATH) {
        $mcp."android-automation".env.PATH = $MCP_ENV_PATH
        $needsWrite = $true
        Write-INFO "PATH was outdated - updated"
    }
}

if ($needsWrite) {
    $config | ConvertTo-Json -Depth 20 | Out-File $CLAUDE_JSON -Encoding utf8
    Write-OK ".claude.json updated"
} else {
    Write-OK ".claude.json already correct - no changes needed"
}

# ---------------------------------------------------------------------------
# 6. ADB device check
# ---------------------------------------------------------------------------
Write-Step "Checking ADB device connection"

$adbOut  = & $ADB devices 2>&1
$devices = $adbOut | Select-Object -Skip 1 | Where-Object { $_ -match "\bdevice\b" }

if ($devices) {
    Write-OK "Device(s) connected:"
    $devices | ForEach-Object { Write-INFO "  $_" }
} else {
    Write-WARN "No device detected. Connect your Galaxy S25 Ultra via USB with USB debugging on."
    Write-INFO "  Verify with:    $ADB devices"
    Write-INFO "  First-time init (once connected): $PYTHON -m uiautomator2 init"
}

# ---------------------------------------------------------------------------
# 7. Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  android-mcp setup complete" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If device was not connected, after connecting run:" -ForegroundColor Yellow
Write-Host "  1. $ADB devices"
Write-Host "  2. $PYTHON -m uiautomator2 init"
Write-Host "  3. Restart Claude Code to reload MCP servers"
Write-Host ""
