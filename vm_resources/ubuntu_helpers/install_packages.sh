#!/bin/bash
# install_packages.sh - Install additional packages for Ubuntu automation

set -e

echo "Updating package lists..."
sudo apt-get update -y

echo "Installing automation and development tools..."
sudo apt-get install -y \
  imagemagick \
  xdotool \
  x11-apps \
  x11-utils \
  wmctrl \
  scrot \
  xclip \
  jq \
  curl \
  wget \
  git \
  vim \
  htop \
  net-tools \
  firefox \
  chromium-browser \
  gnome-terminal \
  file-roller \
  gedit \
  evince \
  || true

echo "Installing Python development tools..."
sudo apt-get install -y \
  python3-pip \
  python3-venv \
  python3-opencv \
  tesseract-ocr \
  || true

echo "Installing GUI testing tools..."
pip3 install --user \
  pyautogui \
  pillow \
  pytesseract \
  opencv-python \
  || true

echo "✓ Package installation complete"
echo "Verify installations:"
echo "  - xdotool: $(command -v xdotool || echo 'NOT FOUND')"
echo "  - imagemagick: $(command -v convert || echo 'NOT FOUND')"
echo "  - tesseract: $(command -v tesseract || echo 'NOT FOUND')"
echo "  - firefox: $(command -v firefox || echo 'NOT FOUND')"
