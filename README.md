# TaskFlow

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

A small command-line task manager written in **pure Python** (standard library only, no dependencies).
Tasks are saved to a JSON file, so they persist between runs.

## Features

- Add tasks with a **priority** (`low`, `medium`, `high`), **due date** and **tags**
- List tasks, filtered by status, priority or tag, and sorted by id, priority or due date
- Mark tasks as done, delete them, or clear all completed tasks
- Search by keyword (titles and tags)
- Summary statistics, with overdue tasks flagged automatically
- Friendly error messages and proper exit codes (no raw tracebacks for user mistakes)

## Requirements

Python 3.9 or newer. Nothing else to install.

## Quick start

```bash
git clone https://github.com/<your-username>/taskflow-cli.git
cd taskflow-cli

python -m taskflow add "Finish portfolio README" -p high -t career -d 2030-01-01
python -m taskflow add "Buy groceries" -t home -d 2000-01-01
python -m taskflow add "Practice Python" -p low -t career
python -m taskflow done 1
python -m taskflow list
```

Output:

```text
[x]   1. Finish portfolio README  (high)  due 2030-01-01  #career
[ ]   2. Buy groceries  (medium)  due 2000-01-01 OVERDUE  #home
[ ]   3. Practice Python  (low)  #career

3 task(s)
```

Optional: install it so you can type `taskflow` instead of `python -m taskflow`:

```bash
pip install .
```

## Commands

| Command | Example |
| --- | --- |
| `add` | `taskflow add "Write report" -p high -d tomorrow -t work -t urgent` |
| `list` | `taskflow list --status pending --sort due` |
| `done` | `taskflow done 3` |
| `delete` | `taskflow delete 3` |
| `search` | `taskflow search report` |
| `stats` | `taskflow stats` |
| `clear` | `taskflow clear` |

Dates accept `YYYY-MM-DD`, `today` or `tomorrow`. Run `taskflow --help` or `taskflow <command> --help` for all options.

By default tasks are stored in `~/.taskflow/tasks.json`. Change this with the `TASKFLOW_FILE`
environment variable or the `--file` option (placed before the command):

```bash
taskflow --file ./work-tasks.json list
```

## Project structure

```text
taskflow/
  models.py    Task dataclass and Priority enum
  storage.py   JSON persistence with atomic writes
  manager.py   Business logic (add, complete, filter, sort, search, stats)
  cli.py       argparse command-line interface
tests/         56 unit tests (unittest)
```

The code is split into layers (models, storage, logic, interface) so each part can be tested on its own.

## Running the tests

```bash
python -m unittest discover -v
```

## What this project demonstrates

- Type hints and dataclasses
- Enums and input validation
- Separation of concerns across modules
- Safe file handling (atomic writes, clear errors for corrupt files)
- A command-line interface built with `argparse`
- Automated tests and continuous integration with GitHub Actions

## License

MIT, see [LICENSE](LICENSE).
