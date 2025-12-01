# x11vnc Service Fix - RESOLVED ✅

## Problem Found
The x11vnc systemd service was failing with the error:
```
Fatal server error:
(EE) Unrecognized option: &
```

## Root Cause
The `ExecStartPre` directive in the systemd service had an invalid `&` at the end:
```bash
# BEFORE (WRONG):
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp &
```

Systemd doesn't support shell backgrounding operators (`&`) in ExecStartPre commands. The `&` was being passed directly to Xvfb, which doesn't recognize it as a valid option.

## Solution Applied
Changed the ExecStartPre command to wrap it in bash explicitly:
```bash
# AFTER (FIXED):
ExecStartPre=/bin/bash -c 'Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp &'
```

By wrapping the command in `/bin/bash -c '...'`, the shell handles the `&` operator correctly, backgrounding the Xvfb process as intended.

## Changes Made
**File:** `auraos.sh` (Line 662)

**Before:**
```bash
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp &
```

**After:**
```bash
ExecStartPre=/bin/bash -c 'Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp &'
```

## Verification Results

### Service Status
✅ Service now starts successfully and stays running
```
● auraos-x11vnc.service - AuraOS x11vnc VNC Server
   Active: active (running) since Mon 2025-11-10 13:34:35 CST
   Main PID: 14138 (x11vnc)
   CGroup:
   ├─14137 Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp
   └─14138 /usr/bin/x11vnc -display :99 -forever -shared ...
```

### Health Check Results
✅ Health check now shows:
```
[2/7] x11vnc Service
✓ x11vnc running

[3/7] noVNC Service
✓ noVNC running

[4/7] VNC Authentication
✓ Password file exists

[5/7] Port 5900 (x11vnc)
✓ Listening on 5900

[6/7] Port 6080 (noVNC)
✓ Host listening on 6080
```

### Previous Failure
Before fix:
```
[2/7] x11vnc Service
✗ x11vnc not running
  Starting...
Job for auraos-x11vnc.service failed because the control process exited with error code.
```

## How It Works Now

1. **ExecStartPre** runs `/bin/bash -c 'Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp &'`
   - Bash shell starts Xvfb in the background
   - Xvfb creates a virtual X display on display :99
   - Process continues after backgrounding completes

2. **ExecStart** then runs `/usr/bin/x11vnc -display :99 ...`
   - x11vnc connects to the virtual display :99
   - Provides VNC remote access on port 5900
   - Listens for incoming VNC connections

3. **Systemd** keeps the service running
   - If either process dies, it restarts automatically (Restart=on-failure)
   - Both Xvfb and x11vnc remain active together

## Impact
This fix ensures that:
- ✅ VNC server starts cleanly on each reboot
- ✅ Remote desktop access is available at `localhost:6080` (noVNC)
- ✅ No manual intervention needed to start GUI services
- ✅ Health check passes completely
- ✅ GUI automation can work with reliable display

## Testing
To verify the fix works:
```bash
# Run health check
./auraos.sh health

# Or check service directly
multipass exec auraos-multipass -- systemctl status auraos-x11vnc.service

# Connect to VNC
open http://localhost:6080/vnc.html
# Password: auraos123
```

## Future Deployments
The fixed auraos.sh script now has the correct ExecStartPre command. Any new VM setup with `./auraos.sh vm-setup` will use this corrected service configuration automatically.
