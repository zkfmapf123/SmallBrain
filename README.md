# SmallBrain

[한국어](README.ko.md)

A Claude Code plugin for projects where one team lead works with several agents. Once installed, the agents use an Obsidian vault (a folder of markdown files) as a shared brain. They keep track of what to do, hand results to each other, and carry lessons from past mistakes into the next task.

## Why I built this

I once had a team of Claude Code agents build games. The main Claude I talk to was the team lead and handed work to agents for planning, coding, and QA. I wrote rules telling everyone to keep their records in an Obsidian vault.

A few days in, the rules stopped being followed.

- The lead wrote "fix this" in the vault, but the agent it was meant for never read that note. It made the same mistake again.
- The table of contents went stale. A game we had dropped was still listed as the "reference game".
- The daily log stopped after day one.

The rules only existed as text. When Claude forgets a text rule, that's the end of it.

So SmallBrain turns the rules into mechanisms. Agents don't have to remember anything. Claude Code feeds them what to read, records their work, and blocks what they shouldn't do.

## Terms

- **Team lead**: whoever hands work to the agents. It can be the main Claude you talk to (the main session), or an agent that calls other agents.
- **Agent**: another Claude the lead hands work to. Each one is a file in `.claude/agents/`.
- **Vault**: a folder of markdown files. Obsidian makes it nice to look at, but it works without Obsidian.
- **Hook**: a script Claude Code runs automatically at certain moments (session start, agent start, right before a file write, agent finish, right before a reply ends). SmallBrain is mostly hooks.

## Both team structures work

```
Structure A: main session leads     Structure B: the lead is an agent too
main session (lead)                 main session (relays)
  ├ builder                           └ supervisor agent (lead)
  └ reviewer                              ├ researcher
                                          ├ proponent
                                          └ critic
```

Both are common. SmallBrain figures out which one you have and behaves accordingly. The rule is simple: **an agent that calls other agents is a lead**. The main session has lead permissions in either structure.

## Install

You need Claude Code and `python3`.

**Install (recommended: project scope)**

Run this in the project you want to use SmallBrain in:

```bash
claude plugin install smallbrain --marketplace zkfmapf123/SmallBrain --scope project
```

With `--scope project`, SmallBrain is on only in that project. The setting goes into `.claude/settings.json`, so you can share it with your team through git. With `--scope user` it's on in every project, and projects without a vault get a one-line "no vault" notice at the start of every session.

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

What init does depends on the project.

**If there are no agents yet**, it builds a Structure A team. It asks for the project goal, suggests 2-3 worker agents that fit, and creates them in `.claude/agents/` once you agree. The main session is the lead.

**If you already have agents**, it reads your structure. An agent whose `tools` list includes `Agent` is registered as a lead, the rest as workers. Your agent definition files are not modified. An agent with no `tools` line starts as a worker, and the hook switches it to lead the moment it actually calls another agent. To set a role yourself: `python3 scripts/brain.py role <name> supervisor` or `worker`.

In both cases it also:

- creates a `vault/` folder in the project.
- appends a SmallBrain block to the end of `CLAUDE.md`, once. It says that rules like "only answer in chat" are about deliverable files, so they don't stop vault records. If your `CLAUDE.md` has lines that might conflict, init shows them.

**If init created new agent files, restart the session.** Claude Code only reads agent definitions when a session starts. To put the vault somewhere else, set the `SMALLBRAIN_VAULT` environment variable.

## Day-to-day use

There are no commands to type. Ask for work like you normally would, for example "build the login page". From there:

1. The lead splits the work and hands it to agents.
2. **When an agent starts**, a hook gives it what it needs: the current goal, its role, principles from past mistakes, any meeting waiting for its answer, and the current time. When the same agent wakes up again in the background, it isn't given all of this a second time.
3. **When an agent writes a file**, a hook checks it. A worker can only create new reflection notes and meeting turn files of its own. Touching shared files is blocked with an explanation, and so is writing to the vault through Bash. A lead can write anywhere in the vault.
4. **When an agent finishes**, a hook saves its final report to its `journal/`. Agents don't have to record anything themselves, and agents without write tools still get their reports saved.
5. **When the main session finishes a reply**, a hook rebuilds the vault's table of contents. If the vault changed but the human status page didn't, it asks once for the status page to be updated, and reminds the lead to write a decision note if a decision was made.

## Adding an agent

Create the agent file in `.claude/agents/` the way you normally would, by hand or with the `/agents` command. SmallBrain registers it automatically the first time it gets work. Claude Code only picks up new agent files after a session restart.

Claude Code's built-in agents such as Explore and Plan are not registered. If they try to write to the vault, they're blocked. They return results to the lead, and the lead does the recording.

## Meetings

When several agents' opinions are needed, the lead opens a meeting on its own. To start one yourself:

```
/smallbrain:meeting Decide the auth method
```

1. The lead creates a meeting note under `vault/20_threads/`.
2. The lead calls the attending agents. Each one reads what's been said so far and gives its opinion. The hook saves each opinion to that agent's journal.
3. After each round, the lead writes down what's agreed and what's still open, and links each opinion.
4. At most 3 rounds. The outcome is saved as a decision note in `40_knowledge/41_decisions/`.

In Structure B, the lead agent runs the meeting. The hook hands it the meeting steps when it starts.

## Reflections and principles

- A reflection is written when something actually went wrong: a failing test, a review comment, or a correction from you. A reflection without that evidence isn't saved.
- Agents with write tools write to their own `reflections/`. Agents without them add a `반성:` (reflection) section to their report, and the lead turns it into a reflection note.
- When the same lesson shows up twice, the lead turns it into a principle. Once could be a fluke. To force it, type `/smallbrain:reflect`.
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
│  ├─ 02_now.md        current goal and progress, for the team
│  └─ 03_status.md     status page, for you
├─ 10_agents/11_builder/
│  ├─ profile.md       role (role: supervisor or worker)
│  ├─ principles/      principles (only the lead writes here)
│  ├─ reflections/     reflections
│  └─ journal/         work reports (saved by the hook)
├─ 20_threads/2026-10-17-auth-method/
│  ├─ index.md         agenda and what's agreed
│  └─ turns/           turns written directly by agents
├─ 30_projects/        deliverable documents
├─ 40_knowledge/       decisions, shared lessons
└─ 90_archive/         notes that were cleared away
```

Folders are numbered by function in steps of 10. Splitting by agent instead would leave no clear place for shared notes like meetings and decisions.

## Troubleshooting

You can see exactly what an agent receives when it starts:

```bash
python3 scripts/brain.py digest builder   # what builder gets
python3 scripts/brain.py digest           # what the main session gets
python3 scripts/brain.py index            # rebuild the table of contents
python3 tests/test_brain.py               # tests
```
