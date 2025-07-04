# commands/README.md

This directory contains modular command scripts for AuraOS AI.

- Each subfolder or script represents a general or specific command.
- The AI should check here for reusable logic before generating new scripts.
- New commands can be added as the system learns new tasks.

Example structure:

file/
  list.py
  search.py
system/
  info.py
  update.py
web/
  fetch.py

All command modules should:
- Accept arguments from stdin or command line
- Print results to stdout
- Be as general as possible, but allow for specialization
