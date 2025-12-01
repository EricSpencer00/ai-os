# Smart App Installation - AuraOS Browser & GUI Agent

## Overview

AuraOS now has **intelligent app installation** capabilities. If you try to open or use an application that isn't installed, the system will automatically attempt to install it for you.

## Features

### 1. Browser Smart Installer (`auraos_browser.py`)

**Automatic Detection & Installation**:
- When you click "🌐 Open Firefox" button
- When you perform a search that requires Firefox
- System checks if Firefox is installed
- If missing, automatically installs via GUI Agent
- Provides real-time feedback on installation progress

**How It Works**:
```python
ensure_app_installed("firefox")
├─ Check if already cached as available
├─ Check if app binary exists (shutil.which)
├─ If missing: Send install request to GUI Agent
├─ Verify installation success
└─ Cache result for future use
```

**User Experience**:
```
⟳ Checking Firefox availability...
⟳ firefox not found. Installing via smart installer...
✓ firefox installed successfully!
✓ Firefox is available. Opening now...
✓ Firefox opened - 4 actions executed
```

### 2. GUI Agent Smart Installer (`gui_agent.py`)

**Installation Endpoint**:
- Detects "install" commands in queries
- Extracts app name from request
- Maps common names to package names
- Executes `apt-get install` in VM via multipass
- Returns success/failure status

**Supported Apps** (with automatic package name mapping):
- firefox → firefox
- chromium → chromium-browser
- chrome → chromium-browser
- git → git
- python → python3
- node → nodejs
- npm → npm
- docker → docker.io
- curl → curl
- wget → wget
- vlc → vlc
- gimp → gimp
- blender → blender

**Request Example**:
```json
POST /ask
{
  "query": "install firefox"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "firefox installed successfully",
  "executed": [
    {
      "action": "install",
      "app": "firefox",
      "status": "success"
    }
  ]
}
```

### 3. Error Handling

**If Installation Fails**:
```
✗ Failed to install firefox: Package not found
→ Please install manually: sudo apt-get install -y firefox
→ Or contact system administrator
```

**Timeout Protection**:
- Installation attempts have 5-minute timeout
- Prevents hanging if network is slow
- Graceful error messages returned to user

**Caching**:
- Once installed, results cached
- No repeated installation attempts for same app in session
- Improves performance for frequently used apps

## Usage Examples

### Scenario 1: Open Firefox Button
```
User clicks "🌐 Open Firefox"
↓
Browser checks if Firefox installed
↓
If not: Installs automatically
↓
Opens Firefox once available
```

### Scenario 2: Search with Firefox
```
User types search query and presses Enter
↓
Browser ensures Firefox is installed
↓
If not: Installs automatically
↓
Opens Firefox and searches
```

### Scenario 3: Direct Install Request
```
Browser sends: "install chromium"
↓
GUI Agent receives request
↓
Runs: apt-get install -y chromium-browser
↓
Returns success/failure
```

## Implementation Details

### Browser Installation Flow

**File**: `auraos_browser.py`

**Key Methods**:
- `ensure_app_installed(app_name)` - Main smart installer
  - Checks cache first (avoids repeated checks)
  - Uses `shutil.which()` to find binary
  - Calls GUI Agent if not found
  - Verifies after installation
  - Returns boolean (success/failure)

- `_perform_install_on_vm(app_name)` - Fallback method
  - Direct multipass execution if GUI Agent fails
  - Maps app names to package names
  - Runs `apt-get update && apt-get install -y`

### GUI Agent Installation Flow

**File**: `gui_agent.py`

**Key Methods**:
- `ask()` endpoint - Now detects install requests
  - Checks if query contains "install" keyword
  - Routes to `handle_app_installation()`
  - Otherwise processes as normal query

- `handle_app_installation(query)` - Installs apps
  - Extracts app name from query
  - Maps to package name
  - Executes multipass apt-get command
  - Returns JSON status response

## Configuration

### Environment Variables (Optional)
```bash
# Multipass VM name (default: auraos-multipass)
export MULTIPASS_VM_NAME="auraos-multipass"

# Default user in VM (default: auraos)
export VM_USER="auraos"

# Installation timeout (default: 300 seconds)
export INSTALL_TIMEOUT="300"
```

### Adding New Apps

To add support for a new app, update the package map in both:

1. **auraos_browser.py** (optional, for caching):
```python
app_map = {
    "myapp": "myapp-package-name",
    # Add here
}
```

2. **gui_agent.py** (required):
```python
package_map = {
    "myapp": "myapp-package-name",
    # Add here
}
```

## Troubleshooting

### Installation Times Out
- Check if VM is running: `./auraos.sh health`
- Check network: `ping 8.8.8.8`
- Try manual install: `multipass exec auraos-multipass -- sudo apt-get install -y firefox`

### Installation Fails with "Package not found"
- App may not be in Ubuntu repos
- Try searching: `apt-cache search firefox`
- Install manually from source if needed

### Firefox Still Not Found After Installation
- Check if it installed to different path
- Verify: `which firefox`
- Check logs: `./auraos.sh inference logs`

### App Not in Package Map
- Add it to `package_map` in `gui_agent.py`
- Use: `apt-cache search <appname>` to find package name
- Test: `apt-get install -y <package-name>`

## Performance

### Installation Time Estimates
| App | Size | Time |
|-----|------|------|
| Firefox | ~80MB | 30-60s |
| Chromium | ~200MB | 60-120s |
| Git | ~5MB | 5-10s |
| Python3 | ~50MB | 10-20s |
| Node.js | ~100MB | 30-60s |
| Docker | ~200MB | 30-60s |

*Times depend on network speed and VM performance*

### Caching Benefits
- First install: 30-120s (depends on app)
- Subsequent checks: <100ms (cached)
- Reduces repeated installation attempts

## Future Enhancements

1. **Progress Tracking** - Show installation progress percentage
2. **Dependency Resolution** - Auto-install dependencies
3. **Version Selection** - Allow specifying versions (firefox 124 vs 125)
4. **Rollback** - Ability to uninstall apps if needed
5. **Repo Management** - Add/remove PPAs for newer versions
6. **Brew Support** - For macOS host installations
7. **Verification** - Check file integrity after install
8. **Offline Mode** - Cache packages locally for fast reinstalls

## Security Notes

- Only installs from official Ubuntu repositories (apt)
- Uses `sudo` with multipass (requires VM setup)
- No arbitrary command execution (app name validated)
- Timeout protection prevents resource exhaustion
- Failed installations don't break the system

## API Reference

### Browser Method: `ensure_app_installed(app_name)`
```python
success = browser.ensure_app_installed("firefox")
# Returns: True if installed/available, False if failed
```

### GUI Agent Endpoint: POST `/ask`
```
Request:  {"query": "install firefox"}
Response: {"status": "success", "message": "...", "executed": [...]}
```

---

**Status**: ✅ Production Ready

All components integrated and validated. Browser and GUI Agent now have smart app installation capabilities.

