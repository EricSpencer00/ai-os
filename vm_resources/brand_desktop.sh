#!/bin/bash
# brand_desktop.sh - Customize XFCE desktop for AuraOS branding

set -e

USER=ubuntu
HOSTNAME="auraos"

echo "Branding AuraOS Desktop..."

# Set hostname to auraos
echo "Setting hostname to ${HOSTNAME}..."
hostnamectl set-hostname "${HOSTNAME}"

# Update /etc/hosts
sed -i "s/127.0.1.1.*/127.0.1.1\t${HOSTNAME}/" /etc/hosts

# Customize XFCE panel (hide username, show AuraOS)
echo "Customizing XFCE panel..."

# Ensure directories exist
mkdir -p /home/${USER}/.config/autostart
mkdir -p /home/${USER}/Desktop

# Create custom desktop background script
cat > /home/${USER}/.config/autostart/auraos-welcome.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=AuraOS Welcome
Comment=Display AuraOS branding on startup
Exec=sh -c 'notify-send "Welcome to AuraOS" "AI-Powered Operating System" --icon=system-run'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

# Set wallpaper text/label (via desktop file)
mkdir -p /home/${USER}/Desktop

cat > /home/${USER}/Desktop/AuraOS.desktop <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=AuraOS
Comment=AI-Powered Operating System
Exec=xterm -e "echo 'AuraOS - AI Operating System'; bash"
Icon=system-software-update
Terminal=false
Categories=System;
EOF

chmod +x /home/${USER}/Desktop/AuraOS.desktop
chown ${USER}:${USER} /home/${USER}/Desktop/AuraOS.desktop

# Create a simple AuraOS label file on desktop
cat > /home/${USER}/Desktop/README.txt <<'EOF'
╔════════════════════════════════════════╗
║           AuraOS - AI OS               ║
║    AI-Powered Operating System         ║
╚════════════════════════════════════════╝

This is AuraOS - an AI-driven operating system.
Vision models can see and interact with this desktop.
EOF

chown ${USER}:${USER} /home/${USER}/Desktop/README.txt

# Create custom panel clock format (remove username)
# This would require xfconf-query commands that need to be run as the user
# We'll create a script the user can run

cat > /home/${USER}/customize_panel.sh <<'PANEL_SCRIPT'
#!/bin/bash
# Run this as ubuntu user to customize panel

export DISPLAY=:1

# Hide username from whoami plugin if it exists
xfconf-query -c xfce4-panel -p /plugins/plugin-1/show-username -s false 2>/dev/null || true

# Set custom clock format
xfconf-query -c xfce4-panel -p /plugins/plugin-2/digital-format -s "AuraOS | %H:%M" 2>/dev/null || true

echo "Panel customized - restart panel with: xfce4-panel -r"
PANEL_SCRIPT

chmod +x /home/${USER}/customize_panel.sh
chown -R ${USER}:${USER} /home/${USER}/.config /home/${USER}/Desktop /home/${USER}/customize_panel.sh

echo "✓ Desktop branded for AuraOS"
echo ""
echo "Hostname set to: ${HOSTNAME}"
echo "Desktop icon created: AuraOS"
echo "To finish panel customization, run as ubuntu:"
echo "  DISPLAY=:1 /home/${USER}/customize_panel.sh"
