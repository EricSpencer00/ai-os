"""
VM Manager plugin for AuraOS Autonomous AI Daemon v8
Manages QEMU virtual machines with ARM64 support for M1 Macs
Handles VM lifecycle, execution isolation, and automation
"""
import os
import json
import subprocess
import time
import logging
import paramiko
from flask import jsonify
from pathlib import Path

# Load config for VM settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    VM_CONFIG = config.get("VM", {})
except Exception:
    VM_CONFIG = {}

# Default VM configuration
VM_BASE_DIR = os.path.expanduser('~/AuraOS_VMs')
VM_IMAGES_DIR = os.path.join(VM_BASE_DIR, 'images')
VM_SSH_PORT = 2222
VM_SSH_USER = 'auraos'
VM_SSH_PASSWORD = 'auraos123'

# Ensure VM directories exist
os.makedirs(VM_BASE_DIR, exist_ok=True)
os.makedirs(VM_IMAGES_DIR, exist_ok=True)


class VMInstance:
    """Represents a running VM instance"""
    def __init__(self, name, pid, ssh_port, vnc_port=None):
        self.name = name
        self.pid = pid
        self.ssh_port = ssh_port
        self.vnc_port = vnc_port
        self.process = None
    
    def is_running(self):
        """Check if VM process is still running"""
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False
    
    def stop(self):
        """Stop the VM"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
            else:
                os.kill(self.pid, 15)  # SIGTERM
            logging.info(f"VM {self.name} stopped")
            return True
        except Exception as e:
            logging.error(f"Error stopping VM {self.name}: {e}")
            return False


class Plugin:
    name = "vm_manager"
    
    def __init__(self):
        self.running_vms = {}  # name -> VMInstance
        self.vm_state_file = os.path.join(VM_BASE_DIR, 'vm_state.json')
        self._load_state()
    
    def _load_state(self):
        """Load VM state from disk"""
        if os.path.exists(self.vm_state_file):
            try:
                with open(self.vm_state_file, 'r') as f:
                    state = json.load(f)
                    for name, vm_data in state.get('vms', {}).items():
                        vm = VMInstance(
                            name=vm_data['name'],
                            pid=vm_data['pid'],
                            ssh_port=vm_data['ssh_port'],
                            vnc_port=vm_data.get('vnc_port')
                        )
                        if vm.is_running():
                            self.running_vms[name] = vm
                        else:
                            logging.info(f"VM {name} was running but is now stopped")
            except Exception as e:
                logging.error(f"Error loading VM state: {e}")
    
    def _save_state(self):
        """Save VM state to disk"""
        try:
            state = {
                'vms': {
                    name: {
                        'name': vm.name,
                        'pid': vm.pid,
                        'ssh_port': vm.ssh_port,
                        'vnc_port': vm.vnc_port
                    }
                    for name, vm in self.running_vms.items()
                }
            }
            with open(self.vm_state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logging.error(f"Error saving VM state: {e}")
    
    def generate_script(self, intent, context):
        """Generate VM management script from intent"""
        intent_lower = intent.lower()
        
        # Classify VM intent
        if any(k in intent_lower for k in ["create vm", "new vm", "setup vm", "make vm"]):
            return self._generate_create_vm_script(intent, context)
        elif any(k in intent_lower for k in ["start vm", "launch vm", "run vm"]):
            return self._generate_start_vm_script(intent, context)
        elif any(k in intent_lower for k in ["stop vm", "shutdown vm", "kill vm"]):
            return self._generate_stop_vm_script(intent, context)
        elif any(k in intent_lower for k in ["list vm", "show vm", "vms"]):
            return self._generate_list_vms_script(intent, context)
        elif any(k in intent_lower for k in ["execute in vm", "run in vm", "vm execute"]):
            return self._generate_vm_execute_script(intent, context)
        else:
            # Default: provide VM help
            help_text = """
VM Manager Commands:
- create vm <name> [ubuntu/debian/alpine] - Create new VM
- start vm <name> - Start existing VM
- stop vm <name> - Stop running VM
- list vms - Show all VMs
- execute in vm <name>: <command> - Run command in VM
"""
            return jsonify({"script_type": "info", "script": help_text}), 200
    
    def _generate_create_vm_script(self, intent, context):
        """Generate script to create a new VM"""
        # Extract VM name and OS from intent
        parts = intent.lower().replace("create vm", "").strip().split()
        vm_name = parts[0] if parts else "auraos-vm-1"
        os_type = parts[1] if len(parts) > 1 else "ubuntu"
        
        script = f"""
