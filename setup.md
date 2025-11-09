## Start the VM
multipass start auraos-multipass

## Enable and start the GUI service in the VM
multipass exec auraos-multipass -- sudo systemctl daemon-reload && multipass exec auraos-multipass -- sudo systemctl enable --now auraos-x11vnc.service

## Open the VM GUI (creates tunnels and opens VNC/noVNC)
./auraos.sh gui

## Capture a screenshot from the VM agent
./auraos.sh screenshot

## Run the full MVP test suite
./auraos.sh test

## Create and activate Python venv and install dependencies
cd auraos_daemon && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

## Add an AI provider API key (example: OpenAI)
./auraos.sh keys add openai <YOUR_OPENAI_KEY>

## Enable local Ollama (if you want to use local models)
./auraos.sh keys ollama

## Restart VM GUI services (if needed)
./auraos.sh restart

## View GUI agent logs
./auraos.sh logs

## Quick manual recovery (if desktop is down)
multipass exec auraos-multipass -- sudo pkill -9 x11vnc Xvfb || true && multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
