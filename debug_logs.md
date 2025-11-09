open:

multipass exec auraos-multipass -- sudo sh -c 'su - ubuntu -c "DISPLAY=:1 dbus-launch startxfce4 > /home/ubuntu/xfce_start.log 2>&1 & sleep 3; ps aux | egrep \"xfce4|xfwm4|xfce4-panel|startxfce4\" || true; tail -n 100 /home/ubuntu/xfce_start.log"'