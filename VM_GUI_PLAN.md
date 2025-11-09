VM GUI & Automation Plan

Goal: create a graphical Ubuntu VM that runs the AuraOS stack, exposes a desktop for user interaction, supports screen-reading (accessibility), and provides deterministic automation (ability to read the screen and execute UI behaviors on the user's behalf).

High-level components

1) Desktop environment
   - Install a lightweight desktop: XFCE or MATE (xfce4 recommended for low weight).
   - Install a display server: Wayland/X11 (X11 with Xfce is simplest for automation).
   - Enable auto-login for a dedicated automation user or start a session via systemd.

2) Remote display / interactive access
   - Provide VNC service (x11vnc or tigervnc) for remote GUI access.
   - Optionally install a desktop-sharing agent (noVNC) that exposes a browser-accessible console.

3) Accessibility / Screen-reading
   - Install Orca screen reader (GNOME Orca) and speech-dispatcher or espeak-ng for TTS.
   - Configure Orca to start automatically with the desktop session for the automation user.
   - Alternatively provide an API-based TTS and OCR pipeline for headless readback.

4) Screen capture and OCR
   - Install and configure a screen-capture tool (scrot, maim) and Tesseract OCR.
   - Use OCR to inspect UI elements when accessibility hooks aren't available.

5) Automation agent
   - Python-based agent inside VM that:
     - Reads UI text via accessibility APIs (AT-SPI/Orca) when available.
     - Falls back to screen capture + OCR when needed.
     - Sends input events via xdotool, python-xlib, or PyAutoGUI.
     - Exposes a local REST API (Flask/FastAPI) to receive high-level commands from host or other services.
   - Agent will run with user privileges and can call sudo for system-level tasks when necessary.

6) Security and sandboxing
   - Restrict network access for the VM if required.
   - Use an explicit API key for the automation agent's REST endpoint.
   - Configure sudoers carefully to limit commands that the agent can run without password.

7) Integration hooks
   - Add cloud-init steps to `vm_resources/bootstrap.sh` (or a new `gui-bootstrap.sh`) to install desktop, VNC, Orca, agent, and enable services.
   - Provide a host-side helper to forward ports, start noVNC, and print access URLs.

Implementation steps (incremental)

A. Minimal GUI + manual test (fast)
   1. Modify `bootstrap.sh` to install `xfce4`, `x11vnc`, `xdotool`, `tesseract-ocr`, `python3-venv`, `python3-pip`, `espeak-ng`.
   2. Add a systemd user service for the automation agent that starts on login.
   3. Build a basic Python agent that can capture a screenshot and run Tesseract, and simulate a click via xdotool.
   4. Boot VM and manually test: VNC in, run agent commands, verify input injection and OCR output.

B. Accessibility-first (preferred)
   1. Install Orca and ensure AT-SPI is available for XFCE.
   2. Modify the agent to use pyatspi or dbus to read UI element text and actions.
   3. Prefer AT-SPI over OCR when text is available.

C. Polishing and UX
   1. Add noVNC to expose the desktop in a browser.
   2. Provide host wrappers: `open_vm_gui.sh` to start noVNC and open browser.
   3. Document how to secure the agent (API key, firewall rules).

D. Optional: Headless fast-path
   - For automation tasks that don't need full desktop, provide a headless agent that uses CLI tools and avoids heavyweight desktop packages.

Deliverables
- cloud-init-enabled `gui-bootstrap.sh` or additions to `vm_resources/bootstrap.sh` that install desktop and agent
- `start_vm_with_multipass.sh` already exists as a reliable launcher on macOS — update it to accept a `--gui` flag that triggers GUI bootstrap.
- `vm_resources/gui_agent/` python agent skeleton (screenshots, OCR, xdotool bindings, REST API)
- `VM_GUI_PLAN.md` (this file)

Risks and caveats
- GUI/Orca integration can be subtle on non-GNOME desktops; XFCE works but may need tweaks to AT-SPI services.
- Running a screen-reading agent that simulates input is potentially risky — secure the REST API and consider offline mode.
- OCR is imperfect; prefer accessibility APIs when available.

Next steps I can implement now
1. Update `start_vm_and_bootstrap.sh` to accept a `--gui` flag and pass it to the multipass cloud-init (or QEMU seed generation).
2. Add a minimal `gui-bootstrap.sh` that installs XFCE, x11vnc, tesseract, xdotool, and a tiny Python agent.
3. Launch a Multipass VM with `--cloud-init gui-bootstrap.sh` and validate the VNC/agent.

Tell me which of the next steps to implement first (I'd start with step 1 and 2).