---
name: init
description: 프로젝트에 SmallBrain vault를 만들고 팀 구조를 맞춘다. agent가 없으면 메인 세션이 팀장인 구조로 일꾼 agent를 만들고, 있으면 그 구조를 읽어 등록한다. "smallbrain 시작", "vault 만들어줘", /smallbrain:init 요청에 사용.
---
# SmallBrain init

1. 실행한다.
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brain.py" init
   ```
   vault 골격을 만들고, 프로젝트와 사용자 `.claude/agents/`의 agent를 등록하고(정의 파일은 수정하지 않음), `CLAUDE.md`에 SmallBrain 블록을 한 번 덧붙인다. 다시 실행해도 안전하다. vault 위치는 기본 `<project>/vault`, 바꾸려면 `SMALLBRAIN_VAULT` 환경변수.

2. 출력의 `STRUCTURE:` 줄에 따라 진행한다.
   - **`none`** (agent 없음): 메인 세션이 팀장이 된다. 사용자에게 프로젝트 목표를 묻고, 목표에 맞는 일꾼 agent 2~3개를 이름, 역할 한 줄, 필요한 tools와 함께 제안한다. 동의하면 `.claude/agents/<이름>.md`를 만든다:
     ```markdown
     ---
     name: <소문자-kebab-case>
     description: <supervisor가 언제 이 agent를 부를지 한 줄>
     tools: <예: Read, Grep, Glob, Edit, Write, Bash>
     ---
     <역할, 하지 않는 일, 완료 기준>
     ```
     일꾼에게는 `Agent` 도구를 주지 않는다(팀장은 메인 세션). 만든 뒤 init을 한 번 더 실행해 등록한다.
   - **`main-lead`**: 메인 세션이 팀장이다. 그대로 쓴다.
   - **`agent-lead`**: 출력의 "팀장:" agent가 다른 agent를 지휘한다. 메인 세션도 팀장 권한을 가진다. 그대로 쓴다.

3. 출력에 "tools를 안 적은 agent"가 있으면 사용자에게 알린다. 일꾼으로 시작하고, 실제로 다른 agent를 부르면 hook이 자동으로 팀장으로 바꾼다. 역할을 직접 정하려면 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brain.py" role <이름> supervisor|worker`.

4. 출력에 "건너뜀"이 있으면 이름이 소문자 kebab-case가 아닌 agent다. 사용자에게 알리고 이름을 바꿀지 묻는다.

5. 출력에 "CLAUDE.md에서 vault 기록과 겹칠 수 있는 줄"이 있으면 그 줄들을 사용자에게 보여 준다. SmallBrain 블록에 "vault 기록에는 적용되지 않는다"는 문장이 들어갔다는 것도 알린다. 사용자가 원하면 그 줄을 고친다.

6. `vault/00_system/02_now.md`의 `## 목표`가 비어 있으면 채운다. 등록된 agent의 `profile.md`가 "(역할 미정)"이면 agent 정의 파일을 읽고 3~5줄로 채운다. `03_status.md`의 `## 현재 상태`를 갱신한다.

7. 이번에 `.claude/agents/`에 파일을 새로 만들었으면 사용자에게 **세션을 다시 시작해야 새 agent를 부를 수 있다**고 알린다. Claude Code는 agent 정의를 세션 시작 때만 읽는다.
