# android-mcp-windows-setup

**Working setup guide and fix pack for [android-mcp](https://github.com/growvv/Android-Automation-MCP) on Windows.**

The `android-mcp` npm package works great on Linux/macOS but fails silently on Windows due to several environmental issues. This repo contains a one-shot PowerShell setup script and the missing Python bridge file that fix all of them.

---

## What This Solves

Installing `android-mcp` on Windows and pointing Claude Code's MCP config at it results in a broken chain — tools appear registered but silently fail. Five distinct issues cause this:

| # | Problem | Root Cause |
|---|---------|------------|
| 1 | `adb` not found | ADB platform-tools not in the PATH seen by the MCP server process |
| 2 | `python` resolves to Windows Store stub | Windows ships a fake `python.exe` that opens the Store — real Python 3.x at a non-standard path |
| 3 | `uiautomator2` not installed | Package missing from the Python environment MCP actually uses |
| 4 | Python bridge script missing | `uiautomator2_bridge.py` is not included in the npm package — must be created manually |
| 5 | Bridge gets deleted on `npm update` | Since the bridge lives inside the npm package directory, any update wipes it |

This repo fixes all five and makes the setup reproducible.

---

## Requirements

- Windows 10 or 11
- [Node.js](https://nodejs.org) (v18+)
- [Python 3.x](https://www.python.org/downloads/) installed to a known path (not the Windows Store version)
- [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools) (for `adb`)
- [Claude Code](https://claude.ai/code) with MCP support
- Android device with USB debugging enabled, OR an Android emulator

---

## Quick Start

```powershell
# 1. Clone this repo
git clone https://github.com/mvahora2023/android-mcp-windows-setup.git
cd android-mcp-windows-setup

# 2. Review the portable path defaults near the top of setup-android-mcp.ps1.
#    Adjust PYTHON / PIP / ANDROID_HOME only if installed elsewhere.

# 3. Run the setup script
powershell -ExecutionPolicy Bypass -File setup-android-mcp.ps1

# 4. Restart Claude Code to reload MCP servers
```

---

## What the Setup Script Does

`setup-android-mcp.ps1` runs these steps in order, idempotently:

1. **Checks prerequisites** — verifies Python, ADB, and Node.js are reachable at the configured paths
2. **Installs android-mcp globally** — `npm install -g android-mcp`
3. **Restores the bridge script** — copies `uiautomator2_bridge.py` from this repo into the npm package directory (survives future `npm update` runs when you re-run the script)
4. **Installs uiautomator2** — `pip install uiautomator2` using the real Python binary
5. **Patches `~/.claude.json`** — ensures the `android-automation` MCP entry exists with the correct PATH and ANDROID_HOME environment variables
6. **Checks ADB device connection** — reports connected devices or warns if none found

You can re-run it after an `npm update`, but review what it will install or modify first. The script has not been independently tested here on every Windows configuration.

---

## Configuration

The script now uses paths derived from your Windows user environment and its own
repository folder. **Check that the defaults match your installation**. Python
may live elsewhere, so update the variables at the start of
`setup-android-mcp.ps1` if needed:

```powershell
$ANDROID_HOME  = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$PYTHON        = Join-Path $env:LOCALAPPDATA "Python\bin\python.exe"
$PIP           = Join-Path $env:LOCALAPPDATA "Python\bin\pip.exe"
$ADB           = Join-Path $ANDROID_HOME "platform-tools\adb.exe"
$BRIDGE_BACKUP = Join-Path $PSScriptRoot "uiautomator2_bridge.py"
```

The MCP environment prepends Android tools and the selected Python directories to
the current PATH. Before editing Claude's configuration, the script backs up
`%USERPROFILE%\.claude.json` as `.claude.json.bak`.


**Finding your real Python path:**

```powershell
# This shows all python.exe on your system — pick the real one, not WindowsApps
where.exe python
Get-Command python | Select-Object -ExpandProperty Source
```

**Finding your npm global prefix:**

```powershell
npm prefix -g
```

---

## After Setup: First-Time Device Init

Once the script completes successfully:

```powershell
# Confirm your device is visible
adb devices

# Initialize uiautomator2 on the device (run once per device)
python -m uiautomator2 init
```

Then restart Claude Code. The `android-automation` MCP tools should now appear.

---

## Claude Code MCP Config

The script updates the per-user `.claude.json` file and writes a backup before changes. If you prefer to configure it manually:

```json
{
  "mcpServers": {
    "android-automation": {
      "command": "android-mcp",
      "args": [],
      "env": {
        "ANDROID_HOME": "C:\\Path\\To\\Android\\Sdk",
        "PATH": "C:\\Path\\To\\Android\\Sdk\\platform-tools;C:\\Path\\To\\Python\\bin;C:\\Path\\To\\Python\\Scripts;C:\\Path\\To\\npm\\global;C:\\Program Files\\nodejs;C:\\Windows\\system32;C:\\Windows"
      }
    }
  }
}
```

The `env.PATH` override is critical — without it, the MCP server process inherits a PATH that either misses ADB or points to the Windows Store Python stub.

---

## Files in This Repo

| File | Purpose |
|------|---------|
| `setup-android-mcp.ps1` | One-shot setup and repair script |
| `uiautomator2_bridge.py` | Python bridge that android-mcp requires but doesn't ship |
| `README.md` | This file |

---

## Troubleshooting

**`android-mcp: command not found` after install**
→ npm global bin directory is not in your system PATH. Add the output of `npm prefix -g` + `\` to your PATH, or use the full path in the MCP config's `command` field.

**`uiautomator2` ImportError**
→ The wrong Python is being used. Check that `$PYTHON` in the script points to the real Python binary, and that `uiautomator2` is installed in that environment.

**Device shows as `unauthorized` in `adb devices`**
→ Disconnect and reconnect the USB cable, then accept the "Allow USB debugging" prompt on the device.

**Tools appear in Claude but return errors**
→ Run `setup-android-mcp.ps1` again (it's idempotent), then restart Claude Code.

---

## Contributing

If you've hit additional Windows-specific issues with android-mcp and found fixes, PRs are welcome. The goal is to keep this as a minimal, no-dependency fix pack.

---

## License

MIT
