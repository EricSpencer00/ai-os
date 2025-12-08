# Firefox Snap Issue - Complete Resolution

## The Problem

Firefox on Ubuntu 22.04 in the VM is installed as a **snap package** instead of a deb package. This causes confinement issues and launch failures with errors like:

```
Command '/usr/bin/firefox' requires the firefox snap to be installed.
Please install it with: snap install firefox
```

## Why This Happens

- Ubuntu 22.04 ships with Firefox as a snap-only package in the default repositories
- Snap has strict confinement that prevents Firefox from running properly in virtualized environments
- The snap package is sandboxed and can't access necessary system resources

## Solutions

### Option 1: Fix Existing VM (Recommended - Fastest)

```bash
./auraos.sh fix-browser
```

This command:
1. Removes the snap Firefox completely (--purge)
2. Adds Mozilla Team PPA for deb-based Firefox
3. Configures apt preferences to prefer PPA over snap
4. Installs proper deb-based Firefox or falls back to Chromium
5. Verifies the installation

Takes ~2-3 minutes.

### Option 2: Clean VM Setup (Complete Solution)

```bash
./auraos.sh vm-setup
```

This creates a new VM with all fixes pre-applied. Takes ~15-20 minutes but includes everything.

## After Fixing

Test Firefox in the VM via noVNC:
1. Open http://localhost:6080/vnc.html
2. Click the Terminal application
3. Run: `firefox`

Or use the Browser app in AuraOS and click "Firefox" to auto-launch.

## If Still Having Issues

1. **Check what firefox actually is:**
   ```bash
   multipass exec auraos-multipass -- which firefox
   multipass exec auraos-multipass -- file /usr/bin/firefox
   ```

2. **Force remove snap completely:**
   ```bash
   multipass exec auraos-multipass -- sudo snap remove --purge firefox
   multipass exec auraos-multipass -- sudo apt-get install -y firefox-esr
   ```

3. **Use Chromium as alternative:**
   ```bash
   multipass exec auraos-multipass -- chromium-browser --no-sandbox &
   ```

## Technical Details

The `fix-browser` command:
- Uses `snap remove --purge` (not just `remove`) to completely eliminate snap version
- Adds Mozilla Team PPA with proper apt preferences
- Sets `Pin-Priority: -1` for snap firefox to prevent re-installation
- Tests for both `/usr/bin/firefox` and `/usr/bin/firefox-esr`
- Has Chromium fallback if Firefox installation fails

## Snap vs Deb

| Aspect | Snap | Deb |
|--------|------|-----|
| Confinement | Strict sandbox | None |
| VM Compatibility | Poor (cgroup2 issues) | Excellent |
| Performance | Slower startup | Fast startup |
| Updates | Automatic | Via apt |
| Size | Large | Smaller |

The deb version is the correct choice for VMs and AuraOS.