# VM Creation Script for {vm_name}
echo "Creating VM: {vm_name} (OS: {os_type})"
echo "This will set up a QEMU ARM64 virtual machine"
echo "Note: You need to download the OS image first"
echo ""
echo "For Ubuntu ARM64:"
echo "  curl -L https://cdimage.ubuntu.com/releases/22.04/release/ubuntu-22.04.3-live-server-arm64.iso -o ~/AuraOS_VMs/images/ubuntu-arm64.iso"
echo ""
echo "VM will be configured with:"
echo "  - 2GB RAM"
echo "  - 20GB disk"
echo "  - SSH on port {VM_SSH_PORT}"
echo "  - VNC on port 5900"
"""
        return jsonify({"script_type": "shell", "script": script, "vm_action": "create", "vm_name": vm_name}), 200
    
    def _generate_start_vm_script(self, intent, context):
        """Generate script to start a VM"""
        parts = intent.lower().replace("start vm", "").strip().split()
        vm_name = parts[0] if parts else "auraos-vm-1"
        
        script = f"echo 'Starting VM: {vm_name}'"
        return jsonify({"script_type": "vm_start", "script": script, "vm_name": vm_name}), 200
    
    def _generate_stop_vm_script(self, intent, context):
        """Generate script to stop a VM"""
        parts = intent.lower().replace("stop vm", "").strip().split()
        vm_name = parts[0] if parts else "auraos-vm-1"
        
        script = f"echo 'Stopping VM: {vm_name}'"
        return jsonify({"script_type": "vm_stop", "script": script, "vm_name": vm_name}), 200
    
    def _generate_list_vms_script(self, intent, context):
        """Generate script to list VMs"""
        vm_list = []
        for name, vm in self.running_vms.items():
            status = "running" if vm.is_running() else "stopped"
            vm_list.append(f"  - {name}: {status} (SSH port: {vm.ssh_port})")
        
        if vm_list:
            script = "Running VMs:\n" + "\n".join(vm_list)
        else:
            script = "No VMs currently running"
        
        return jsonify({"script_type": "info", "script": script}), 200
    
    def _generate_vm_execute_script(self, intent, context):
        """Generate script to execute command in VM"""
        # Parse "execute in vm <name>: <command>"
        if ":" in intent:
            vm_part, command = intent.split(":", 1)
            parts = vm_part.lower().replace("execute in vm", "").strip().split()
            vm_name = parts[0] if parts else "auraos-vm-1"
            command = command.strip()
        else:
            vm_name = "auraos-vm-1"
            command = "echo 'No command specified'"
        
        script = f"echo 'Executing in VM {vm_name}: {command}'"
        return jsonify({
            "script_type": "vm_execute",
            "script": script,
            "vm_name": vm_name,
            "vm_command": command
        }), 200
    
    def execute(self, script, context):
        """Execute VM management commands"""
        # Extract action from context or script
        script_type = context.get('script_type', 'shell') if context else 'shell'
        
        if script_type == "vm_start":
            vm_name = context.get('vm_name', 'auraos-vm-1')
            return self._start_vm(vm_name)
        elif script_type == "vm_stop":
            vm_name = context.get('vm_name', 'auraos-vm-1')
            return self._stop_vm(vm_name)
        elif script_type == "vm_execute":
            vm_name = context.get('vm_name', 'auraos-vm-1')
            command = context.get('vm_command', '')
            return self._execute_in_vm(vm_name, command)
        elif script_type == "info":
            return jsonify({"output": script}), 200
        else:
            # Execute as regular shell script
            try:
                result = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=30)
                return jsonify({
                    "output": result.stdout if result.returncode == 0 else result.stderr,
                    "returncode": result.returncode
                }), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    def _start_vm(self, vm_name):
        """Start a QEMU ARM64 VM"""
        try:
            # Check if already running
            if vm_name in self.running_vms and self.running_vms[vm_name].is_running():
                return jsonify({"error": f"VM {vm_name} is already running"}), 400
            
            # VM disk image path
            vm_disk = os.path.join(VM_IMAGES_DIR, f"{vm_name}.qcow2")
            
            # Check if disk exists, if not create it
            if not os.path.exists(vm_disk):
                logging.info(f"Creating disk image for {vm_name}")
                subprocess.run([
                    "qemu-img", "create", "-f", "qcow2", vm_disk, "20G"
                ], check=True)
            
            # Find available SSH port
            ssh_port = VM_SSH_PORT
            while any(vm.ssh_port == ssh_port for vm in self.running_vms.values()):
                ssh_port += 1
            
            # Find available VNC port
            vnc_port = 5900
            while any(vm.vnc_port == vnc_port for vm in self.running_vms.values()):
                vnc_port += 1
            
            # Build QEMU command for ARM64
            qemu_cmd = [
                "qemu-system-aarch64",
                "-M", "virt",
                "-cpu", "cortex-a72",
                "-m", "2048",
                "-smp", "2",
                "-drive", f"file={vm_disk},if=virtio,format=qcow2",
                "-device", "virtio-net-pci,netdev=net0",
                "-netdev", f"user,id=net0,hostfwd=tcp::{ssh_port}-:22",
                "-vnc", f":{vnc_port - 5900}",
                "-nographic" if VM_CONFIG.get('headless', True) else "",
            ]
            
            # Remove empty strings
            qemu_cmd = [c for c in qemu_cmd if c]
            
            logging.info(f"Starting VM {vm_name} with command: {' '.join(qemu_cmd)}")
            
            # Start VM in background
            process = subprocess.Popen(
                qemu_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Create VM instance
            vm = VMInstance(vm_name, process.pid, ssh_port, vnc_port)
            vm.process = process
            self.running_vms[vm_name] = vm
            self._save_state()
            
            # Wait a bit to ensure it started
            time.sleep(2)
            
            if vm.is_running():
                return jsonify({
                    "output": f"VM {vm_name} started successfully\nSSH: localhost:{ssh_port}\nVNC: localhost:{vnc_port}",
                    "vm_name": vm_name,
                    "ssh_port": ssh_port,
                    "vnc_port": vnc_port,
                    "pid": process.pid
                }), 200
            else:
                return jsonify({"error": f"VM {vm_name} failed to start"}), 500
            
        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"QEMU error: {e.stderr}"}), 500
        except FileNotFoundError:
            return jsonify({
                "error": "QEMU not found. Please install: brew install qemu",
                "install_command": "brew install qemu"
            }), 500
        except Exception as e:
            logging.error(f"Error starting VM: {e}")
            return jsonify({"error": str(e)}), 500
    
    def _stop_vm(self, vm_name):
        """Stop a running VM"""
        try:
            if vm_name not in self.running_vms:
                return jsonify({"error": f"VM {vm_name} is not running"}), 400
            
            vm = self.running_vms[vm_name]
            if vm.stop():
                del self.running_vms[vm_name]
                self._save_state()
                return jsonify({"output": f"VM {vm_name} stopped successfully"}), 200
            else:
                return jsonify({"error": f"Failed to stop VM {vm_name}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _execute_in_vm(self, vm_name, command):
        """Execute a command inside a VM via SSH"""
        try:
            if vm_name not in self.running_vms:
                return jsonify({"error": f"VM {vm_name} is not running"}), 400
            
            vm = self.running_vms[vm_name]
            
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                # Connect to VM
                ssh.connect(
                    'localhost',
                    port=vm.ssh_port,
                    username=VM_SSH_USER,
                    password=VM_SSH_PASSWORD,
                    timeout=10
                )
                
                # Execute command
                stdin, stdout, stderr = ssh.exec_command(command)
                output = stdout.read().decode()
                error = stderr.read().decode()
                exit_status = stdout.channel.recv_exit_status()
                
                ssh.close()
                
                if exit_status == 0:
                    return jsonify({
                        "output": output,
                        "vm_name": vm_name,
                        "command": command
                    }), 200
                else:
                    return jsonify({
                        "error": error,
                        "output": output,
                        "vm_name": vm_name,
                        "command": command
                    }), 500
                    
            except paramiko.AuthenticationException:
                return jsonify({
                    "error": "SSH authentication failed. Ensure VM is configured with correct credentials.",
                    "hint": f"Expected user: {VM_SSH_USER}, password: {VM_SSH_PASSWORD}"
                }), 500
            except Exception as e:
                return jsonify({
                    "error": f"SSH connection error: {str(e)}",
                    "hint": "VM may still be booting. Wait a few minutes and try again."
                }), 500
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def cleanup(self):
        """Cleanup all running VMs"""
        logging.info("Cleaning up VMs...")
        for vm_name in list(self.running_vms.keys()):
            self._stop_vm(vm_name)
