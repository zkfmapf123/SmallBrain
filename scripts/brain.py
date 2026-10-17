#!/usr/bin/env python3
"""SmallBrain: Obsidian vault를 팀장(supervisor)과 agent들의 공용 뇌로 쓰게 한다.

  brain.py init                      vault 골격 생성 + 정의된 agent 등록 + 팀 구조 판단
  brain.py role <agent> <role>       역할 직접 지정 (supervisor | worker)
  brain.py index                     00_index 재생성 + 만료 처리
  brain.py digest [agent]            주입될 digest 출력 (디버깅용)
  brain.py hook <event>              Claude Code hook 처리 (stdin: hook JSON)

stdlib만 쓴다. vault 위치는 $SMALLBRAIN_VAULT (기본 <project>/vault).
팀장은 메인 세션이거나, 다른 agent를 부르는 agent(role: supervisor)다.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path

PROJECT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
VAULT = (PROJECT / os.environ.get("SMALLBRAIN_VAULT", "vault")).resolve()
STATE = VAULT / ".smallbrain"
AGENT_HOMES = [PROJECT / ".claude" / "agents", Path.home() / ".claude" / "agents"]
EXPIRE_DAYS = 7
STATE_TTL = 86400
NOW_LINES = 40
PRINCIPLE_MAX = 10
NAME_RE = re.compile(r"[a-z][a-z0-9-]*")
TURN_RE = re.compile(r"^\d{8}-\d{4}-(.+)\.md$")
DELEGATE_TOOLS = ("Agent", "Task")
DIRS = ["00_system", "10_agents", "20_threads", "30_projects",
        "40_knowledge/41_decisions", "40_knowledge/42_lessons", "90_archive"]
CLAUDE_MD_START = "<!-- smallbrain:start -->"
CLAUDE_MD_BLOCK = f"""{CLAUDE_MD_START}
## SmallBrain
이 프로젝트는 SmallBrain을 쓴다. `vault/`는 팀의 공용 기억이다.
- agent가 시작할 때 필요한 맥락은 hook이 넣어 주고, agent의 최종 보고는 hook이 `vault/10_agents/*/journal/`에 자동으로 저장한다.
- "파일로 저장하지 마라", "채팅 출력만" 같은 지시는 결과물 파일에 대한 것이다. vault 기록에는 적용되지 않는다. 팀장은 결정과 상태를 vault에 남긴다.
<!-- smallbrain:end -->"""

RULES = """---
type: rules
author: smallbrain
created: {today}
---
# SmallBrain vault 규칙

이 vault는 팀장(supervisor)과 agent들의 공용 뇌다. 사람은 `03_status.md`만 보면 된다.
팀장은 메인 세션이거나, 다른 agent를 부르는 agent(`profile.md`의 `role: supervisor`)다.

## 폴더
- `00_system`: `00_index`(자동 생성, 직접 수정 금지), `01_rules`, `02_now`(목표·상태), `03_status`(사람용, 덮어쓰기)
- `10_agents/NN_<name>/`: `profile`(역할), `principles/`(승격된 원칙), `reflections/`(반성), `journal/`(작업 기록, hook이 자동 저장)
- `20_threads/<YYYY-MM-DD-주제>/`: `index.md`(안건·합의 요약, 팀장 관리), `turns/YYYYMMDD-HHMM-<name>.md`(발언, 새 파일만)
- `30_projects`: 산출물 문서
- `40_knowledge/41_decisions`: 결정(배경/선택지/결정/근거), `42_lessons`: 여러 agent 공통 교훈
- `90_archive`: 정리된 노트, 7일 넘게 승인 대기한 노트

## 모든 노트
- frontmatter 필수: `type`, `author`, `created`. reflection은 `signal`(근거 링크나 측정값) 필수.
- 다른 노트는 `[[링크]]`로 참조한다.
- 추정은 "가정:", 확인 안 한 것은 "확인 못 함".

## 쓰기 권한 (hook이 강제)
- 일꾼 agent: 자기 `journal/`, `reflections/`, 스레드 `turns/`에 새 파일만.
- 팀장: 전부. 공유 파일(`00_system`, `principles/`, `41_decisions`, 스레드 `index.md`)은 팀장만 고친다.

