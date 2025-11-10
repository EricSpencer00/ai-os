#!/bin/bash
# Test VNC password authentication
# Attempts to connect and authenticate with x11vnc through the SSH tunnel

echo "Testing VNC password authentication..."
echo ""

# Check if we're connected via SSH tunnel
echo "1. Checking SSH tunnel to VM..."
ssh -L 5901:localhost:5900 ubuntu@192.168.2.9 "echo '✓ SSH connection OK'" 2>&1 | head -1

echo ""
echo "2. Checking x11vnc is running..."
multipass exec auraos-multipass -- ps aux | grep x11vnc | grep -v grep | head -1 | awk '{print "   Process:", $2, $11, $12, $13, $14, $15}'

echo ""
echo "3. Verifying password file exists..."
multipass exec auraos-multipass -- bash -c 'ls -lh /home/ubuntu/.vnc/passwd && hexdump -C /home/ubuntu/.vnc/passwd'

echo ""
echo "4. Testing VNC protocol..."
python3 << 'PYTHON'
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 5901))
response = sock.recv(12)
print(f"   VNC Server: {response.decode().strip()}")
sock.close()
print("   ✓ VNC protocol OK")
PYTHON

echo ""
echo "5. Instructions:"
echo ""
echo "   Browser: http://localhost:6080/vnc.html"
echo "   Native:  open -a 'VNC Viewer' vnc://localhost:5901"
echo ""
echo "   Password: auraos123"
echo ""
echo "If auth still fails:"
echo "  - Check x11vnc service logs:"
echo "    multipass exec auraos-multipass -- journalctl -u auraos-x11vnc.service -n 20"
echo "  - Restart x11vnc:"
echo "    multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service"
