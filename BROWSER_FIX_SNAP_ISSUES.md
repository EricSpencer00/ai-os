# Browser Fix - Firefox/Chromium Not Launching

## Problem
The "Browser" app showed "Failed to execute default Web Browser - Input/output error" when trying to launch Firefox. This is due to snap confinement issues in virtualized environments.

## Solution Applied

### 1. **Updated Browser App** (`auraos_browser.py`)
- ✅ Now tries **Chromium first** (more reliable on ARM than Firefox snap)
- ✅ Falls back to Firefox with `--no-sandbox` flag
- ✅ Added **[Terminal] button** to manually launch browser in Terminal app
- ✅ Clear instructions on how to open browser manually

### 2. **Updated VM Setup Script** (`scripts/vm.sh`)
- ✅ Installs both Firefox AND Chromium packages
- ✅ Creates browser wrapper scripts:
  - `/usr/local/bin/firefox-wrapped` - Firefox with `--no-sandbox`
  - `/usr/local/bin/chromium-wrapped` - Chromium with `--no-sandbox`
- ✅ Pre-configured to work in snap-confined environments

### 3. **Installed Chromium in Current VM**
```bash
multipass exec auraos-multipass -- sudo apt-get install -y chromium-browser
```

## How to Use (Current VM)

### Option 1: Via Browser App UI
1. Click the **[Web] Firefox** button to auto-launch (tries Chromium first)
2. If that doesn't work, click **[Terminal]** button
3. In the Terminal, run:
   ```
   chromium-browser --no-sandbox
   ```
   or
   ```
   firefox
   ```

### Option 2: Manual Launch
Open Terminal app and run:
```bash
chromium-browser --no-sandbox &
# or
firefox &
```

### Option 3: Remote Access via VNC
- Open: http://192.168.2.50:6080/vnc.html
- Password: auraos123
- Use browser on your machine instead

## Technical Details

**Why the error occurs:**
- Ubuntu 22.04 on ARM only has snap-packaged Firefox in the default repos
- Snap confinement prevents Firefox from running in constrained VMs (missing cgroup2, seccomp issues)
- Chromium from debs is more flexible

**What the fix does:**
- Browser app now tries Chromium first (more compatible)
- Falls back to Firefox if Chromium unavailable
- Both browsers launched with `--no-sandbox` to bypass snap/cgroup issues
- Terminal button provides escape hatch for manual browser access
- VM setup script now creates wrapper scripts on fresh installs

## Testing

✅ **Verified:**
- Chromium installed in VM: `/usr/bin/chromium-browser`
- Chromium can be invoked with `--no-sandbox` flag
- Browser app code updated and syntax valid
- VM setup script includes both browsers + wrappers

## If Still Not Working

1. **Try direct access:**
   ```bash
   multipass exec auraos-multipass -- DISPLAY=:99 chromium-browser --no-sandbox &
   ```

2. **Check for missing libraries:**
   ```bash
   multipass exec auraos-multipass -- sudo apt-get install -y libgtk-3-0 libdbus-glib-1-2
   ```

3. **Use noVNC web browser:**
   - Open: http://192.168.2.50:6080/vnc.html
   - Use browser in the VNC session directly

## Files Changed

- `auraos_browser.py` - Try Chromium first, add Terminal button
- `scripts/vm.sh` - Add Chromium, create browser wrappers

## Next Steps

When setting up new VMs:
```bash
./auraos.sh vm-setup
# Chromium + Firefox + wrappers will be pre-installed
```

For existing VM, run this to apply wrappers:
```bash
multipass exec auraos-multipass -- sudo bash -c '
cat > /usr/local/bin/chromium-wrapped <<EOF
#!/bin/bash
exec /usr/bin/chromium-browser --no-sandbox --disable-gpu "\$@"
EOF
chmod +x /usr/local/bin/chromium-wrapped
'
```
