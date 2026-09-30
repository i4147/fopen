# 🪖 WithOpen as f : "Your code's .txt guide"
> A robust, zero-dependency .txt file manager for structured automation, pipelines, and bots. Built for reliability, integrity, and confidence.
> Replacing 20+ lines of code and logic with a single one-liner.
This project started from a simple frustration:
After writing **hundreds of `with open(file) as ..` lines**, building backups, validating structures, and hacking delete filters, I realized I was reinventing the same patterns over and over.
So I made **fopen**:
A zero-dependency Python utility that treats plain `.txt` files like structured datasets. Safely and scalably.
It's **not a database**. It's a reliable, structured backend for:
* **Automations**
* **Bots**
* **CLI tools**
* **Low overhead microservices**
## 🎯 Key Capabilities
* **Structure Enforcement**: First write or append defines whether data is 1D or 2D. Future data must match.
* **CRUD Operations**: `w()` (write), `r()` (read), `a()` (append), `d()` (delete, trim, filter)
* **Multi console safe**: Handles concurrent processes to avoid corruption.
* **Backups & Snapshots**: Automatic and manual backups. Time-based snapshots.
* **Backdate**: Point the DB to a previous backup folder for reading or restoring past states. Write operations are blocked by default to prevent accidental data corruption.
* **Auto Folder Organization**: All files, backups, and snapshots are kept in structured folders. No clutter.
* **Anti-Tamper Safe Mode**: Hidden files and structure locking help protect against manual edits or file corruption.
* **Debug & Recovery**: Scan for structural errors and selectively repair.
* **Hide / Unhide**: Protect files from accidental user tampering.
* **Zero dependencies**, intuitive API, and minimal setup.
## 🔑 Core Functions
### ✅ `w()`: Write or Overwrite
```python
w(txt_name, write_list, is2d=None)
```
| Parameter    | Type             | Description                                                                                         |
| ------------ | ---------------- | --------------------------------------------------------------------------------------------------- |
| `txt_name`   | `str`            | Name of the file (without extension).                                                               |
| `write_list` | `list`           | Data to write (1D or 2D list). Overwrites existing content.                                         |
| `is2d`       | `bool` or `None` | Specify structure type on first write or when resetting. Only required if the file is new or empty. |
📝 *Use `[]` to reset file structure.*
### 📖 `r()`: Read
```python
r(txt_name, index=None, set_new=[], notify_new=True)
```
| Parameter    | Type                     | Description                                                      |
| ------------ | ------------------------ | ---------------------------------------------------------------- |
| `txt_name`   | `str`                    | Name of the file.                                                |
| `index`      | `int`, `list`, or `None` | Return only data from specific index or columns.                 |
| `set_new`    | `list`                   | If file doesn't exist, create it using this list.                |
| `notify_new` | `bool`                   | Print a message if the file was auto-created. Default is `True`. |
### ➕ `a()`: Append
```python
a(txt_name, append_list, is2d=None)
```
| Parameter     | Type             | Description                                     |
| ------------- | ---------------- | ----------------------------------------------- |
| `txt_name`    | `str`            | Name of the file.                               |
| `append_list` | `list`           | Data to append (must match existing structure). |
| `is2d`        | `bool` or `None` | Required only for new or empty files.           |
### ❌ `d()`: Delete, Filter, or Trim
```python
d(txt_name, del_list=[], index=None, cutoff=None, keep=None, reverse=False, size=None)
```
| Parameter  | Type                           | Description                                                    |
| ---------- | ------------------------------ | -------------------------------------------------------------- |
| `txt_name` | `str`                          | Name of the file.                                              |
| `del_list` | `list` or `str`                | Values to match for deletion.                                  |
| `index`    | `int`, `list`, `"*"` or `None` | Column or columns to match values in. `"*"` matches whole row. |
| `cutoff`   | `int`                          | Maximum number of deletions per value.                         |
| `keep`     | `int`                          | Retain only N matching rows.                                   |
| `reverse`  | `bool`                         | Delete from end instead of top.                                |
| `size`     | `int`                          | Trim the file to only last N rows.                             |
🧠 *You can mix and match these for precise cleanup strategies.*
## ⚙️ Installation
```bash
pip install fopen
```
## Example Workflow
```python
import fopen as f

# Write 2D data (first write locks structure)
f.w("tasks", [["Name", "Status"], ["Ping", "Done"], ["Build", "Pending"]])
# Append new row (must match shape)
f.a("tasks", [["Test", "Pending"]])
# Read all rows
print(f.r("tasks"))
# Read specific column or row
print(f.r("tasks", index=1))  # second column across all rows
print(f.r("tasks", index=[0, 2]))  # columns 0 and 2
# Delete by matching value
f.d("tasks", del_list=["Done"], index=1)
# Trim to last N rows
f.d("tasks", size=3)
# Backup and snapshot
f.backup("tasks")
f.snapshot("tasks", unit="h", gap=4)
# Backdate to a previous backup state (read-only by default)
f.backdate(recency=1)  # point DB to latest backup, writes blocked
f.backdate(recency=2, write=True)  # point DB to second latest, writes allowed
f.backdate(recency=0)  # return to live DB
# Debug or fix structure errors
f.debug("tasks", is2d=True, length=2)
# Hide or unhide
f.hide("tasks")
f.unhide("tasks")
```
## 📋 Data Models: 1D and 2D
| Mode   | Example                                       | Notes                                     |
| ------ | --------------------------------------------- | ----------------------------------------- |
| **1D** | `["apple", "banana", "pear"]`                 | Use `is2d=False` on first write or append |
| **2D** | `[["user","score"], ["alice",10], ["bob",8]]` | Use `is2d=True` on first write or append  |
To reset structure (clear file):
```python
f.w("filename", [], is2d=None)
```
## 🧹 Deletion and Filtering
`d()` is versatile. Combine arguments:
* `del_list` (values or rows)
* `index` (column index, list of indices, or `"*"` for full row)
* `cutoff` (max deletes per value)
* `keep` (retain only N matches)
* `reverse` (delete from end)
* `size` (keep only last N rows)
### Examples
**Delete rows where status is "Done":**
```python
f.d("tasks", del_list=["Done"], index=1)
```
**Delete a full exact row:**
```python
f.d("tasks", del_list=[["Ping", "Done"]], index="*")
```
**Trim to last 5 rows:**
```python
f.d("tasks", size=5)
```
**Keep only N occurrences of a value:**
```python
f.d("tasks", del_list=["Pending"], index=1, keep=2)
```
## 🔢 Index Matching Patterns
### 1. Match by Single Index (Column)
```python
f.d("tasks", del_list=["Pending"], index=1)
```
*Deletes all rows where column `1` (status) is `"Pending"`.*
### 2. Match by Multiple Indexes (Multi-Column Logic)
```python
f.d("tasks", del_list=[["Fix Bug", "High"]], index=[0, 2])
```
*Deletes rows where column `0` is `"Fix Bug"` and column `2` is `"High"`.*
### 3. Match Entire Row
```python
f.d("tasks", del_list=[["Fix Bug", "Done", "Low"]], index="*")
```
*Deletes exact row match across all columns.*
### 4. Match Multiple Rows by Value in a Column
```python
f.d("tasks", del_list=[["Deploy"], ["Write Docs"]], index=0)
```
*Deletes any row where column `0` (task name) matches `"Deploy"` or `"Write Docs"`.*
### 5. Selective Cutoff Deletes
```python
f.d("tasks", del_list=["Pending"], index=1, cutoff=2)
```
*Deletes only the first 2 rows where column `1` is `"Pending"`.*
### 6. Reverse Delete
```python
f.d("tasks", del_list=["Done"], index=1, reverse=True)
```
*Deletes from the bottom up, not top-down.*
### 7. Trim by Row Count (No `index`)
```python
f.d("tasks", size=5)
```
*Keeps only the last 5 rows. Trims the rest.*
## 🛠 Debugging and Recovery
When a file's structure is compromised:
```python
debug("tasks", is2d=True, length=2)
```
* Flags bad rows and optionally cleans them.
* Use majority-vote backups to restore when corruption occurs.
## 📁 Backups, Snapshots, and Backdate
WithOpen supports three different recovery systems:
| Feature      | Purpose                                             |
| ------------ | --------------------------------------------------- |
| `backup()`   | Manual version checkpoint                           |
| `snapshot()` | Automated timed backups                             |
| `backdate()` | Temporarily switch the active DB to an older backup |
---
### 💾 `backup()`
Creates a manual backup copy of a file or the entire package state.
```python
f.backup("tasks")
```
Backups are stored in:
```text
WithOpen All Backups/
```
Each backup folder is timestamped:
```text
2026-06-01_03-44-11_WithOpen
```
Useful before:
* major deletes
* bulk writes
* migrations
* automation runs
---
### 📸 `snapshot()`
Creates automatic time-based snapshots.
```python
f.snapshot("tasks", unit="h", gap=4)
```
Example:
* every 4 hours
* only if enough time passed since last snapshot
Supported units:
| Unit   | Meaning |
| ------ | ------- |
| `'s'`  | seconds |
| `'m'`  | minutes |
| `'h'`  | hours   |
| `'d'`  | days    |
| `'mo'` | months  |
| `'y'`  | years   |
Optional controls:
| Parameter | Purpose                  |
| --------- | ------------------------ |
| `trim`    | limit snapshot row count |
| `begin`   | delay first snapshot     |
Snapshots are useful for:
* long-running bots
* automation scripts
* logging systems
* CLI tools
* recovery checkpoints
---
# ⏪ `backdate()`: Time Travel for Your DB
```python
f.backdate(recency=1)
```
`backdate()` does NOT restore or overwrite files.
Instead, it changes which package folder the API reads and writes from.
Think of it like changing the active database pointer.
---
## 🧠 How It Works
Normally all operations use:
```text
WithOpen/
```
Example:
```python
f.r("tasks")
f.w("tasks", data)
f.a("tasks", data)
```
By default these point to:
```text
WithOpen/tasks/
```
---
After:
```python
f.backdate(recency=1)
```
the active package becomes:
```text
WithOpen All Backups/2026-06-01_03-44-11_WithOpen/
```
Now ALL future operations automatically use that backup instead:
```python
f.r("tasks")
f.a("tasks", data)
f.d("tasks")
```
These now point to:
```text
WithOpen All Backups/.../tasks/
```
without changing your code.
---
## 🔁 Persistent Active Path
The active package path is stored internally using a hidden control file.
This means the selected backup remains active even after:
* restarting Python
* rerunning scripts
* importing from another module
* multiprocessing
* console changes
This behavior is intentional.
---
## 🔢 Recency Rules
| Value  | Meaning               |
| ------ | --------------------- |
| `1`    | latest backup         |
| `2`    | second latest backup  |
| `3`    | third latest backup   |
| `0`    | reset back to live DB |
| `None` | reset back to live DB |
Examples:
```python
f.backdate(recency=1)
```
Use latest backup.
```python
f.backdate(recency=3)
```
Use third latest backup.
```python
f.backdate(recency=0)
```
Return to live database.
---
## ⚠️ Important Behavior
`backdate()` affects ALL future operations globally.
By default (`write=False`), any multi-backup write attempt outside the active package will be **blocked and force-shutdown the app**:
```python
f.backdate(recency=1)
f.w("tasks", data)  # 🛑 blocked — write=False by default
```
To allow writes into the backup folder, set `write=True`:
```python
f.backdate(recency=1, write=True)
f.w("tasks", data)  # ✅ allowed
```
Internal system writes (`single_write=True`) such as active path and lock state updates are always allowed regardless of the lock.
If you switch back to the main package while the lock is active, the lock is **automatically cleared**:
```python
f.backdate(recency=0)  # resets to live DB, lock always cleared
```
---
## ✅ Common Workflow
### Inspect old data (safe, read-only)
```python
f.backdate(recency=2)
print(f.r("tasks"))
```
---
### Restore live mode
```python
f.backdate(recency=0)
```
---
### Compare current vs old state
```python
f.backdate(recency=0)
live = f.r("tasks")
f.backdate(recency=1)
old = f.r("tasks")
```
---
### Experiment safely in a backup
```python
f.backdate(recency=1, write=True)
f.d("tasks", del_list=["Done"], index=1)  # modifies backup, not live DB
f.backdate(recency=0)  # return to live when done
```
---
## 🛡️ Safety Advantage
Unlike traditional restore systems:
* no files are overwritten
* no irreversible rollback happens
* no restore copy is required
You simply switch the active package context.
This makes recovery safer and nearly instant.
Backups and snapshots are stored in structured subfolders.
## 🔐 Hide or Unhide Files
* `hide("tasks")`: prevents accidental edits or reads
* `unhide("tasks")`: makes file visible again
* Use `"*"` to hide or unhide all files
## 🧠 Best Practices
1. Always use the API (`w`, `a`, `r`, `d`) and avoid manual edits.
2. Run `debug()` periodically for long-lived files.
3. Use `snapshot()` in scripts that run continuously.
4. Use `backdate()` to read or inspect data from a previous backup state — writes are blocked by default.
5. Use `hide()` when bundling scripts to protect internal files.
6. Reset structure if your shape definition changes (with `w("file", [])`).
## 🔧 Utility Functions
### 🖥️ `consoles()`: Console Mode Config
```python
f.consoles(txt_name, multiple=True, alert=True)
```
Sets console interaction mode for:
* Multiple scripts
* Multiple tabs
* Bots and automation tools
Ensures safe concurrent access by coordinating file locks per console context.
Use this when your files are read or written by multiple parallel environments.
---
### 🔕 `warning()`: Enable or Disable Read Alerts
```python
f.warning(alert=False)
```
Turns on or off the warning that appears when reading a file outside of console safe mode.
Useful for bots or CI/CD logs where alerts aren't needed.
---
### ⏪ `backdate(recency, write=False, display=True)`
Points the DB to a previous backup folder instead of the live main package.
Useful for inspecting or restoring past states without touching current data.
| Parameter | Type   | Description                                                                   |
| --------- | ------ | ----------------------------------------------------------------------------- |
| `recency` | `int`  | How many backups ago. `1` = latest, `2` = second latest, etc.                 |
| `write`   | `bool` | Whether to allow write operations while in backup mode. Default is `False`.   |
| `display` | `bool` | Whether to print the updated path. Default is `True`.                         |
```python
f.backdate(recency=1)  # read-only, latest backup
f.backdate(recency=1, write=True)  # allow writes into backup folder
f.backdate(recency=3, display=False)  # silent, third latest, read-only
f.backdate(recency=0)  # return to live DB, lock cleared
```
⚠️ *This overrides the active package path globally. Call `f.backdate(0)` to return to live data.*
---
### 🗑️ `remove(txt_name, display=True)`
Deletes the target file along with all backups and snapshots.
⚠️ Use with caution. This is irreversible.
### ℹ️ `info(txt_name, display=True)`
Returns metadata such as structure type, total rows, shape, and last modified time.
### 🧪 `debug(txt_name, is2d=None, length=None, display=True)`
Scans for structure issues like row length mismatches or corrupted lines.
Can auto-fix when used with `length` or `is2d`.
### 📂 `listdir(display=True)`
Lists all structured text files currently being tracked.
### 🆘 `help()`
Prints a quick-reference summary of all available functions and parameters.
Great for in-terminal use.
## 📄 License
This project is licensed under the **MIT License**.
Use freely, modify, share. No warranties.