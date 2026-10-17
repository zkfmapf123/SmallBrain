# SmallBrain

[한국어](README.ko.md)

A Claude Code plugin for projects that run one supervisor and several agents. Once installed, the agents use an Obsidian vault (a folder of markdown files) as a shared brain. They keep track of what to do, hand results to each other, and carry lessons from past mistakes into the next task.

## Why I built this

I once had a team of Claude Code agents build games. The main Claude I talk to was the team lead and handed work to agents for planning, coding, and QA. I wrote rules telling everyone to keep their records in an Obsidian vault.

A few days in, the rules stopped being followed.

- The lead wrote "fix this" in the vault, but the agent it was meant for never read that note. It made the same mistake again.
- The table of contents went stale. A game we had dropped was still listed as the "reference game".
- The daily log stopped after day one.

The rules only existed as text. When Claude forgets a text rule, that's the end of it.

So SmallBrain turns the rules into mechanisms. Agents don't have to remember anything. Claude Code feeds them what to read, blocks what they shouldn't do, and checks their work.

## Terms

- **Supervisor**: the main Claude you talk to. The team lead.
- **Agent**: another Claude the supervisor hands work to. Each one is a file in `.claude/agents/`.
- **Vault**: a folder of markdown files. Obsidian makes it nice to look at, but it works without Obsidian.
- **Hook**: a script Claude Code runs automatically at certain moments (session start, agent start, right before a file write, right before finishing). SmallBrain is mostly hooks.

## Install

You need Claude Code and `python3`.

**Install (recommended: project scope)**

Run this in the project you want to use SmallBrain in:

```bash
claude plugin install smallbrain --marketplace zkfmapf123/SmallBrain --scope project
```

With `--scope project`, SmallBrain is on only in that project. The setting goes into `.claude/settings.json`, so you can share it with your team through git. With `--scope user`, it's on in every project. That works fine, but projects without a vault get a one-line "no vault" notice at the start of every session.

**Try it without installing**

```bash
cd your-project
claude --plugin-dir /path/to/SmallBrain
```

It's on only for that session and gone when you quit.

## Getting started

Run this once in the project:

```
/smallbrain:init
```

1. Creates a `vault/` folder in the project and asks what the project's goal is.
2. Registers every agent you already have in `.claude/agents/`. Each agent gets a personal folder in the vault (`vault/10_agents/11_<name>/`). Your agent definition files are not modified.

That's all the setup there is. To put the vault somewhere else, set the `SMALLBRAIN_VAULT` environment variable.

## Day-to-day use

There are no commands to type. Tell the supervisor "build the login page" like you normally would. From there:

1. The supervisor splits the work and hands it to agents.
2. When an agent starts, a hook gives it what it needs: the current goal, its role, principles from past mistakes, and any meeting waiting for its answer.
3. When an agent writes a file, a hook checks it. An agent can only create new files in its own folder and its own meeting turn files. Anything else is blocked, and the agent is told why. Existing files can't be edited, only new ones created, so several agents can work at the same time without overwriting each other.
4. When an agent finishes, a hook checks that it left a work journal. If not, the agent is sent back once with "leave a record before you finish".
5. When the supervisor finishes a reply, a hook rebuilds the vault's table of contents. If the vault changed but the human status page didn't, the supervisor is asked to update it.

## Adding an agent

Create the agent file in `.claude/agents/` the way you normally would, by hand or with the `/agents` command. SmallBrain registers it automatically the first time it gets work.

Claude Code's built-in agents such as Explore and Plan are not registered. If they try to write to the vault, they're blocked. They return results to the supervisor, and the supervisor does the recording.

## Meetings

When several agents' opinions are needed, the supervisor opens a meeting on its own. To start one yourself:

```
/smallbrain:meeting Decide the auth method
```

The supervisor runs the meeting:

1. It creates a meeting note under `vault/20_threads/`.
2. It calls the attending agents one at a time. Each agent reads the turns so far and adds its own turn as a new file.
3. After each round, the supervisor writes down what's agreed and what's still open.
4. At most 3 rounds. The outcome is saved as a decision note in `40_knowledge/41_decisions/`.

Agents go through the supervisor instead of calling each other because in Claude Code only the supervisor can call agents.

## Reflections and principles

- An agent writes a reflection when something actually went wrong: a failing test, a review comment, or a correction from you. A reflection without that evidence isn't saved.
- When the same lesson shows up twice, the supervisor turns it into a principle. Once could be a fluke, so a single occurrence stays a reflection. To force it, type `/smallbrain:reflect`.
- From then on, the principle is handed to that agent every time it starts work.
- A principle that conflicts with an existing one needs your approval. It shows up on your status page, and if you leave it for 7 days it's cleared away automatically.

## What you look at

Just `vault/00_system/03_status.md`. It has three things:

- where things stand now
- what was done recently (with links to the original notes)
- what you need to decide

The rest of the vault is the agents' records. You don't need to read it. Follow the links if you're curious.

## Vault layout

```
vault/
├─ 00_system/
│  ├─ 00_index.md      table of contents, made by a script, don't edit
│  ├─ 01_rules.md      vault rules
│  ├─ 02_now.md        current goal and progress, for agents
│  └─ 03_status.md     status page, for you
├─ 10_agents/11_builder/
│  ├─ profile.md       role
│  ├─ principles/      principles (only the supervisor writes here)
│  ├─ reflections/     reflections
│  └─ journal/         work journal
├─ 20_threads/2026-10-17-auth-method/
│  ├─ index.md         agenda and what's agreed
│  └─ turns/           one file per turn
├─ 30_projects/        deliverable documents
├─ 40_knowledge/       decisions, shared lessons
└─ 90_archive/         notes that were cleared away
```

Folders are numbered by function in steps of 10. Splitting by agent instead would leave no clear place for shared notes like meetings and decisions.

## Troubleshooting

You can see exactly what an agent receives when it starts:

```bash
python3 scripts/brain.py digest builder   # what builder gets
python3 scripts/brain.py digest           # what the supervisor gets
python3 scripts/brain.py index            # rebuild the table of contents
python3 tests/test_brain.py               # tests
```

## Known gaps

- The write check only covers Claude's Write and Edit tools. If an agent writes a file through a terminal command, it isn't blocked.
- Whether this is actually more efficient hasn't been measured yet. That's being tested now.
- Not built yet: a git commit per meeting round, automatically confirming principles that hold up, and summarizing old notes.
