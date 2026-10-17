#!/usr/bin/env python3
"""SmallBrain: Obsidian vault를 supervisor(메인 세션)와 sub-agent들의 공용 뇌로 쓰게 한다.

  brain.py init                  vault 골격 생성
  brain.py hire <name> [역할]    agent 정의 + vault 폴더 생성
  brain.py index                 00_index 재생성 + 만료 처리
  brain.py digest [agent]        주입될 digest 출력 (디버깅용)
  brain.py hook <event>          Claude Code hook 처리 (stdin: hook JSON)

stdlib만 쓴다. vault 위치는 $SMALLBRAIN_VAULT (기본 <project>/vault).
"""
import json
import os
import re
import shutil
import sys
import time
from datetime import date
from pathlib import Path

PROJECT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
VAULT = (PROJECT / os.environ.get("SMALLBRAIN_VAULT", "vault")).resolve()
STATE = VAULT / ".smallbrain"
EXPIRE_DAYS = 7
NOW_LINES = 40
PRINCIPLE_MAX = 10
TURN_RE = re.compile(r"^\d{8}-\d{4}-(.+)\.md$")
DIRS = ["00_system", "10_agents", "20_threads", "30_projects",
        "40_knowledge/41_decisions", "40_knowledge/42_lessons", "90_archive"]

RULES = """---
type: rules
author: smallbrain
created: {today}
---
# SmallBrain vault 규칙

이 vault는 supervisor(메인 세션)와 sub-agent들의 공용 뇌다. 사람은 `03_status.md`만 보면 된다.

## 폴더
- `00_system`: `00_index`(자동 생성, 직접 수정 금지), `01_rules`, `02_now`(agent용 목표·상태), `03_status`(사람용, 덮어쓰기)
- `10_agents/NN_<name>/`: `profile`(역할), `principles/`(승격된 원칙), `reflections/`(반성), `journal/`(작업 기록)
- `20_threads/<YYYY-MM-DD-주제>/`: `index.md`(안건·합의 요약, supervisor 관리), `turns/YYYYMMDD-HHMM-<name>.md`(발언, 새 파일만)
- `30_projects`: 산출물 문서
- `40_knowledge/41_decisions`: 결정(배경/선택지/결정/근거), `42_lessons`: 여러 agent 공통 교훈
- `90_archive`: 정리된 노트, 7일 넘게 승인 대기한 노트

## 모든 노트
- frontmatter 필수: `type`, `author`, `created`. reflection은 `signal`(근거 링크나 측정값) 필수.
- 다른 노트는 `[[링크]]`로 참조한다.
- 추정은 "가정:", 확인 안 한 것은 "확인 못 함".

## 쓰기 권한 (hook이 강제)
- sub-agent: 자기 `journal/`, `reflections/`, 스레드 `turns/`에 새 파일만.
- supervisor: 전부. 공유 파일(`00_system`, `principles/`, `41_decisions`, 스레드 `index.md`)은 supervisor만 고친다.

## 원칙 승격
- 같은 교훈이 reflections에 2번 나오면 supervisor가 `principles/`에 원칙 노트를 만든다.
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
---
# {name}
{role}
"""

AGENT = """---
name: {name}
description: {desc}
---
{role}

## Brain
시작할 때 주입되는 SmallBrain digest가 내 맥락이다. 더 필요하면 digest에 적힌 경로의 원본을 읽는다.
- vault에는 `{own}/journal/`, `{own}/reflections/`, `{vault}/20_threads/<스레드>/turns/YYYYMMDD-HHMM-{name}.md`에 **새 파일만** 만든다. 그 밖은 읽기만 한다.
- 끝내기 전에 기록을 하나 이상 남긴다. 회의 중이면 turn, 아니면 journal(한 일 / 결과 / 검증한 것 / 확인 못 한 것).
- 테스트 실패, 리뷰 지적, 사용자 정정 같은 실패 신호가 있었으면 `reflections/`에 반성 노트를 쓴다.
- 추정은 "가정:", 확인하지 않은 것은 "확인 못 함"으로 쓴다.
"""

SUPERVISOR_RULES = """## supervisor 규칙 (SmallBrain)
- 일은 hire된 agent에게 맡긴다. 그들은 시작할 때 digest를 자동으로 받으니 프롬프트에는 이번 작업과 관련 vault 경로만 적는다.
- 여러 agent의 의견이 필요하면 `/smallbrain:meeting`을 쓴다.
- agent 결과를 받으면 `00_system/02_now.md`를 갱신하고, 결정은 `40_knowledge/41_decisions/`에 남긴다.
- 실패 신호를 본 agent는 반성을 남긴다. 같은 교훈이 2번이면 `/smallbrain:reflect`로 원칙을 승격한다.
- vault를 바꾼 응답을 끝내기 전에 `00_system/03_status.md`를 덮어쓴다(현재 상태 / 최근 한 일 / 사람 결정 필요 embed 유지). 안 하면 Stop hook이 막는다.
- `00_system/00_index.md`는 스크립트가 만든다. 직접 고치지 않는다."""

