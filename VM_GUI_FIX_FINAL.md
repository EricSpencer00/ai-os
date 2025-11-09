# VM GUI Fix Summary

## Problem
The VNC screen was showing black because:
1. XFCE session processes died but weren't restarted
2. The startup script's process detection used `pgrep -f` (substring match) which incorrectly matched stale `xfconfd` processes
3. Script thought XFCE was running when it wasn't

## Solution
Fixed `/opt/auraos/start_xvfb_xfce_x11vnc.sh` to:
1. Use `pgrep -x` (exact process name match) instead of `pgrep -f` (substring)
2. Check for all 3 critical processes: `xfce4-session`, `xfwm4`, and `xfce4-panel`
3. Clean up stale XFCE processes before starting new session
4. Wait up to 30s for all processes to start before continuing

## Status
✅ **Fixed and working**

- XFCE processes running: `xfce4-session` (PID 22378), `xfwm4`, `xfce4-panel`
- Screenshot captured successfully (222KB PNG, 1280x720)
- Service logs show: "XFCE session started successfully (waited 2s)"

## Commands to Test

### Check XFCE is running
```bash
multipass exec auraos-multipass -- ps aux | grep -E 'xfce4-session|xfwm4|xfce4-panel' | grep -v grep
```

### Capture screenshot
```bash
curl -sS http://localhost:8765/screenshot -o /tmp/test.png && open /tmp/test.png
```

### Open VNC viewer
```bash
./open_vm_gui.sh
```

### Manual VNC connection
- URL: `vnc://localhost:5901`
- Password: `auraos123`

### Browser-based noVNC
- URL: `http://localhost:6080`

### Restart service if needed
```bash
multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
```

### Check service logs
```bash
multipass exec auraos-multipass -- sudo journalctl -u auraos-x11vnc.service -n 50 --no-pager
```

## Files Modified
- `/opt/auraos/start_xvfb_xfce_x11vnc.sh` (VM) - Fixed process detection
- `/opt/auraos/bin/ensure_desktop.sh` (VM) - Fixed process detection
- `vm_resources/start_xvfb_xfce_x11vnc.sh` (host repo) - Updated source
- `vm_resources/ubuntu_helpers/ensure_desktop.sh` (host repo) - Updated source

## Next Steps
1. **Test the desktop**: Run `./open_vm_gui.sh` and verify you see the XFCE desktop (not black)
2. **Reboot test**: Reboot VM and verify XFCE starts automatically: `multipass restart auraos-multipass`
3. **Automation test**: Try `./ubuntu_vm.sh screenshot /tmp/screen.png` or `./ubuntu_vm.sh click 640 360`

## Key Technical Details
- **Root cause**: `pgrep -f "xfce4-session"` matches any process with "xfce4" in cmdline, including `/usr/lib/.../xfce4/xfconf/xfconfd`
- **Fix**: Use `pgrep -x "xfce4-session"` for exact binary name match
- **Verification**: Check all 3 critical processes exist: `xfce4-session && xfwm4 && xfce4-panel`
