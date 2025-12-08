# Quick Test: Browser Fix

## One-Command VM Update (Install Chromium)

```bash
multipass exec auraos-multipass -- sudo apt-get install -y chromium-browser
```

## Test 1: Launch Browser App
```bash
./auraos.sh launcher  # or ./auraos.sh ui
# Click "Browser" app
# Should see Chromium attempts or Terminal button option
```

## Test 2: Manual Browser Launch in Terminal
```bash
# Open Terminal app from launcher
# Then run:
chromium-browser --no-sandbox &
# or
firefox &
```

## Test 3: Check Browser Wrappers (Fresh VM Only)
```bash
# If you set up VM with updated scripts/vm.sh:
multipass exec auraos-multipass -- which firefox-wrapped chromium-wrapped
```

## Expected Behavior

✅ **Browser App Click:**
- Should show "[OK] Chromium launched" or "[OK] Firefox launched"
- Desktop displays browser window
- OR displays [Terminal] button option

✅ **Manual Terminal Command:**
- Browser window opens (headless display :99)
- Visible via noVNC at http://192.168.2.50:6080/vnc.html

✅ **No More Error Dialog:**
- "Failed to execute default Web Browser" should not appear
- Either browser launches or clear UI option is shown

## Troubleshooting

**If Chromium still fails:**
```bash
# Try Firefox directly
multipass exec auraos-multipass -- DISPLAY=:99 firefox --no-sandbox &
```

**If neither works, check Xvfb (display) is running:**
```bash
multipass exec auraos-multipass -- ps aux | grep Xvfb
# Should see: /usr/bin/Xvfb :99 -screen 0 1280x720x24
```

**Check browser process:**
```bash
multipass exec auraos-multipass -- ps aux | grep -E 'firefox|chromium'
```

## Success Indicator

✅ When you run `./auraos.sh launcher` and click Browser:
- Either: Browser window appears in VNC
- Or: UI shows clear "[Terminal]" button with instructions
- **NOT:** "Failed to execute default Web Browser" error