AGENT_RULES = """## 쓰기 규칙
- 새 파일만: `{own}/journal/YYYY-MM-DD-HHMM.md`, `{own}/reflections/YYYY-MM-DD-주제.md`, `20_threads/<스레드>/turns/YYYYMMDD-HHMM-{agent}.md`
- frontmatter: `type`(journal | reflection | turn), `author: {agent}`, `created: YYYY-MM-DD`. reflection은 `signal` 필수.
- 끝내기 전에 기록 하나 이상(회의 중이면 turn, 아니면 journal). 없으면 종료가 막힌다.
- 실패 신호(테스트 실패, 리뷰 지적, 사용자 정정)가 있었으면 reflections/에 남긴다:
  ---
  type: reflection
  author: {agent}
  created: YYYY-MM-DD
  signal: "근거 링크나 측정값"
  ---
  - 무슨 일: / - 원인: / - 다음 규칙:
- 공유 파일을 바꿔야 하면 직접 고치지 말고 turn이나 최종 답변에 제안으로 적는다."""


def today():
    return date.today().isoformat()


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
        n_pr = len(titles(d / "principles"))
        n_rf = len(list((d / "reflections").glob("*.md")))
        agents.append(f"- [[{rel(d)}/profile|{d.name.partition('_')[2]}]] — 원칙 {n_pr}개, 반성 {n_rf}개")
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


def digest(agent=None):
    now = clip(meta(VAULT / "00_system" / "02_now.md")[1], NOW_LINES)
    lessons = titles(VAULT / "40_knowledge" / "42_lessons")
    if agent:
        d = agent_dir(agent)
        own = rel(d)
        principles = titles(d / "principles")
        warn = [f"경고: 원칙 {len(principles)}개. supervisor에게 정리(합치기)를 제안한다."] \
            if len(principles) > PRINCIPLE_MAX else []
        mine = [t for t in threads() if agent in t["parts"] or "all" in t["parts"]]
        lines = [f"- `{t['path']}/` — 턴 {t['turns']}개, 마지막 {t['last'] or '-'}"
                 + (" (내 차례)" if t["last"] != agent else "") for t in mine]
        return "\n\n".join([
            f"# SmallBrain digest — {agent}\nvault: `{VAULT}` (아래 경로는 vault 기준)",
            "## 지금 (00_system/02_now.md)\n" + now,
            f"## 내 역할 ({own}/profile.md)\n" + meta(d / "profile.md")[1].strip(),
            "## 내 원칙\n" + "\n".join(principles or ["- 아직 없음"]) + ("\n" + warn[0] if warn else ""),
            "## 공통 교훈\n" + "\n".join(lessons or ["- 아직 없음"]),
            "## 나에게 열린 스레드\n" + "\n".join(lines or ["- 없음"]),
            AGENT_RULES.format(own=own, agent=agent),
        ])
    status = clip(meta(VAULT / "00_system" / "03_status.md")[1], 30)
    names = [d.name.partition("_")[2] for d in agent_dirs()]
    n_pending = sum(1 for p in notes() if meta(p)[0].get("status") == "pending-approval")
    open_threads = [f"- `{t['path']}/` — {t['title']}, 마지막 {t['last'] or '-'}" for t in threads()]
    return "\n\n".join([
        f"# SmallBrain — supervisor\nvault: `{VAULT}`",
        "## 지금 (00_system/02_now.md)\n" + now,
        "## 사람용 상태 (00_system/03_status.md)\n" + status,
        "## 열린 스레드\n" + "\n".join(open_threads or ["- 없음"]),
        f"## agents\n{', '.join(names) or '없음 (/smallbrain:hire 로 추가)'}\n사람 결정 대기: {n_pending}건",
        SUPERVISOR_RULES,
    ])


NAME_RE = re.compile(r"[a-z][a-z0-9-]*")


def init():
    """vault를 만들고 .claude/agents/ 에 이미 있는 agent를 전부 등록한다. 다시 실행해도 안전하다."""
    for d in DIRS:
        (VAULT / d).mkdir(parents=True, exist_ok=True)
    for name, tpl in (("01_rules.md", RULES), ("02_now.md", NOW), ("03_status.md", STATUS)):
        write_new(VAULT / "00_system" / name, tpl.replace("{today}", today()))
    added, skipped = [], []
    for f in sorted((PROJECT / ".claude" / "agents").glob("*.md")):
        fm = meta(f)[0]
        name = fm.get("name") or f.stem
        if not NAME_RE.fullmatch(name):
            skipped.append(name)
        elif not agent_dir(name):
            register(name, fm.get("description") or "")
            added.append(name)
    build_index()
    print(f"vault 준비됨: {VAULT}")
    if added:
        print(f"기존 agent 등록: {', '.join(added)}")
    if skipped:
        print(f"이름이 소문자 kebab-case가 아니라 건너뜀: {', '.join(skipped)}")


