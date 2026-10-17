# SmallBrain

[한국어](README.ko.md)

A Claude Code plugin that turns an Obsidian vault into a shared brain for a supervisor (your main session) and its sub-agents.

Agents don't have to remember to read or write notes. Hooks inject the right context when an agent starts, enforce who may write where, and refuse to let an agent finish without leaving a record.

## How it works

| Hook | What it does |
|---|---|
| `SessionStart` | Gives the supervisor the current goal, the human status page, open threads, and its rules |
| `SubagentStart` | Gives each hired agent a short digest: current goal, its role, its principles, threads waiting for it, write rules |
| `PreToolUse` | Checks vault writes by `agent_type`: an agent may only create new files in its own `journal/`, `reflections/`, and its own thread turns. Requires frontmatter; a reflection needs a `signal` |
| `SubagentStop` | Blocks an agent from finishing (once) if it left no journal or turn |
| `Stop` | Rebuilds the index, archives approvals pending over 7 days, and asks the supervisor to update `03_status.md` if the vault changed |

## Requirements

- Claude Code with plugin support
- `python3` (standard library only)
- Obsidian is optional. It is only for you to read the vault

## Install

Load it locally from the folder you want to use it in:

```bash
cd your-project
claude --plugin-dir /path/to/smallbrains
```

## Usage

### 1. Create the vault

```
/smallbrain:init
```

Creates `vault/` in the project and asks for the project goal. To use another location, set `SMALLBRAIN_VAULT` (relative to the project root).

### 2. Hire agents

```
/smallbrain:hire builder Implements features
/smallbrain:hire reviewer Reviews code and tests
```

Each call creates `.claude/agents/<name>.md` and `vault/10_agents/NN_<name>/`. Restart the session if a new agent doesn't show up.

### 3. Work as usual

Give the supervisor a task, for example "Build the login page". It delegates to the hired agents, and the hooks handle context injection and record keeping.

### 4. Hold a meeting when you need several opinions

```
/smallbrain:meeting Choose the auth method
```

The supervisor opens a thread in `vault/20_threads/`, runs up to 3 rounds where each agent writes its own turn file, then records the decision in `40_knowledge/41_decisions/`.

### 5. Promote lessons

```
/smallbrain:reflect
```

When the same lesson appears twice in an agent's `reflections/`, the supervisor turns it into a principle (`status: trial`). A principle that conflicts with an existing one becomes `pending-approval` and shows up on your status page.

### 6. Check the status

Open `vault/00_system/03_status.md` in Obsidian. It has three sections: current state, recent work, and decisions waiting for you. Approve or reject pending principles there. Anything left pending for 7 days is archived automatically.

## Vault layout

```
vault/
├─ 00_system/
│  ├─ 00_index.md      # generated, do not edit
│  ├─ 01_rules.md      # vault rules
│  ├─ 02_now.md        # for agents: goal, progress, next steps
│  └─ 03_status.md     # for you: overwritten by the supervisor
├─ 10_agents/NN_<name>/
│  ├─ profile.md       # role
│  ├─ principles/      # promoted principles (supervisor only)
│  ├─ reflections/     # lessons from failure signals
│  └─ journal/         # work records
├─ 20_threads/<YYYY-MM-DD-topic>/
│  ├─ index.md         # agenda and agreement summary (supervisor)
│  └─ turns/YYYYMMDD-HHMM-<name>.md
├─ 30_projects/
├─ 40_knowledge/{41_decisions,42_lessons}/
└─ 90_archive/
```

## Debugging

```bash
python3 scripts/brain.py digest builder   # what builder receives at start
python3 scripts/brain.py digest           # what the supervisor receives
python3 scripts/brain.py index            # rebuild the index
python3 tests/test_brain.py               # run the tests
```

## Limitations

- Only `Write`/`Edit` are checked. Files written through Bash bypass the write rules.
- Not built yet: per-round git commits, automatic trial-to-active promotion, a consolidate skill.
