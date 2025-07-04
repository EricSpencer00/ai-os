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

        # Ensure git repo
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=False)
            subprocess.run(["git", "add", "daemon.py"], check=False)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=False)

        # Commit current daemon.py before upgrade
        subprocess.run(["git", "add", "daemon.py"], check=False)
        subprocess.run(["git", "commit", "-m", "[updater] Backup before self-upgrade"], check=False)
        subprocess.run(["git", "tag", "backup-before-upgrade"], check=False)

        if os.path.exists("daemon.py"):
            os.rename("daemon.py", "daemon_backup.py")

        with open("daemon.py", "w") as f:
            f.write(code)

        # Run test suite
        print("[Updater] Running test suite...")
        test_result = subprocess.run(["sh", "test_execute_script.sh"], capture_output=True, text=True)
        print(test_result.stdout)
        print(test_result.stderr)
        if test_result.returncode != 0:
            print("[Updater] Tests failed! Rolling back...")
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=False)
            os.execvp("python3", ["python3", "daemon.py"])
            return
        else:
            print("[Updater] Tests passed. Committing new version.")
            subprocess.run(["git", "add", "daemon.py"], check=False)
            subprocess.run(["git", "commit", "-m", "[updater] Self-upgrade successful"], check=False)
            subprocess.run(["git", "tag", "upgrade-success"], check=False)

        print("[Updater] Relaunching daemon.py...")
        os.execvp("python3", ["python3", "daemon.py"])
    except Exception as e:
        print(f"[Updater] Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
