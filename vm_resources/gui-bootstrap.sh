#!/usr/bin/env bash
# GUI bootstrap for AuraOS VM — installs XFCE desktop, VNC, OCR, and a small automation agent.
set -euo pipefail

echo "[gui-bootstrap] Updating apt..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

echo "[gui-bootstrap] Installing packages (xfce4, tigervnc, OCR, tools, git)..."
apt-get install -y -qq \
    git \
    xfce4 xfce4-goodies \
    x11vnc xvfb \
    xdotool scrot tesseract-ocr \
    python3-venv python3-pip \
    espeak-ng orca || true

USER_HOME="/home/ubuntu"
AGENT_DIR="/opt/auraos/gui_agent"

echo "[gui-bootstrap] Configuring VNC xstartup for user ubuntu"
mkdir -p "$USER_HOME/.vnc"
cat > "$USER_HOME/.vnc/xstartup" <<'XSTART'
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
startxfce4 &
XSTART
chmod +x "$USER_HOME/.vnc/xstartup"
chown -R ubuntu:ubuntu "$USER_HOME/.vnc"

# Create a VNC password for the ubuntu user so tigervnc can start non-interactively
echo "[gui-bootstrap] Setting VNC password for ubuntu user"
mkdir -p "$USER_HOME/.vnc"
printf "auraos123\n" | vncpasswd -f > "$USER_HOME/.vnc/passwd" || true
chown ubuntu:ubuntu "$USER_HOME/.vnc/passwd" || true
chmod 600 "$USER_HOME/.vnc/passwd" || true

echo "[gui-bootstrap] Creating systemd service for Xvfb + x11vnc (display :1)"
cat > /etc/systemd/system/auraos-x11vnc.service <<'X11UNIT'
[Unit]
Description=AuraOS Xvfb + x11vnc virtual desktop
After=network.target

[Service]
Type=simple
User=root
ExecStart=/bin/bash -lc 'Xvfb :1 -screen 0 1280x720x24 & sleep 1; export DISPLAY=:1; su - ubuntu -c "xauth generate :1 . trusted || true"; chown ubuntu:ubuntu /home/ubuntu/.Xauthority >/dev/null 2>&1 || true; su - ubuntu -c "dbus-launch startxfce4" & sleep 1; /usr/bin/x11vnc -auth /home/ubuntu/.Xauthority -display :1 -rfbport 5900 -rfbauth /home/ubuntu/.vnc/passwd -forever -shared -noxdamage -nowf -ncache 10'
Restart=on-failure

[Install]
WantedBy=multi-user.target
X11UNIT

systemctl daemon-reload
systemctl enable --now auraos-x11vnc.service || true

echo "[gui-bootstrap] Installing noVNC (web VNC client) and websockify"
# ensure pip available and install websockify (used by noVNC utils)
python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install websockify >/dev/null 2>&1 || true

if [ ! -d /opt/novnc ]; then
    echo "[gui-bootstrap] Cloning noVNC into /opt/novnc"
    git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc || true
    chown -R ubuntu:ubuntu /opt/novnc || true
fi

cat > /etc/systemd/system/auraos-novnc.service <<'NOVNC'
[Unit]
Description=AuraOS noVNC web proxy
After=network.target auraos-x11vnc.service

[Service]
Type=simple
User=ubuntu
Environment=HOME=/home/ubuntu
ExecStart=/opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080
Restart=on-failure

[Install]
WantedBy=multi-user.target
NOVNC

systemctl daemon-reload
systemctl enable --now auraos-novnc.service || true

echo "[gui-bootstrap] Installing GUI automation agent into $AGENT_DIR"
mkdir -p "$AGENT_DIR"
cat > "$AGENT_DIR/agent.py" <<'PY'
#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import subprocess, os, uuid

app = Flask(__name__)

@app.route('/screenshot', methods=['GET'])
def screenshot():
    out = f'/tmp/screen_{uuid.uuid4().hex}.png'
    # use scrot to capture display :1
    subprocess.run(['DISPLAY=:1', 'scrot', out], shell=True)
    return send_file(out, mimetype='image/png')

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.json or {}
    path = data.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'error':'missing path or file not found'}), 400
    # run tesseract
    proc = subprocess.run(['tesseract', path, 'stdout'], capture_output=True, text=True)
    return jsonify({'text': proc.stdout})

@app.route('/click', methods=['POST'])
def click():
    data = request.json or {}
    x = data.get('x')
    y = data.get('y')
    if x is None or y is None:
        return jsonify({'error':'x and y required'}), 400
    subprocess.run(['DISPLAY=:1', 'xdotool', 'mousemove', str(x), str(y), 'click', '1'], shell=True)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8765)
PY

python3 -m venv "$AGENT_DIR/venv"
"$AGENT_DIR/venv/bin/pip" install --upgrade pip setuptools
"$AGENT_DIR/venv/bin/pip" install flask pillow pytesseract || true
chmod +x "$AGENT_DIR/agent.py"

cat > /etc/systemd/system/auraos-gui-agent.service <<'AUNIT'
[Unit]
Description=AuraOS GUI automation agent
After=network.target tigervnc.service

[Service]
Type=simple
User=root
ExecStart=/opt/auraos/gui_agent/venv/bin/python /opt/auraos/gui_agent/agent.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
AUNIT

systemctl daemon-reload
systemctl enable --now auraos-gui-agent.service || true

echo "[gui-bootstrap] Installing headless-agent skeleton (disabled by default)"
cat > "$AGENT_DIR/headless_agent.py" <<'HAG'
#!/usr/bin/env python3
from flask import Flask, request, jsonify
import subprocess, os

app = Flask(__name__)

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.json or {}
    path = data.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'error':'missing path or file not found'}), 400
    proc = subprocess.run(['tesseract', path, 'stdout'], capture_output=True, text=True)
    return jsonify({'text': proc.stdout})

@app.route('/run', methods=['POST'])
def run_cmd():
    data = request.json or {}
    cmd = data.get('cmd')
    if not cmd:
        return jsonify({'error':'cmd required'}), 400
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return jsonify({'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8766)
HAG

chmod +x "$AGENT_DIR/headless_agent.py"
cat > /etc/systemd/system/auraos-headless-agent.service <<'HEADLESS'
[Unit]
Description=AuraOS headless automation agent (CLI-only)
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/auraos/gui_agent/venv/bin/python /opt/auraos/gui_agent/headless_agent.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
HEADLESS

# Do not enable headless agent by default; user can enable it if they prefer headless mode
# systemctl enable --now auraos-headless-agent.service || true

echo "[gui-bootstrap] GUI bootstrap complete. VNC server should be listening on display :1 (localhost)."
echo "Use 'multipass info <name>' to find the VM address and forward or use SSH port forwarding to access VNC (or use ssh -L)."

exit 0
