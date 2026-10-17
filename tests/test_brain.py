"""brain.py 동작 확인. 실행: python3 tests/test_brain.py"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "brain.py"
TMP = Path(tempfile.mkdtemp()).resolve()
V = TMP / "vault"
ENV = {**os.environ, "CLAUDE_PROJECT_DIR": str(TMP)}
FM = "---\ntype: journal\nauthor: {a}\ncreated: 2026-10-17\n---\n본문\n"


def run(*args, data=None):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], input=json.dumps(data or {}),
                       capture_output=True, text=True, env=ENV, cwd=TMP)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stdout


def write(agent, path, content="", tool="Write"):
    data = {"tool_name": tool, "tool_input": {"file_path": str(V / path), "content": content}}
    if agent:
        data["agent_type"] = agent
    out = run("hook", "PreToolUse", data=data)
    return out["hookSpecificOutput"]["permissionDecision"] if out else "allow"


# init, hire
run("init")
assert (V / "00_system/00_index.md").exists() and (V / "00_system/03_status.md").exists()
run("hire", "builder", "구현 담당")
run("hire", "code-reviewer", "리뷰 담당")
assert (TMP / ".claude/agents/builder.md").exists()
assert (V / "10_agents/11_builder/journal").is_dir() and (V / "10_agents/12_code-reviewer").is_dir()

# 이미 있던 agent는 init 재실행으로 등록되고, 정의 파일은 그대로다
legacy = TMP / ".claude/agents/legacy-dev.md"
legacy.write_text("---\nname: legacy-dev\ndescription: 기존 개발자\n---\n원래 지침\n")
(TMP / ".claude/agents/Bad_Name.md").write_text("원래 지침\n")
out = run("init")
assert "legacy-dev" in out and "Bad_Name" in out
assert "기존 개발자" in (V / "10_agents/13_legacy-dev/profile.md").read_text()
assert legacy.read_text().endswith("원래 지침\n") and "## Brain" not in legacy.read_text()
assert not (V / "10_agents/14_builder").exists()  # 재실행해도 중복 등록 없음

# PreToolUse 권한
assert write("builder", "10_agents/11_builder/journal/2026-10-17-1400.md", FM.format(a="builder")) == "allow"
assert write("smallbrain:builder", "10_agents/11_builder/journal/x.md", FM.format(a="builder")) == "allow"
assert write("builder", "00_system/02_now.md", FM.format(a="builder")) == "deny"
assert write("builder", "10_agents/12_code-reviewer/journal/x.md", FM.format(a="builder")) == "deny"
assert write("builder", "10_agents/11_builder/principles/x.md", FM.format(a="builder")) == "deny"
assert write("builder", "20_threads/t/turns/20261017-1400-builder.md", FM.format(a="builder")) == "allow"
assert write("builder", "20_threads/t/turns/20261017-1400-code-reviewer.md", FM.format(a="builder")) == "deny"
assert write("builder", "10_agents/11_builder/journal/x.md", FM.format(a="code-reviewer")) == "deny"  # author 불일치
assert write("builder", "10_agents/11_builder/reflections/r.md",
             "---\ntype: reflection\nauthor: builder\ncreated: 2026-10-17\n---\n") == "deny"  # signal 없음
assert write("builder", "10_agents/11_builder/reflections/r.md",
             "---\ntype: reflection\nauthor: builder\ncreated: 2026-10-17\nsignal: \"[[t/turns/x]]\"\n---\n") == "allow"
assert write("Explore", "00_system/x.md", FM.format(a="x")) == "deny"  # hire 안 된 agent
assert write(None, "00_system/02_now.md", "제목만") == "deny"  # main도 frontmatter 필요
assert write(None, "00_system/02_now.md", "", tool="Edit") == "allow"
assert write(None, "../outside.md", "아무거나") == "allow"  # vault 밖
(V / "10_agents/11_builder/journal/old.md").write_text(FM.format(a="builder"))
assert write("builder", "10_agents/11_builder/journal/old.md", FM.format(a="builder")) == "deny"  # 기존 파일

# SubagentStart digest, SubagentStop 기록 강제
out = run("hook", "SubagentStart", data={"agent_type": "builder", "agent_id": "a1"})
ctx = out["hookSpecificOutput"]["additionalContext"]
assert "digest — builder" in ctx and "구현 담당" in ctx
assert run("hook", "SubagentStart", data={"agent_type": "Explore", "agent_id": "a2"}) == ""
time.sleep(0.05)
stop = {"agent_type": "builder", "agent_id": "a1"}
assert run("hook", "SubagentStop", data=stop)["decision"] == "block"
assert run("hook", "SubagentStop", data={**stop, "stop_hook_active": True}) == ""  # 루프 방지
run("hook", "SubagentStart", data={"agent_type": "builder", "agent_id": "a3"})
time.sleep(0.05)
(V / "10_agents/11_builder/journal/2026-10-17-1500.md").write_text(FM.format(a="builder"))
assert run("hook", "SubagentStop", data={"agent_type": "builder", "agent_id": "a3"}) == ""

# 스레드, Stop의 03_status 강제
out = run("hook", "SessionStart", data={"session_id": "s1"})
assert "supervisor" in out["hookSpecificOutput"]["additionalContext"]
time.sleep(0.05)
t = V / "20_threads/2026-10-17-auth"
(t / "turns").mkdir(parents=True)
(t / "index.md").write_text("---\ntype: thread\nauthor: supervisor\nstatus: open\n"
                            "participants: [builder, code-reviewer]\ncreated: 2026-10-17\n---\n")
(t / "turns/20261017-1600-builder.md").write_text(FM.format(a="builder"))
assert run("hook", "Stop", data={"session_id": "s1"})["decision"] == "block"
(V / "00_system/03_status.md").write_text("---\ntype: status\nauthor: supervisor\ncreated: 2026-10-17\n---\n갱신\n")
assert run("hook", "Stop", data={"session_id": "s1"}) == ""
digest = run("digest", "code-reviewer")
assert "20_threads/2026-10-17-auth/" in digest and "(내 차례)" in digest

# 승인 대기, 만료, index
p = V / "10_agents/11_builder/principles"
(p / "new.md").write_text("---\ntype: principle\nauthor: supervisor\nstatus: pending-approval\n"
                          f"created: {time.strftime('%Y-%m-%d')}\ntitle: 테스트 먼저\n---\n")
(p / "old.md").write_text("---\ntype: principle\nauthor: supervisor\nstatus: pending-approval\n"
                          "created: 2026-01-01\n---\n")
(p / "ok.md").write_text("---\ntype: principle\nauthor: supervisor\nstatus: trial\n"
                         "created: 2026-10-17\ntitle: 브라우저로 확인한다\n---\n")
run("index")
index = (V / "00_system/00_index.md").read_text()
assert "principles/new" in index and "2026-10-17-auth" in index
assert not (p / "old.md").exists() and (V / "90_archive/10_agents/11_builder/principles/old.md").exists()
assert "[trial] 브라우저로 확인한다" in run("digest", "builder")

print("OK", TMP)