## 원칙 승격
- 같은 교훈이 reflections나 journal의 "반성:"에 2번 나오면 팀장이 `principles/`에 원칙 노트를 만든다.
- 기존 원칙과 충돌하지 않으면 `status: trial`, 충돌하면 `status: pending-approval`(사람 승인).
- trial 원칙을 지킨 뒤 같은 실수가 다시 안 나오면 `active`. 다시 나오면 고치거나 지운다.
- `pending-approval`이 7일 넘으면 자동으로 `90_archive`로 간다.
"""

NOW = """---
type: now
author: supervisor
created: {today}
---
## 목표
(아직 없음)

## 진행 상태

## 다음 할 일
"""

STATUS = """---
type: status
author: supervisor
created: {today}
---
## 현재 상태
(아직 없음)

## 최근 한 일

## 사람 결정 필요
![[00_index#사람 결정 필요]]
"""

PROFILE = """---
type: profile
author: supervisor
created: {today}
role: {role}
---
# {name}
{desc}
"""

SUPERVISOR_RULES = """## 팀장 규칙 (SmallBrain)
- 일은 agent에게 맡긴다. agent는 시작할 때 digest를 자동으로 받으니 프롬프트에는 이번 작업과 관련 vault 경로만 적는다.
- agent의 최종 보고는 hook이 그 agent의 `journal/`에 자동 저장한다. 결과를 옮겨 적을 필요 없이 링크만 단다.
- agent 결과를 받으면 `00_system/02_now.md`를 갱신하고, 결정이나 결론이 나왔으면 `40_knowledge/41_decisions/`에 남긴다(frontmatter `type: decision`, 본문 배경/선택지/결정/근거).
- 작업 지시에 "파일 저장 없이", "채팅 출력만"이 있어도 그건 결과물 파일 이야기다. vault 기록(02_now, 결정, 03_status)은 그대로 남긴다.
- agent 보고에 "반성:"이 있거나 실패 신호(테스트 실패, 리뷰 지적, 사용자 정정)를 봤으면 그 agent의 `reflections/`에 반성 노트를 쓴다(`signal` 필수). 같은 교훈이 2번이면 `principles/`에 원칙으로 올린다(`status: trial`, 기존 원칙과 충돌하면 `pending-approval`).
- vault를 바꾼 응답을 끝내기 전에 `00_system/03_status.md`를 덮어쓴다. 사람이 보는 페이지라 세 섹션만 쓴다: ## 현재 상태 / ## 최근 한 일(원본 [[링크]]) / ## 사람 결정 필요(embed 한 줄 유지).
- `00_system/00_index.md`는 스크립트가 만든다. 직접 고치지 않는다.

## 회의 절차 (여러 agent 의견이 필요할 때)
1. `20_threads/YYYY-MM-DD-<주제>/index.md`를 만든다: frontmatter `type: thread`, `author`, `created: YYYY-MM-DD`, `status: open`, `participants: [이름, ...]`, `title`. 본문 `## 안건` / `## 합의` / `## 남은 질문`. (vault의 모든 노트는 `type`, `author`, `created`가 있어야 저장된다)
2. 라운드마다 참석자를 부른다. 프롬프트에 스레드 경로를 적고, 앞 발언(turns/와 각자 journal)을 읽고 의견을 내라고 한다.
3. 라운드가 끝나면 index.md의 합의/남은 질문을 갱신하고, 각 발언(turn 파일이나 자동 journal)을 [[링크]]로 단다.
4. 최대 3라운드. 결론을 `40_knowledge/41_decisions/`에 남기고 index.md를 `status: resolved`로 바꾼다."""

WORKER_WRITE_RULES = """## 기록 규칙
- 내 최종 보고는 hook이 `{own}/journal/`에 자동으로 저장한다. 따로 기록할 필요 없다.
- 실패 신호(테스트 실패, 리뷰 지적, 사용자 정정)가 있었으면 `{own}/reflections/YYYY-MM-DD-주제.md`를 새로 만든다:
  ---
  type: reflection
  author: {agent}
  created: YYYY-MM-DD
  signal: "근거 링크나 측정값"
  ---
  - 무슨 일: / - 원인: / - 다음 규칙:
- 회의 중이면 발언을 `20_threads/<스레드>/turns/YYYYMMDD-HHMM-{agent}.md`로 새로 만들어도 된다.
- vault에서 쓸 수 있는 곳은 위 두 곳뿐이고, 기존 파일은 고치지 못한다. 공유 파일을 바꿔야 하면 보고에 제안으로 적는다."""

WORKER_READONLY_RULES = """## 기록 규칙
- 내 최종 보고는 hook이 `{own}/journal/`에 자동으로 저장한다. 나는 파일을 쓰지 않는다.
- 실패 신호(테스트 실패, 리뷰 지적, 사용자 정정)가 있었으면 보고 끝에 `반성:` 섹션을 적는다: 무슨 일 / 원인 / 다음 규칙 / 근거. 팀장이 반성 노트로 옮긴다."""


def today():
    return date.today().isoformat()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def parse(text):
    """frontmatter(평평한 key: value, [a, b] 리스트)와 본문을 돌려준다."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    fm = {}
    for line in text[4:end].splitlines():
        key, sep, val = line.partition(":")
        if not sep or not key.strip() or key[0].isspace():
            continue
        val = val.split(" #")[0].strip().strip("\"'")
        if val.startswith("[") and val.endswith("]") and not val.startswith("[["):
            val = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
        fm[key.strip()] = val
    return fm, text[end + 4:].lstrip("\n")


def meta(path):
    try:
        return parse(path.read_text(encoding="utf-8"))
    except OSError:
        return {}, ""


def rel(path):
    return path.relative_to(VAULT).as_posix()


def write_new(path, text):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def turn_author(name):
    m = TURN_RE.match(name)
    return m.group(1) if m else None


def agent_dirs():
    root = VAULT / "10_agents"
    if not root.is_dir():
        return []
    return sorted(d for d in root.iterdir() if d.is_dir() and "_" in d.name)


def agent_dir(name):
    for d in agent_dirs():
        if d.name.partition("_")[2] == name:
            return d
    return None


def role_of(name):
    d = agent_dir(name)
    return meta(d / "profile.md")[0].get("role", "worker") if d else None


def set_role(name, role):
    p = agent_dir(name) / "profile.md"
    text = p.read_text(encoding="utf-8")
    if re.search(r"(?m)^role:.*$", text):
        text = re.sub(r"(?m)^role:.*$", f"role: {role}", text, count=1)
    else:
        text = text.replace("\n---\n", f"\nrole: {role}\n---\n", 1)
    p.write_text(text, encoding="utf-8")


def defined_agents():
    """프로젝트와 사용자 .claude/agents/ 의 agent: {name: {desc, tools}}. tools는 생략이면 None."""
    out = {}
    for home in AGENT_HOMES:
        for f in sorted(home.glob("*.md")):
            fm = meta(f)[0]
            tools = fm.get("tools")
            if isinstance(tools, str):
                tools = [t.strip() for t in tools.split(",") if t.strip()]
            out.setdefault(fm.get("name") or f.stem, {"desc": fm.get("description") or "", "tools": tools})
    return out


def detect_role(info):
    """tools에 Agent/Task가 있으면 팀장. 생략(None)이면 일꾼으로 시작하고, 실제로 agent를 부르면 hook이 팀장으로 바꾼다."""
    return "supervisor" if any(t in (info["tools"] or []) for t in DELEGATE_TOOLS) else "worker"


def can_write(name):
    tools = defined_agents().get(name, {}).get("tools")
    return tools is None or any(t in tools for t in ("Write", "Edit", "MultiEdit"))


def notes():
    for p in VAULT.rglob("*.md"):
        parts = p.relative_to(VAULT).parts
        if parts[0] in (".smallbrain", ".obsidian", "90_archive"):
            continue
        yield p


def threads():
    """열린 스레드 목록. index.md의 status가 resolved가 아니면 열린 것."""
    root = VAULT / "20_threads"
    out = []
    if not root.is_dir():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        fm = meta(d / "index.md")[0]
        if fm.get("status") == "resolved":
            continue
        turns = sorted((d / "turns").glob("*.md")) if (d / "turns").is_dir() else []
        parts = fm.get("participants") or []
        out.append({
            "path": rel(d), "title": fm.get("title") or d.name,
            "parts": [parts] if isinstance(parts, str) else parts,
            "turns": len(turns), "last": turn_author(turns[-1].name) if turns else None,
        })
    return out


def titles(folder):
    """trial/active 원칙의 title 한 줄씩."""
    out = []
    for p in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        fm, body = meta(p)
        if fm.get("status") in ("trial", "active"):
            line = fm.get("title") or (body.strip().splitlines() or [p.stem])[0]
            out.append(f"- [{fm['status']}] {line} ([[{rel(p)[:-3]}]])")
    return out


def clip(text, n):
    lines = text.strip().splitlines()
    more = f"\n... ({len(lines) - n}줄 더, 원본 참고)" if len(lines) > n else ""
    return "\n".join(lines[:n]) + more


def expire():
    cutoff = date.today().toordinal() - EXPIRE_DAYS
    for p in list(notes()):
        fm = meta(p)[0]
        if fm.get("status") != "pending-approval":
            continue
        try:
            created = date.fromisoformat(str(fm.get("created", ""))[:10])
        except ValueError:
            continue
        if created.toordinal() < cutoff:
            dst = VAULT / "90_archive" / p.relative_to(VAULT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dst))


def build_index():
    if not (VAULT / "00_system").is_dir():
        return
    expire()
    pending, decisions = [], []
    for p in notes():
        fm = meta(p)[0]
        link = f"[[{rel(p)[:-3]}]]"
        if fm.get("status") == "pending-approval":
            pending.append(f"- {link} — {fm.get('author', '?')}, {fm.get('created', '?')}")
        if fm.get("type") == "decision":
            decisions.append(f"- {link} — {fm.get('created', '?')}")
    open_threads = [f"- [[{t['path']}/index|{t['title']}]] — 참석 {', '.join(t['parts']) or '?'}, "
                    f"턴 {t['turns']}개, 마지막 {t['last'] or '-'}" for t in threads()]
    agents = []
    for d in agent_dirs():
        name = d.name.partition("_")[2]
        n_pr = len(titles(d / "principles"))
        n_jr = len(list((d / "journal").glob("*.md")))
        n_rf = len(list((d / "reflections").glob("*.md")))
        agents.append(f"- [[{rel(d)}/profile|{name}]] ({role_of(name)}) — 기록 {n_jr}개, 반성 {n_rf}개, 원칙 {n_pr}개")
    text = "\n".join([
        "---", "type: index", "author: smallbrain", f"created: {today()}", "---",
        "# Index", "스크립트가 만든다. 직접 고치지 않는다.", "",
        "## 사람 결정 필요", *(pending or ["- 없음"]), "",
        "## 열린 스레드", *(open_threads or ["- 없음"]), "",
        "## agents", *(agents or ["- 없음"]), "",
        "## 결정", *(decisions or ["- 없음"]), "",
    ])
    path = VAULT / "00_system" / "00_index.md"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def digest_supervisor(agent=None):
    """팀장 digest. agent=None이면 메인 세션."""
    now = clip(meta(VAULT / "00_system" / "02_now.md")[1], NOW_LINES)
    status = clip(meta(VAULT / "00_system" / "03_status.md")[1], 30)
    roster = [f"{d.name.partition('_')[2]}({role_of(d.name.partition('_')[2])})" for d in agent_dirs()]
    n_pending = sum(1 for p in notes() if meta(p)[0].get("status") == "pending-approval")
    open_threads = [f"- `{t['path']}/` — {t['title']}, 마지막 {t['last'] or '-'}" for t in threads()]
    who = f"`{agent}` agent (팀장)" if agent else "메인 세션 (팀장)"
    parts = [
        f"# SmallBrain — {who}\nvault: `{VAULT}` (아래 경로는 vault 기준)\n지금 시각: {now_str()}",
        "## 지금 (00_system/02_now.md)\n" + now,
        "## 사람용 상태 (00_system/03_status.md)\n" + status,
        "## 열린 스레드\n" + "\n".join(open_threads or ["- 없음"]),
        f"## agents\n{', '.join(roster) or '없음 (.claude/agents/ 에 정의하면 처음 일할 때 자동 등록)'}\n사람 결정 대기: {n_pending}건",
    ]
    if agent:
        parts.append(f"## 내 원칙\n" + "\n".join(titles(agent_dir(agent) / "principles") or ["- 아직 없음"]))
        parts.append(f"vault에 쓰는 노트의 frontmatter `author`는 `{agent}`로 한다.")
    parts.append(SUPERVISOR_RULES)
    return "\n\n".join(parts)


def digest_worker(agent):
    d = agent_dir(agent)
    own = rel(d)
    principles = titles(d / "principles")
    warn = f"\n경고: 원칙 {len(principles)}개. 팀장에게 정리(합치기)를 제안한다." if len(principles) > PRINCIPLE_MAX else ""
    mine = [t for t in threads() if agent in t["parts"] or "all" in t["parts"]]
    lines = [f"- `{t['path']}/` — 턴 {t['turns']}개, 마지막 {t['last'] or '-'}" for t in mine]
    rules = WORKER_WRITE_RULES if can_write(agent) else WORKER_READONLY_RULES
    return "\n\n".join([
        f"# SmallBrain digest — {agent}\nvault: `{VAULT}` (아래 경로는 vault 기준)\n지금 시각: {now_str()}",
        "## 지금 (00_system/02_now.md)\n" + clip(meta(VAULT / "00_system" / "02_now.md")[1], NOW_LINES),
        f"## 내 역할 ({own}/profile.md)\n" + meta(d / "profile.md")[1].strip(),
        "## 내 원칙\n" + "\n".join(principles or ["- 아직 없음"]) + warn,
        "## 공통 교훈\n" + "\n".join(titles(VAULT / "40_knowledge" / "42_lessons") or ["- 아직 없음"]),
        "## 나에게 열린 스레드\n" + "\n".join(lines or ["- 없음"]),
        rules.format(own=own, agent=agent),
    ])


def digest(agent=None):
    if agent and role_of(agent) != "supervisor":
        return digest_worker(agent)
    return digest_supervisor(agent)


def register(name, desc, role="worker"):
    """vault에 agent 폴더를 만든다. agent 정의 파일은 건드리지 않는다."""
    d = agent_dir(name)
    if not d:
        nums = [int(x.name.partition("_")[0]) for x in agent_dirs() if x.name.partition("_")[0].isdigit()]
        d = VAULT / "10_agents" / f"{max(nums, default=10) + 1}_{name}"
    for sub in ("principles", "reflections", "journal"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    write_new(d / "profile.md", PROFILE.format(today=today(), name=name, desc=desc or "(역할 미정)", role=role))
    return d


def update_claude_md():
    """CLAUDE.md에 SmallBrain 블록을 덧붙이고(한 번만), 기록과 충돌할 수 있는 줄을 돌려준다."""
    path = PROJECT / "CLAUDE.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if CLAUDE_MD_START not in text:
        path.write_text((text.rstrip() + "\n\n" if text.strip() else "") + CLAUDE_MD_BLOCK + "\n", encoding="utf-8")
    outside = text.split(CLAUDE_MD_START)[0]
    pat = re.compile(r"저장하지|채팅\s*출력만|파일로\s*남기지|기록하지|knowledge_base|다른 vault|obsidian", re.I)
    return [line.strip() for line in outside.splitlines() if pat.search(line)]


def init():
    """vault를 만들고 정의된 agent를 등록하고 팀 구조를 판단한다. 다시 실행해도 안전하다."""
    for d in DIRS:
        (VAULT / d).mkdir(parents=True, exist_ok=True)
    for name, tpl in (("01_rules.md", RULES), ("02_now.md", NOW), ("03_status.md", STATUS)):
        write_new(VAULT / "00_system" / name, tpl.replace("{today}", today()))
    agents = defined_agents()
    added, skipped = [], []
    for name, info in agents.items():
        if not NAME_RE.fullmatch(name):
            skipped.append(name)
        elif not agent_dir(name):
            register(name, info["desc"], detect_role(info))
            added.append(name)
    conflicts = update_claude_md()
    build_index()
    print(f"vault 준비됨: {VAULT}")
    if not agents:
        print("STRUCTURE: none (.claude/agents/ 에 agent가 없다. 메인 세션이 팀장인 구조로 일꾼 agent를 만든다)")
    else:
        leads = [n for n in agents if NAME_RE.fullmatch(n) and role_of(n) == "supervisor"]
        print(f"STRUCTURE: {'agent-lead' if leads else 'main-lead'}")
        print(f"팀장: {', '.join(leads) + ' agent (메인 세션도 팀장 권한)' if leads else '메인 세션'}")
        omitted = [n for n, i in agents.items() if i["tools"] is None and role_of(n) == "worker"]
        if omitted:
            print(f"tools를 안 적은 agent: {', '.join(omitted)} (일꾼으로 시작, 다른 agent를 부르면 자동으로 팀장 전환)")
    if added:
        print(f"agent 등록: {', '.join(added)}")
    if skipped:
        print(f"이름이 소문자 kebab-case가 아니라 건너뜀: {', '.join(skipped)}")
    if conflicts:
        print("CLAUDE.md에서 vault 기록과 겹칠 수 있는 줄 (SmallBrain 블록이 우선함을 덧붙였다):")
        for line in conflicts:
            print(f"  - {line}")


def handback_from(transcript):
    """agent transcript에서 마지막 SubagentHandback 메시지, 없으면 마지막 assistant 텍스트."""
    handback = text = ""
    try:
        lines = Path(transcript).read_text(encoding="utf-8").splitlines()
    except (OSError, TypeError):
        return ""
    for line in lines:
        try:
            msg = json.loads(line).get("message") or {}
        except ValueError:
            continue
        if msg.get("role") != "assistant" or not isinstance(msg.get("content"), list):
            continue
        for c in msg["content"]:
            if c.get("type") == "tool_use" and c.get("name") == "SubagentHandback":
                handback = (c.get("input") or {}).get("message") or handback
            elif c.get("type") == "text" and c.get("text", "").strip():
                text = c["text"]
    return (handback or text).strip()


def load_state(agent_id):
    try:
        return json.loads((STATE / f"agent-{agent_id}.json").read_text())
    except (OSError, ValueError):
        return None


def save_state(agent_id, st):
    (STATE / f"agent-{agent_id}.json").write_text(json.dumps(st, ensure_ascii=False))


def save_report(agent_id, st, report):
    """최종 보고를 agent journal에 이어 붙인다. 같은 보고는 한 번만."""
    h = hashlib.sha1(report.encode()).hexdigest()
    if h in st["saved"]:
        return
    d = agent_dir(st["agent"])
    if not st.get("journal"):
        stamp = datetime.fromtimestamp(st["t"]).strftime("%Y-%m-%d-%H%M")
        st["journal"] = rel(d / "journal" / f"{stamp}-{agent_id[-6:]}.md")
        write_new(VAULT / st["journal"], f"---\ntype: journal\nauthor: {st['agent']}\ncreated: {today()}\n"
                                         f"agent_id: {agent_id}\nauto: true\n---\n")
    with open(VAULT / st["journal"], "a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now().strftime('%H:%M')} 보고\n{report}\n")
    st["saved"].append(h)


def sweep():
    """보고를 못 읽고 끝난 agent를 transcript에서 다시 읽고, 하루 지난 상태 파일을 지운다."""
    for f in STATE.glob("agent-*.json"):
        st = load_state(f.name[6:-5])
        if st and st.get("pending") and st.get("transcript"):
            report = handback_from(st["transcript"])
            if report and agent_dir(st["agent"]):
                save_report(f.name[6:-5], st, report)
                st["pending"] = False
                save_state(f.name[6:-5], st)
    for f in STATE.iterdir():
        if time.time() - f.stat().st_mtime > STATE_TTL:
            f.unlink()


READ_CMDS = {"cat", "ls", "head", "tail", "grep", "rg", "find", "wc", "stat", "file", "diff", "tree", "less", "echo"}


def check_bash(data, agent):
    """일꾼 agent의 Bash 명령이 vault를 건드리면 읽기 명령만 허용한다(허용 목록). vault 밖은 관여하지 않는다."""
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not agent or role_of(agent) == "supervisor":
        return None
    in_vault = re.compile(rf"{re.escape(str(VAULT))}|(^|[\s'\"=/]){re.escape(VAULT.name)}(/|\s|$)")
    if not in_vault.search(cmd):
        return None
    for seg in re.split(r"&&|\|\||[;|\n]", cmd):
        words = seg.split()
        targets = re.findall(r"(?<![0-9&])>>?\s*([^\s&]+)", seg)
        bad_cmd = words and words[0] not in READ_CMDS
        bad_find = words and words[0] == "find" and re.search(r"-delete|-exec", seg)
        if any(in_vault.search(t) for t in targets) or bad_find or (bad_cmd and in_vault.search(seg)):
            return ("SmallBrain: 일꾼 agent는 vault에 대해 읽기 명령(cat, ls, grep 등)만 Bash로 쓸 수 있다. "
                    "반성은 Write로 reflections/에, 작업 보고는 자동 저장되니 보고에 적어라.")
    return None


def check_write(data, agent):
    """PreToolUse: 차단 사유를 돌려준다. 허용이면 None. agent는 sub-agent일 때만 이름, 메인 세션이면 None."""
    if data.get("tool_name") == "Bash":
        return check_bash(data, agent)
    ti = data.get("tool_input") or {}
    if not ti.get("file_path"):
        return None
    p = Path(ti["file_path"])
    if not p.is_absolute():
        p = Path(data.get("cwd") or PROJECT) / p
    p = p.resolve()
    try:
        parts = p.relative_to(VAULT).parts
    except ValueError:
        return None  # vault 밖은 관여하지 않는다
    if parts and parts[0] in (".obsidian", ".smallbrain"):
        return None
    if agent:
        d = agent_dir(agent)
        if not d:
            return f"SmallBrain: vault는 .claude/agents/ 에 정의된 agent만 쓴다('{agent}'는 기본 agent라 등록 안 됨). 결과는 팀장에게 돌려줘라."
        if role_of(agent) != "supervisor":
            own = d.relative_to(VAULT).parts
            in_own = (len(parts) == len(own) + 2 and parts[:len(own)] == own
                      and parts[len(own)] in ("journal", "reflections"))
            is_turn = (len(parts) == 4 and parts[0] == "20_threads" and parts[2] == "turns"
                       and turn_author(parts[3]) == agent)
            own_s = "/".join(own)
            if not (in_own or is_turn):
                return (f"SmallBrain: {agent}는 vault에서 {own_s}/reflections/, "
                        f"20_threads/<스레드>/turns/YYYYMMDD-HHMM-{agent}.md 에만 새 파일을 쓸 수 있다. "
                        "작업 보고는 자동 저장되고, 공유 파일 변경은 보고에 제안으로 적어라.")
            if p.exists():
                return "SmallBrain: 기존 파일은 고치지 않는다. 이어 쓸 내용은 새 파일로 만들어라."
    if data.get("tool_name") == "Write" and p.suffix == ".md":
        fm = parse(ti.get("content") or "")[0]
        missing = [k for k in ("type", "author", "created") if not fm.get(k)]
        if missing:
            return f"SmallBrain: frontmatter에 {', '.join(missing)}가 필요하다(--- 로 감싼 맨 위 블록)."
        if agent and fm.get("author") != agent:
            return f"SmallBrain: author는 '{agent}'여야 한다."
        if fm.get("type") == "reflection" and not fm.get("signal"):
            return "SmallBrain: reflection에는 signal(근거 링크나 측정값)이 필요하다. 근거 없는 반성은 남기지 않는다."
    return None


def emit_context(event, text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}},
                     ensure_ascii=False))