def register(name, role):
    """vault에 agent 폴더를 만든다. agent 정의 파일은 건드리지 않는다."""
    d = agent_dir(name)
    if not d:
        nums = [int(x.name.partition("_")[0]) for x in agent_dirs() if x.name.partition("_")[0].isdigit()]
        d = VAULT / "10_agents" / f"{max(nums, default=10) + 1}_{name}"
    for sub in ("principles", "reflections", "journal"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    write_new(d / "profile.md", PROFILE.format(today=today(), name=name, role=role or "(역할 미정)"))
    return d


def hire(name, role=""):
    if not NAME_RE.fullmatch(name):
        sys.exit("agent 이름은 소문자 kebab-case여야 한다 (예: builder, code-reviewer)")
    if not (VAULT / "10_agents").is_dir():
        sys.exit("vault가 없다. 먼저 init")
    d = register(name, role)
    vault_rel = os.path.relpath(VAULT, PROJECT)
    write_new(PROJECT / ".claude" / "agents" / f"{name}.md", AGENT.format(
        name=name, desc=role or "TODO: supervisor가 언제 이 agent를 부를지 한 줄로",
        role=role, own=f"{vault_rel}/{rel(d)}", vault=vault_rel))
    build_index()
    print(f"agent 준비됨: .claude/agents/{name}.md, {rel(d)}/")


def check_write(data):
    """PreToolUse: 차단 사유를 돌려준다. 허용이면 None."""
    # ponytail: Write/Edit만 검사한다. Bash로 쓰는 파일은 못 막는다. 우회가 실측되면 Bash 명령 검사 추가.
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
    agent = (data.get("agent_type") or "").split(":")[-1]
    if agent:
        d = agent_dir(agent)
        if not d:
            return f"SmallBrain: vault는 hire된 agent만 쓴다('{agent}'는 hire 안 됨). 결과는 supervisor에게 돌려줘라."
        own = d.relative_to(VAULT).parts
        in_own = (len(parts) == len(own) + 2 and parts[:len(own)] == own
                  and parts[len(own)] in ("journal", "reflections"))
        is_turn = (len(parts) == 4 and parts[0] == "20_threads" and parts[2] == "turns"
                   and turn_author(parts[3]) == agent)
        own_s = "/".join(own)
        if not (in_own or is_turn):
            return (f"SmallBrain: {agent}는 vault에서 {own_s}/journal/, {own_s}/reflections/, "
                    f"20_threads/<스레드>/turns/YYYYMMDD-HHMM-{agent}.md 에만 새 파일을 쓸 수 있다. "
                    "공유 파일 변경은 turn이나 최종 답변에 제안으로 적어라.")
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


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


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
    agent = (data.get("agent_type") or "").split(":")[-1]

    if event == "SessionStart":
        (STATE / f"session-{data.get('session_id')}").write_text(str(time.time()))
        build_index()
        emit_context(event, digest())

    elif event == "SubagentStart":
        if agent_dir(agent):
            (STATE / f"agent-{data.get('agent_id')}").write_text(str(time.time()))
            emit_context(event, digest(agent))

    elif event == "PreToolUse":
        reason = check_write(data)
        if reason:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": reason}}, ensure_ascii=False))

    elif event == "SubagentStop":
        sf = STATE / f"agent-{data.get('agent_id')}"
        d = agent_dir(agent)
        if not d or not sf.exists():
            return
        if data.get("stop_hook_active"):  # 이미 한 번 막았다. 무한 루프 방지
            sf.unlink()
            return
        start = float(sf.read_text())
        turns = (VAULT / "20_threads").glob("*/turns/*.md")
        mine = list(d.rglob("*.md")) + [p for p in turns if turn_author(p.name) == agent]
        if any(p.stat().st_mtime >= start for p in mine):
            sf.unlink()
        else:
            block(f"SmallBrain: 작업 기록이 없다. 끝내기 전에 {rel(d)}/journal/YYYY-MM-DD-HHMM.md"
                  "(한 일 / 결과 / 검증한 것 / 확인 못 한 것)를 남겨라. 회의 중이면 turn을 쓴다. "
                  "실패 신호가 있었으면 reflections/에도 남긴다.")

    elif event == "Stop":
        if data.get("stop_hook_active"):
            return
        build_index()
        sf = STATE / f"session-{data.get('session_id')}"
        if not sf.exists():
            return
        start = float(sf.read_text())
        skip = {"00_system/00_index.md", "00_system/03_status.md"}
        changed = [p.stat().st_mtime for p in notes() if rel(p) not in skip and p.stat().st_mtime >= start]
        status = VAULT / "00_system" / "03_status.md"
        if changed and (not status.exists() or status.stat().st_mtime < max(changed)):
            block("SmallBrain: 이번 세션에 vault가 바뀌었는데 00_system/03_status.md가 그보다 오래됐다. "
                  "끝내기 전에 덮어써라: ## 현재 상태 / ## 최근 한 일(원본 [[링크]]) / "
                  "## 사람 결정 필요(![[00_index#사람 결정 필요]] 유지).")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "init":
        init()
    elif cmd == "hire" and len(argv) > 2:
        hire(argv[2], " ".join(argv[3:]))
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
