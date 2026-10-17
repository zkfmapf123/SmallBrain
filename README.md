# SmallBrain

[한국어](README.ko.md)

A Claude Code plugin for when you run several agents together. It lets them use an Obsidian vault (just a folder of markdown files) as one shared brain.

## Why I built this

I once had a team of Claude Code agents build games for me. The main Claude I talk to acted as the team lead and handed work to agents for planning, coding, and QA. I wrote rules telling everyone to keep their records in an Obsidian vault.

It worked at first. A few days later the rules started slipping.

- The lead would write "fix this" in the vault, but the agent it was meant for never read that note. It made the same mistake again.
- The table of contents went stale. A game we had already dropped was still listed as the "reference game".
- The daily log was supposed to be written every day. After day one there were none.

The cause was always the same: the rules only existed as text. When Claude forgets a text rule, that's the end of it.

So this time the rules aren't text, they're mechanisms. Agents don't have to remember anything. Claude Code itself feeds them what to read, blocks what they shouldn't do, and checks their work.

## A few terms first

- **Supervisor**: the main Claude you talk to. The team lead.
- **Sub-agents**: the other Claudes the supervisor hands work to. Each one is defined in `.claude/agents/`.
- **Vault**: a folder of markdown files. Obsidian makes it nice to look at, but it works without Obsidian. Agents just read and write files.
- **Hook**: a script Claude Code runs automatically at certain moments (session start, agent start, right before a file write, right before finishing). This plugin is mostly hooks.

## What it actually does

**When an agent starts**, it gets what it needs automatically: the current goal, its role, the principles it earned from past mistakes, and any meeting waiting for its answer. You never have to tell an agent "read this first", so it can't forget to.

**When an agent tries to write a file**, the write gets checked. An agent may only write in its own folder (work journal, reflections) and its own turn files in meetings. If it tries to touch someone else's file or a shared one, the write is blocked and the agent is told why. Existing files can't be edited, only new ones created, so several agents can run at the same time without overwriting each other.

**When an agent tries to finish**, the plugin checks that it left a record. If there's no journal entry or meeting turn, the agent gets sent back once with "leave a record before you finish".

**When the supervisor finishes a reply**, the vault's table of contents is rebuilt. A script regenerates it every time instead of anyone editing it by hand, so it can't go stale. If the vault changed during the conversation but the human status page didn't, the supervisor is asked to update it.

**Reflections need evidence.** An agent writes one only when something actually went wrong, like a failing test or a review comment. A reflection without the evidence (which test, which comment) isn't saved at all. When the same lesson shows up twice, the supervisor turns it into a principle, and from then on that principle is handed to the agent every time it starts. A principle that conflicts with an existing one needs my approval. If I ignore it for 7 days, it gets cleared away automatically.

## What do I look at?

Just `vault/00_system/03_status.md`. It has three things:

- where things stand now
- what was done recently (with links to the original notes)
- what I need to decide

The rest of the vault is the agents' brain. You don't need to read it. If you're curious, follow the links.

## Install

You need Claude Code and `python3`. No other libraries.

Start Claude Code from the project you want to use it in:

```bash
cd your-project
claude --plugin-dir /path/to/smallbrains
```

## How to use it

### Once: create the vault

```
/smallbrain:init
```

That's the only setup step. It does two things:

1. Creates a `vault/` folder in the project and asks what the project's goal is.
2. Registers every agent already in `.claude/agents/`. Each one gets a personal folder like `vault/10_agents/11_<name>/`. **Your existing agent definition files are not touched.**

If you're adding this to a team that already runs a supervisor and several agents, you're done here. Registration matters because the hooks only treat an agent as a SmallBrain agent if it has a personal folder in the vault. An unregistered agent gets no digest, and its writes to the vault are blocked.

To put the vault somewhere else, set the `SMALLBRAIN_VAULT` environment variable.

### Day to day: just give it work

You don't type any `/smallbrain` commands in normal use. Tell the supervisor "build the login page" and that's it. The supervisor decides who does what, and the hooks handle context, write checks, and record keeping.

You don't have to start meetings (`meeting`) or principle promotion (`reflect`) yourself either. Both are skills, so the supervisor picks them up on its own when it thinks they're needed. Type them only when you want to force it:

```
/smallbrain:meeting Decide the auth method
/smallbrain:reflect
```

- **meeting**: the supervisor opens a meeting room under `vault/20_threads/`. Agents each write their own turn files, and after each round the supervisor sums up what's agreed and what's still open. At most 3 rounds; the outcome goes to `40_knowledge/41_decisions/`.
- **reflect**: turns any lesson that appears at least twice in an agent's reflections into a principle. A lesson that appeared once could be a fluke, so it stays where it is.

### Agents can't talk to each other directly

In Claude Code, a sub-agent can't call another sub-agent. That's a Claude Code limit, not something this plugin adds. So agents talk through files. Each one leaves a turn file in the meeting room, the supervisor calls the next one, and that agent reads the earlier turns before answering. They aren't talking live, they're passing the same notebook around.

### Adding a new agent

```
/smallbrain:hire builder Implements features
```

This creates the agent definition (`.claude/agents/builder.md`) and its vault folder in one step. I made it do both because I once hired an agent and forgot to add it to the roster. If you wrote the agent file yourself, just run `/smallbrain:init` again. It skips agents that are already registered and only adds new ones. If a new agent doesn't show up in the list, restart the session.

### If you already have a vault

An existing vault with a different layout can't be picked up as is. SmallBrain expects its own layout (below). I'd make a fresh vault and move over only the notes you need.

## What the vault looks like

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

Folders are numbered by function in steps of 10. Splitting by agent instead makes it unclear where shared notes like meetings and decisions should go.

## When something looks wrong

You can see exactly what an agent receives when it starts:

```bash
python3 scripts/brain.py digest builder   # what builder gets
python3 scripts/brain.py digest           # what the supervisor gets
python3 scripts/brain.py index            # rebuild the table of contents
python3 tests/test_brain.py               # tests
```

## What's still missing

- The write check only covers Claude's Write and Edit tools. If an agent writes a file through a terminal command, it isn't blocked. I'll add that if I see agents actually doing it.
- I haven't measured yet whether this is really more efficient. I'm comparing it against the records from my old game project (tokens and time per task).
- Not built yet: a git commit per meeting round, automatically confirming principles that hold up, and summarizing and clearing out old notes.