def hook(event):
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    if not (VAULT / "00_system").is_dir():
        if event == "SessionStart":
            emit_context(event, "SmallBrain: 이 프로젝트에는 vault가 없다. 쓰려면 /smallbrain:init")
        return
    STATE.mkdir(exist_ok=True)
    agent_id = data.get("agent_id")
    # agent_id가 없으면 메인 세션이다(--agent로 띄워도 agent_type만 있고 agent_id는 없다)
    agent = (data.get("agent_type") or "").split(":")[-1] if agent_id else None

    if event == "SessionStart":
        sweep()
        sf = STATE / f"session-{data.get('session_id')}.json"
        sf.write_text(json.dumps({"t": time.time(), "asked": False}))
        build_index()
        emit_context(event, digest())

    elif event == "SubagentStart":
        if not agent_dir(agent) and NAME_RE.fullmatch(agent or ""):
            info = defined_agents().get(agent)
            if info is not None:  # 직접 정의한 agent만 처음 일할 때 자동 등록
                register(agent, info["desc"], detect_role(info))
                build_index()
        if agent_dir(agent) and not load_state(agent_id):  # background agent가 다시 깨어날 때는 주입하지 않는다
            save_state(agent_id, {"agent": agent, "t": time.time(), "saved": [], "journal": None,
                                  "transcript": None, "pending": False})
            emit_context(event, digest(agent))

    elif event == "PreToolUse":
        if data.get("tool_name") in DELEGATE_TOOLS:
            if agent and agent_dir(agent) and role_of(agent) != "supervisor":
                set_role(agent, "supervisor")
                build_index()
                emit_context(event, f"SmallBrain: `{agent}`는 다른 agent에게 일을 맡기므로 이제 팀장 규칙이 적용된다.\n\n"
                             + digest_supervisor(agent))
            return
        reason = check_write(data, agent)
        if reason:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": reason}}, ensure_ascii=False))

    elif event == "SubagentStop":
        st = load_state(agent_id)
        if not st or not agent_dir(st["agent"]):
            return
        st["transcript"] = data.get("agent_transcript_path") or st.get("transcript")
        report = (data.get("last_assistant_message") or "").strip() or handback_from(st["transcript"])
        if report:
            save_report(agent_id, st, report)
            st["pending"] = False
        else:
            st["pending"] = True  # transcript가 아직 안 써졌을 수 있다. 다음 Stop/SessionStart에서 다시 읽는다
        save_state(agent_id, st)

    elif event == "Stop":
        if data.get("stop_hook_active"):
            return
        sweep()
        build_index()
        sf = STATE / f"session-{data.get('session_id')}.json"
        try:
            ss = json.loads(sf.read_text())
        except (OSError, ValueError):
            return
        skip = {"00_system/00_index.md", "00_system/03_status.md"}
        changed = [p.stat().st_mtime for p in notes() if rel(p) not in skip and p.stat().st_mtime >= ss["t"]]
        status = VAULT / "00_system" / "03_status.md"
        if changed and not ss["asked"] and (not status.exists() or status.stat().st_mtime < max(changed)):
            ss["asked"] = True  # 세션당 한 번만 요청한다
            sf.write_text(json.dumps(ss))
            print(json.dumps({"decision": "block", "reason":
                "SmallBrain: 이번 세션에 vault가 바뀌었는데 00_system/03_status.md가 그보다 오래됐다. "
                "끝내기 전에 덮어써라(맨 위 frontmatter type/author/created 유지). 사람이 보는 페이지라 "
                "이 세 섹션만 쓴다: ## 현재 상태 / ## 최근 한 일(원본 [[링크]]) / "
                "## 사람 결정 필요(![[00_index#사람 결정 필요]] 한 줄 유지). "
                "이번 작업에서 결정이나 결론이 나왔는데 40_knowledge/41_decisions/에 없으면 함께 남기고, "
                "목표나 진행 상황이 바뀌었으면 00_system/02_now.md도 갱신한다."}, ensure_ascii=False))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "init":
        init()
    elif cmd == "role" and len(argv) == 4 and argv[3] in ("supervisor", "worker") and agent_dir(argv[2]):
        set_role(argv[2], argv[3])
        build_index()
        print(f"{argv[2]}: {argv[3]}")
    elif cmd == "index":
        build_index()
    elif cmd == "digest":
        print(digest(argv[2] if len(argv) > 2 else None))
    elif cmd == "hook" and len(argv) > 2:
        hook(argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
