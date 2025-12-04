30 Basic Terminal Tasks for AI-to-Bash testing

1. Show current working directory
2. List files in the current directory (long listing)
3. Show hidden files
4. List Python files recursively
5. Count number of lines in a file `README.md`
6. Show first 10 lines of `README.md`
7. Show disk usage of current directory
8. Show free disk space
9. Show `python` version
10. Show `python3` version
11. Install `requests` into user site (pip)
12. Show active network interfaces
13. Ping `8.8.8.8` once
14. Show top 5 memory-consuming processes
15. Show last 200 lines of `debug_logs.md` (if present)
16. Search for "TODO" in repository
17. Count files in repository
18. Find large files (>10M)
19. Show available package updates (apt-get) [non-destructive]
20. Print environment variables related to PATH
21. Show git branch and latest commit
22. Create a directory `tmp_test_dir` (non-destructive)
23. Remove the created `tmp_test_dir` (only if exists and empty)
24. Show installed pip packages (user)
25. Show Node.js version
26. List listening TCP ports
27. Show last reboot time
28. Display kernel uname info
29. Show contents of `/etc/passwd` (read-only)
30. Run shell command to check if port 8081 is open locally

Notes:
- Tests will validate commands without executing destructive actions.
- When possible, prefer non-destructive flags (e.g., `--version`, `-n`, `-v`) and avoid interactive commands.
