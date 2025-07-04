# updater.py
import base64, json, subprocess, sys, os

def main():
    if len(sys.argv) != 2:
        print("Usage: updater.py <base64_payload>")
        exit(1)
    try:
        payload = json.loads(base64.b64decode(sys.argv[1]))
        code = payload["code"]
        packages = payload.get("packages", [])

        print("[Updater] Installing packages:", packages)
        for p in packages:
            subprocess.run(["pip3", "install", p], check=False)

        if os.path.exists("daemon.py"):
            os.rename("daemon.py", "daemon_backup.py")

        with open("daemon.py", "w") as f:
            f.write(code)

        print("[Updater] Relaunching daemon.py...")
        os.execvp("python3", ["python3", "daemon.py"])
    except Exception as e:
        print(f"[Updater] Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
