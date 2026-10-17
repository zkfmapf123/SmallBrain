"""brain.py 동작 확인. 실행: python3 tests/test_brain.py"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "brain.py"
FM = "---\ntype: {t}\nauthor: {a}\ncreated: 2026-10-17\n---\n본문\n"


class Project:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.v = self.root / "vault"
        self.env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.root), "HOME": str(self.root / "home")}

    def run(self, *args, data=None):
        r = subprocess.run([sys.executable, str(SCRIPT), *args], input=json.dumps(data or {}),
                           capture_output=True, text=True, env=self.env, cwd=self.root)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stdout

    def define(self, name, desc, tools="Read", home=None):
        f = (home or self.root) / ".claude/agents" / f"{name}.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        line = f"tools: {tools}\n" if tools is not None else ""
        f.write_text(f"---\nname: {name}\ndescription: {desc}\n{line}---\n원래 지침\n")
        return f

    def hook(self, event, **data):
        return self.run("hook", event, data=data)

    def write(self, agent, path, content="", tool="Write", agent_id="w1"):
        data = {"tool_name": tool, "tool_input": {"file_path": str(self.v / path), "content": content}}
        if agent:
            data.update(agent_type=agent, agent_id=agent_id)
        out = self.run("hook", "PreToolUse", data=data)
        return out["hookSpecificOutput"]["permissionDecision"] if out else "allow"

    def role(self, name):
        d = next(self.v.glob(f"10_agents/*_{name}"))
        return [l for l in (d / "profile.md").read_text().splitlines() if l.startswith("role:")][0][6:]


def ctx(out):
    return out["hookSpecificOutput"]["additionalContext"] if out else ""


# ---- 구조 A: agent가 없는 프로젝트 ----
a = Project()
(a.root / "CLAUDE.md").write_text("# 규칙\n- 저장 요청 없으면 채팅 출력만 한다.\n")
out = a.run("init")
assert "STRUCTURE: none" in out
assert "채팅 출력만" in out  # 충돌 가능 줄 안내
claude_md = (a.root / "CLAUDE.md").read_text()
assert claude_md.startswith("# 규칙") and claude_md.count("smallbrain:start") == 1
a.run("init")
assert (a.root / "CLAUDE.md").read_text().count("smallbrain:start") == 1  # 재실행해도 한 번
assert "메인 세션 (팀장)" in ctx(a.hook("SessionStart", session_id="s1"))

# ---- 구조 B: 팀장 agent가 일꾼 agent를 부르는 프로젝트 (sm-test와 같은 모양) ----
b = Project()
b.define("supervisor", "논의 감독", tools="Agent, Read, Grep, Glob, Write")
b.define("critic", "반론 담당", tools="Read, Grep, Glob, WebSearch")
b.define("builder", "구현 담당", tools="Read, Write, Edit")
b.define("helper", "tools 생략 agent", tools=None)
(b.root / ".claude/agents/Bad_Name.md").write_text("원래 지침\n")
out = b.run("init")
assert "STRUCTURE: agent-lead" in out and "팀장: supervisor" in out
assert "helper" in out and "Bad_Name" in out
assert b.role("supervisor") == "supervisor" and b.role("critic") == "worker" and b.role("helper") == "worker"
assert (b.root / ".claude/agents/critic.md").read_text().endswith("---\n원래 지침\n")  # 정의 파일 그대로

# 메인 세션: --agent로 띄워도(agent_type만 있고 agent_id 없음) 팀장 digest, 전체 쓰기
assert "메인 세션 (팀장)" in ctx(b.hook("SessionStart", session_id="s1", agent_type="supervisor"))
assert b.write(None, "00_system/02_now.md", FM.format(t="now", a="supervisor")) == "allow"
d = {"tool_name": "Write", "agent_type": "supervisor",
     "tool_input": {"file_path": str(b.v / "00_system/02_now.md"), "content": FM.format(t="now", a="x")}}
assert b.run("hook", "PreToolUse", data=d) == ""  # agent_id 없음 = 메인 세션, author 자유

# 팀장 agent: 팀장 digest + 공유 파일 쓰기 가능
c = ctx(b.hook("SubagentStart", agent_type="supervisor", agent_id="sup1"))
assert "`supervisor` agent (팀장)" in c and "회의 절차" in c and "지금 시각" in c
assert b.write("supervisor", "00_system/02_now.md", FM.format(t="now", a="supervisor"), agent_id="sup1") == "allow"
assert b.write("supervisor", "40_knowledge/41_decisions/d.md", FM.format(t="decision", a="supervisor"), agent_id="sup1") == "allow"

# background 팀장이 다시 깨어나도 digest는 한 번만
assert b.hook("SubagentStart", agent_type="supervisor", agent_id="sup1") == ""

# 쓰기 도구 없는 일꾼: 읽기 전용 규칙, 보고는 자동 저장
c = ctx(b.hook("SubagentStart", agent_type="critic", agent_id="cr1"))
assert "나는 파일을 쓰지 않는다" in c and "반성:" in c
b.hook("SubagentStop", agent_type="critic", agent_id="cr1", last_assistant_message="반론: 정의가 순환한다")
j = list(b.v.glob("10_agents/*_critic/journal/*.md"))
assert len(j) == 1 and "반론: 정의가 순환한다" in j[0].read_text() and "auto: true" in j[0].read_text()
b.hook("SubagentStop", agent_type="critic", agent_id="cr1", last_assistant_message="반론: 정의가 순환한다")
assert j[0].read_text().count("정의가 순환한다") == 1  # 같은 보고는 한 번만

# 쓰기 가능한 일꾼: 권한 검사
assert "reflections/" in ctx(b.hook("SubagentStart", agent_type="builder", agent_id="bd1"))
bd = next(b.v.glob("10_agents/*_builder")).relative_to(b.v).as_posix()
assert b.write("builder", f"{bd}/reflections/r.md", FM.format(t="reflection", a="builder").replace(
    "created", "signal: \"pnpm test 실패\"\ncreated"), agent_id="bd1") == "allow"
assert b.write("builder", f"{bd}/reflections/r2.md", FM.format(t="reflection", a="builder"), agent_id="bd1") == "deny"
assert b.write("builder", "00_system/02_now.md", FM.format(t="now", a="builder"), agent_id="bd1") == "deny"
assert b.write("builder", "20_threads/t/turns/20261017-1400-builder.md", FM.format(t="turn", a="builder"), agent_id="bd1") == "allow"
assert b.write("builder", "20_threads/t/turns/20261017-1400-critic.md", FM.format(t="turn", a="builder"), agent_id="bd1") == "deny"
assert b.write("builder", f"{bd}/reflections/x.md", FM.format(t="journal", a="critic"), agent_id="bd1") == "deny"
(b.v / bd / "reflections/old.md").write_text(FM.format(t="reflection", a="builder"))
assert b.write("builder", f"{bd}/reflections/old.md", "", tool="Edit", agent_id="bd1") == "deny"
assert b.write("Explore", "00_system/x.md", FM.format(t="x", a="x"), agent_id="ex1") == "deny"
assert b.write(None, "00_system/x.md", "제목만") == "deny"  # 메인도 frontmatter 필요
assert b.write(None, "../outside.md", "아무거나") == "allow"


def bash(agent, cmd, aid="bd1"):
    data = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    if agent:
        data.update(agent_type=agent, agent_id=aid)
    out = b.run("hook", "PreToolUse", data=data)
    return out["hookSpecificOutput"]["permissionDecision"] if out else "allow"


assert bash("builder", f"echo hi > {b.v}/00_system/02_now.md") == "deny"
assert bash("builder", "cp x.md vault/00_system/02_now.md") == "deny"
assert bash("builder", f"cat {b.v}/00_system/02_now.md && ls vault/") == "allow"  # 읽기는 허용
assert bash("builder", "grep -r x vault/ 2>&1 >/dev/null | head") == "allow"
assert bash("builder", "cat a.md | tee vault/x.md") == "deny"
assert bash("builder", "sed -i '' 's/a/b/' vault/00_system/02_now.md") == "deny"
assert bash("builder", "rm -rf vault/10_agents") == "deny"
assert bash("builder", "python3 -c \"open('vault/00_system/02_now.md','w').write('x')\"") == "deny"
assert bash("builder", "find vault -name '*.md' -delete") == "deny"
assert bash("builder", "echo hi > vault/x.md") == "deny"
assert bash("builder", "python3 -m pytest tests/") == "allow"  # vault와 무관한 명령
assert bash("builder", "echo hi > src/app.ts") == "allow"  # vault 밖 쓰기는 관여 안 함
assert bash("supervisor", f"echo hi > {b.v}/00_system/02_now.md", aid="sup1") == "allow"
assert bash(None, f"echo hi > {b.v}/00_system/02_now.md") == "allow"  # 메인 세션

# tools 생략 agent가 다른 agent를 부르면 그 자리에서 팀장으로 전환되고 팀장 규칙을 받는다
assert "나는 파일을 쓰지 않는다" not in ctx(b.hook("SubagentStart", agent_type="helper", agent_id="hp1"))
out = b.hook("PreToolUse", agent_type="helper", agent_id="hp1", tool_name="Agent", tool_input={"subagent_type": "critic"})
assert "이제 팀장 규칙이 적용된다" in ctx(out) and b.role("helper") == "supervisor"
assert b.hook("PreToolUse", agent_type="helper", agent_id="hp1", tool_name="Agent", tool_input={}) == ""  # 한 번만
assert b.hook("PreToolUse", tool_name="Agent", tool_input={}) == ""  # 메인 세션 호출은 무관
b.run("role", "helper", "worker")
assert b.role("helper") == "worker"

# 보고가 비어 있으면 transcript의 SubagentHandback에서 읽고, 그래도 없으면 나중에 다시 읽는다
tr = b.root / "t.jsonl"
b.hook("SubagentStart", agent_type="critic", agent_id="cr2")
b.hook("SubagentStop", agent_type="critic", agent_id="cr2", last_assistant_message="", agent_transcript_path=str(tr))
st = json.loads((b.v / ".smallbrain/agent-cr2.json").read_text())
assert st["pending"] is True
tr.write_text(json.dumps({"message": {"role": "assistant", "content": [
    {"type": "tool_use", "name": "SubagentHandback", "input": {"message": "핸드백 보고"}}]}}) + "\n")
b.hook("SessionStart", session_id="s2")  # sweep
assert any("핸드백 보고" in p.read_text() for p in b.v.glob("10_agents/*_critic/journal/*.md"))

# 처음 보는 agent(나중에 정의, 사용자 scope 포함)는 첫 호출에 자동 등록, 기본 agent는 제외
b.define("late-dev", "나중에 만든 개발자", tools="Read")
b.define("user-dev", "사용자 scope", tools="Read", home=b.root / "home")
for name, aid in (("late-dev", "x1"), ("user-dev", "x2")):
    assert f"digest — {name}" in ctx(b.hook("SubagentStart", agent_type=name, agent_id=aid))
b.hook("SubagentStart", agent_type="Explore", agent_id="x3")
assert not any("Explore" in p.name for p in (b.v / "10_agents").iterdir())

# Stop: vault가 바뀌었는데 03_status가 낡았으면 세션당 한 번만 요청
b.hook("SessionStart", session_id="s3")
time.sleep(0.05)
(b.v / "30_projects/x.md").write_text(FM.format(t="doc", a="supervisor"))
assert b.hook("Stop", session_id="s3")["decision"] == "block"
assert b.hook("Stop", session_id="s3") == ""  # 두 번째는 막지 않음
b.hook("SessionStart", session_id="s4")
time.sleep(0.05)
(b.v / "30_projects/y.md").write_text(FM.format(t="doc", a="supervisor"))
(b.v / "00_system/03_status.md").write_text(FM.format(t="status", a="supervisor"))
time.sleep(0.05)
b.hook("SubagentStart", agent_type="critic", agent_id="cr4")
b.hook("SubagentStop", agent_type="critic", agent_id="cr4", last_assistant_message="상태 갱신 뒤 저장된 보고")
assert b.hook("Stop", session_id="s4") == ""  # 상태 갱신 뒤 자동 저장된 journal로는 다시 요청하지 않음
# vault 밖 프로젝트 파일만 고쳐도 요청한다. 프로젝트 밖 파일(~/.claude 메모리 등)은 세지 않는다
b.hook("SessionStart", session_id="s5")
b.hook("PreToolUse", session_id="s5", tool_name="Write", tool_input={"file_path": "/tmp/elsewhere.md"})
assert b.hook("Stop", session_id="s5") == ""
b.hook("PreToolUse", session_id="s5", tool_name="Edit", tool_input={"file_path": str(b.root / "reference/a.md")})
out = b.hook("Stop", session_id="s5")
assert out["decision"] == "block" and "30_projects" in out["reason"]
assert "직접 한 작업" in ctx(b.hook("SessionStart", session_id="s6"))

# 논의 요청이면 회의 스레드: 메인 세션과 팀장 agent에게 안내, 스레드 없으면 Stop에서 한 번 요청
b.hook("SessionStart", session_id="d1")
assert b.hook("UserPromptSubmit", session_id="d1", prompt="로그인 버튼 고쳐줘") == ""
assert "회의 스레드" not in ctx(b.hook("SubagentStart", session_id="d1", agent_type="supervisor", agent_id="sup9"))
assert "회의" in ctx(b.hook("UserPromptSubmit", session_id="d1", prompt="1+1은 왜 2인지 논의해줘"))
assert "회의 스레드로 진행" in ctx(b.hook("SubagentStart", session_id="d1", agent_type="supervisor", agent_id="sup10"))
assert "회의 스레드로 진행" not in ctx(b.hook("SubagentStart", session_id="d1", agent_type="critic", agent_id="cr9"))
time.sleep(0.05)
(b.v / "00_system/03_status.md").write_text(FM.format(t="status", a="supervisor"))
assert b.hook("Stop", session_id="d1", background_tasks=[{"id": "sup10"}]) == ""  # 팀장 agent가 아직 일하는 중
assert b.hook("UserPromptSubmit", session_id="d1",
              prompt="<task-notification>\n<summary>Agent \"논의\" finished</summary>") == ""  # 알림은 무시
out = b.hook("Stop", session_id="d1")
assert out["decision"] == "block" and "회의 스레드가 없다" in out["reason"]
assert b.hook("Stop", session_id="d1") == ""  # 한 번만
b.hook("UserPromptSubmit", session_id="d1", prompt="인증 방식 토론해줘")
time.sleep(0.05)
t2 = b.v / "20_threads/2026-10-17-auth-method"
t2.mkdir(parents=True)
(t2 / "index.md").write_text("---\ntype: thread\nauthor: supervisor\nstatus: open\ncreated: 2026-10-17\n---\n")
(b.v / "00_system/03_status.md").write_text(FM.format(t="status", a="supervisor"))
assert b.hook("Stop", session_id="d1") == ""  # 스레드가 있고 상태도 최신이면 요청 없음
import shutil
shutil.rmtree(t2)

# /compact와 resume은 같은 session_id로 SessionStart가 다시 온다: 논의 표시와 시작 시각 유지, digest는 다시 주입
b.hook("SessionStart", session_id="c1", source="startup")
b.hook("UserPromptSubmit", session_id="c1", prompt="배포 방식 논의해줘")
before = json.loads((b.v / ".smallbrain/session-c1.json").read_text())
assert "메인 세션 (팀장)" in ctx(b.hook("SessionStart", session_id="c1", source="compact"))
assert json.loads((b.v / ".smallbrain/session-c1.json").read_text()) == before
assert "discussion" not in json.loads(b.hook("SessionStart", session_id="c2", source="clear") and
                                      (b.v / ".smallbrain/session-c2.json").read_text())  # /clear는 새 세션

# vault가 아무리 커져도 digest 크기는 일정 범위 안
big = Project()
for n in ("lead", "w1"):
    big.define(n, "d")
big.run("init")
for i in range(100):
    d = big.v / f"20_threads/2026-10-{i:03d}-t"
    d.mkdir(parents=True)
    (d / "index.md").write_text(f"---\ntype: thread\nauthor: lead\ncreated: 2026-10-17\nstatus: open\nparticipants: [w1]\n---\n")
for i in range(50):
    (big.v / f"40_knowledge/42_lessons/l{i}.md").write_text(f"---\ntype: principle\nauthor: lead\ncreated: 2026-10-17\nstatus: active\ntitle: 교훈 {i} 긴 문장 긴 문장 긴 문장\n---\n")
w1 = next(big.v.glob("10_agents/*_w1"))
for i in range(30):
    (w1 / f"principles/p{i}.md").write_text(f"---\ntype: principle\nauthor: lead\ncreated: 2026-10-17\nstatus: trial\ntitle: 원칙 {i} 긴 문장 긴 문장\n---\n")
for i in range(200):
    (w1 / f"journal/j{i}.md").write_text("---\ntype: journal\nauthor: w1\ncreated: 2026-10-17\n---\n" + "보고 " * 2000)
(big.v / "00_system/02_now.md").write_text("---\ntype: now\nauthor: lead\ncreated: 2026-10-17\n---\n" + ("긴 줄 " * 300 + "\n") * 300)
for who in (None, "w1"):
    size = len(big.run("digest", *([who] if who else [])).encode())
    assert size < 10000, (who, size)

# 하루 지난 상태 파일 정리
old = b.v / ".smallbrain/agent-old.json"
old.write_text("{}")
os.utime(old, (time.time() - 90000, time.time() - 90000))
b.hook("SessionStart", session_id="s5")
assert not old.exists()

# 스레드, 승인 대기, 만료, index
t = b.v / "20_threads/2026-10-17-auth"
(t / "turns").mkdir(parents=True)
(t / "index.md").write_text("---\ntype: thread\nauthor: supervisor\nstatus: open\n"
                            "participants: [builder, critic]\ncreated: 2026-10-17\n---\n")
assert "20_threads/2026-10-17-auth/" in b.run("digest", "critic")
p = b.v / bd / "principles"
(p / "new.md").write_text("---\ntype: principle\nauthor: supervisor\nstatus: pending-approval\n"
                          f"created: {time.strftime('%Y-%m-%d')}\ntitle: 테스트 먼저\n---\n")
(p / "old.md").write_text("---\ntype: principle\nauthor: supervisor\nstatus: pending-approval\ncreated: 2026-01-01\n---\n")
(p / "ok.md").write_text("---\ntype: principle\nauthor: supervisor\nstatus: trial\ncreated: 2026-10-17\ntitle: 브라우저로 확인한다\n---\n")
b.run("index")
index = (b.v / "00_system/00_index.md").read_text()
assert "principles/new" in index and "2026-10-17-auth" in index and "(supervisor)" in index
assert not (p / "old.md").exists() and (b.v / "90_archive" / bd / "principles/old.md").exists()
assert "[trial] 브라우저로 확인한다" in b.run("digest", "builder")

print("OK")
