# AuraOS Terminal & Browser - Dual-Mode Implementation

## Overview

Two new companion applications have been created as standalone Python/tkinter applications:

1. **AuraOS Terminal** (`auraos_terminal.py`) - Dual-mode terminal interface
2. **AuraOS Browser** (`auraos_browser.py`) - Perplexity Comet-inspired AI search

Both integrate seamlessly with the existing `./auraos.sh automate` command for AI-powered automation.

---

## 1. AuraOS Terminal - Dual-Mode

### Architecture

```
┌────────────────────────────────────────┐
│      AuraOS Terminal Application       │
├────────────────────────────────────────┤
│  ⚡ AuraOS Terminal (AI Mode)          │
│  [🔄 Switch to Regular]                │
├────────────────────────────────────────┤
│                                        │
│      Chat-style Output Display         │
│      (shows AI responses and output)   │
│                                        │
├────────────────────────────────────────┤
│ ⚡ Type AI request here... [Send]      │
└────────────────────────────────────────┘
```

### Mode 1: AI Mode (Default)

**Purpose**: ChatGPT-like interface for automation tasks

**Features**:
- Natural language request input
- Integration with `./auraos.sh automate` command
- Full daemon automation support
- Command history with Up/Down navigation
- Real-time status updates

**Examples of AI Requests**:
```
⚡ open firefox
⚡ make an excel sheet with top 5 presidents by salary
⚡ create a backup of important files
⚡ find all files larger than 100MB
⚡ install python dependencies
⚡ download and extract the latest release
```

**How It Works**:
1. User types request in plain English
2. Terminal calls: `./auraos.sh automate "<request_text>"`
3. auraos.sh routes request to AI daemon
4. Results displayed with full output and status

### Mode 2: Regular Mode

**Purpose**: Standard shell terminal with AI file search integration

**Features**:
- Regular shell command execution
- AI-powered file search (prefix with `ai:`)
- Command history with Up/Down navigation
- Full bash/shell compatibility

**Command Examples**:
```
$ ls -la
$ pwd
$ git status
$ python script.py

ai: find all files suffixed by .txt
ai: find all files with more than 500 words
ai: search for config files
ai: find python files in src/
```

**How AI File Search Works**:
1. User types: `ai: find all files with .txt extension`
2. Terminal calls: `./auraos.sh automate "find files: find all files with .txt extension"`
3. auraos.sh routes to smart file search engine
4. Results displayed with file listings

### Switching Modes

- Click **🔄 Switch to Regular** button to toggle modes
- Title bar shows current mode: "⚡ AI Mode" or "$ Regular Mode"
- Prompt changes: `⚡ ` (AI) or `$ ` (Regular)
- History automatically switches between mode types

### Key Interactions

| Action | AI Mode | Regular Mode |
|--------|---------|--------------|
| Send | Calls `automate` command | Executes shell command |
| Prompt | ⚡ (green) | $ (cyan) |
| History | AI requests | Shell commands |
| Help | AI features | Shell commands |

---

## 2. AuraOS Browser - Perplexity Comet-Inspired

### Architecture

```
┌──────────────────────────────────────────────────────┐
│        AuraOS Browser - AI Search                    │
│  [🌐 Open Firefox]  🔍 Status: Ready                │
├─────────────┬──────────────────────────────────────┤
│   History   │      Search Results Display           │
│  (left)     │                                       │
│             │   • Shows AI search responses        │
│             │   • Related topics                   │
│             │   • Conversation history             │
│             │                                       │
├─────────────┴──────────────────────────────────────┤
│ 🔍 Enter search query...  [Search] [Clear]         │
└──────────────────────────────────────────────────────┘
```

### Features

**Search Interface**:
- Perplexity Comet-style chat interface
- AI-powered search recommendations
- Search history sidebar (left panel)
- Firefox integration button

**Example Searches**:
```
python tutorials
how to set up a docker container
latest news on artificial intelligence
compare python vs javascript for web development
machine learning best practices
```

**Firefox Integration**:
- Click 🌐 **Open Firefox** to launch browser
- Results can be opened in Firefox
- Conversation context maintained

### How It Works

1. User enters search query
2. Browser calls: `./auraos.sh automate "search: <query>"`
3. auraos.sh routes to search engine
4. Results displayed with:
   - Main results in center panel
   - Search history in left sidebar
   - Related topics suggestions
   - Firefox launch button

### Key Features

| Feature | Implementation |
|---------|-----------------|
| Search | subprocess call to auraos.sh automate |
| Firefox | subprocess.Popen(["firefox"]) |
| History | List maintained in memory, displayed left |
| Conversation | Chat-style output with tags |
| Status | Real-time status updates |

---

## 3. Integration with auraos.sh

### Installation Process

The `./auraos.sh vm-setup` command now:

1. **[Step 6/7]** Installs applications:
   ```bash
   # Transfer files from host to VM
   multipass transfer auraos_terminal.py "$VM_NAME:/tmp/"
   multipass transfer auraos_browser.py "$VM_NAME:/tmp/"
   
   # Copy to /opt/auraos/bin/
   # Create command launchers in /usr/local/bin/
   # Create desktop .desktop files
   ```

2. **Launchers Created**:
   ```bash
   /usr/local/bin/auraos-terminal      → calls auraos_terminal.py
   /usr/local/bin/auraos-browser       → calls auraos_browser.py
   /usr/local/bin/auraos-home          → calls auraos_homescreen.py
   ```

3. **Desktop Files Created**:
   - `~/Desktop/AuraOS_Terminal.desktop`
   - `~/Desktop/AuraOS_Browser.desktop`
   - `~/Desktop/AuraOS_Home.desktop`

### Access Methods

**From Desktop**:
- Double-click desktop icons
- Appear in XFCE application menu
- Add to taskbar

**From Command Line**:
```bash
# In VM or via multipass exec
auraos-terminal    # Launch terminal
auraos-browser     # Launch browser
auraos-home        # Launch home screen
```

**Programmatically**:
```bash
# Via auraos.sh
./auraos.sh automate "open terminal"
./auraos.sh automate "open browser"
```

---

## 4. File Specifications

### auraos_terminal.py

**Size**: ~280 lines
**Dependencies**: tkinter (Python 3)
**Entry Points**:
- GUI mode (default): `python3 auraos_terminal.py`
- CLI mode: `python3 auraos_terminal.py --cli`

**Key Classes**:
```python
class AuraOSTerminal:
    def setup_ui()           # Create widgets
    def execute()            # Process commands
    def execute_ai_task()    # Call auraos.sh automate
    def execute_shell_command() # Run shell commands
    def switch_mode()        # Toggle between modes
```

### auraos_browser.py

**Size**: ~320 lines
**Dependencies**: tkinter (Python 3), Firefox
**Entry Point**: `python3 auraos_browser.py`

**Key Classes**:
```python
class AuraOSBrowser:
    def setup_ui()           # Create widgets
    def search()             # Perform search
    def _perform_search()    # Call auraos.sh automate
    def open_firefox()       # Launch Firefox
```

---

## 5. Communication Flow

### AI Mode Request Flow

```
User Input
    ↓
execute() method
    ↓
subprocess.run(["./auraos.sh", "automate", request_text])
    ↓
auraos.sh routes to daemon
    ↓
AI daemon processes request
    ↓
Result returned to subprocess
    ↓
Display in output area (with color tags)
```

### File Search Flow

```
User Input: "ai: find .txt files"
    ↓
execute_ai_search() method
    ↓
subprocess.run(["./auraos.sh", "automate", "find files: find .txt files"])
    ↓
auraos.sh smart search engine
    ↓
File list returned
    ↓
Display results in terminal
```

---

## 6. Configuration & Logging

### Log Files

**Terminal**:
- `/tmp/auraos_terminal.log` - Terminal activity log
- Logs: STARTUP, MODE_SWITCH, AI_SUCCESS, AI_ERROR, COMMAND, SEARCH

**Browser**:
- `/tmp/auraos_browser.log` - Browser activity log
- Logs: STARTUP, SEARCH_SUCCESS, SEARCH_ERROR, FIREFOX_OPENED

### Configuration

Both applications can load from `~/.auraos/config.json`:
```json
{
  "ai_endpoint": "http://localhost:8765",
  "timeout": 60,
  "max_history": 100
}
```

---

## 7. Usage Examples

### Terminal - AI Mode

```
⚡ AuraOS Terminal (AI Mode)

⚡ open firefox
⟳ Processing request...
✓ Firefox has been opened successfully

⚡ create a backup of my documents
⟳ Processing request...
✓ Backup created: /home/user/backup_2024-01-15.tar.gz
```

### Terminal - Regular Mode

```
$ AuraOS Terminal (Regular Mode)

$ ls -la
-rw-r--r-- 1 user group  1024 Jan 15 10:30 file.txt
...

ai: find all python files in src/
🔍 Searching for: find all python files in src/
Found:
  ./src/main.py
  ./src/utils.py
  ./src/config.py
✓ Search completed
```

### Browser Search

```
🔍 AuraOS Browser

[Search box] → "python tutorials"
⟳ Searching...

Results:
• Python official tutorial (python.org)
• Real Python tutorials
• Python 3 beginner's guide
• Advanced Python concepts

Click 🌐 Open Firefox to browse
```

---

## 8. Repeatability & Reproducibility

Both applications are designed for reproducibility:

1. **Standalone Files**: `auraos_terminal.py` and `auraos_browser.py` are independent
2. **No External Dependencies**: Only use standard library + tkinter
3. **Subprocess Calls**: Use `subprocess.run()` for full traceability
4. **Integrated Logging**: All actions logged to `/tmp/*.log`
5. **Desktop Integration**: Automatically installed and available
6. **Scriptable**: Can be called from command line and scripts

### Deployment Flow

```
Local Machine:
  auraos_terminal.py → multipass transfer
                    ↓
VM /tmp/auraos_terminal.py
                    ↓
VM /opt/auraos/bin/auraos_terminal.py
                    ↓
/usr/local/bin/auraos-terminal launcher
                    ↓
Desktop icon launches application
```

---

## 9. Next Steps

### Testing the Applications

In the VM, test both applications:

```bash
# Test Terminal - AI Mode
auraos-terminal
# Type: open firefox
# Should see AI processing and Firefox launch

# Test Terminal - Regular Mode
auraos-terminal
# Click: 🔄 Switch to Regular
# Type: ls -la
# Should see file listing

# Test Browser
auraos-browser
# Type: python tutorials
# Click: 🌐 Open Firefox
```

### Extending Functionality

1. **Add new AI commands**: Update auraos.sh automate function
2. **Enhance search**: Extend browser search with custom providers
3. **Add themes**: Modify color schemes in setup_ui()
4. **Implement conversation memory**: Add persistent history to ~/.auraos/

---

## 10. Summary

Both applications are:
- ✅ **Dual-mode** (AI + Regular)
- ✅ **Desktop-integrated** (Desktop icons, XFCE menu)
- ✅ **Scriptable** (Command-line launchers)
- ✅ **Repeatable** (Standalone Python files)
- ✅ **Logged** (Full activity logging)
- ✅ **Integrated** (Use ./auraos.sh automate)

The implementations provide a complete user-facing interface for AuraOS automation and AI-powered search capabilities.
