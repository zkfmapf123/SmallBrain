---
name: init
description: 프로젝트에 SmallBrain vault를 만들고 .claude/agents/ 의 기존 agent를 전부 등록한다. "smallbrain 시작", "vault 만들어줘", agent 파일을 직접 추가한 뒤 등록할 때, /smallbrain:init 요청에 사용.
---
# SmallBrain init

1. 실행한다. vault 골격을 만들고 `.claude/agents/*.md`의 agent를 전부 vault에 등록한다(정의 파일은 수정하지 않음). 다시 실행해도 이미 등록된 agent는 건너뛴다. vault 위치는 기본 `<project>/vault`, 바꾸려면 `SMALLBRAIN_VAULT` 환경변수.
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brain.py" init
   ```
2. 출력에 "건너뜀"이 있으면 이름이 소문자 kebab-case가 아닌 agent다. 사용자에게 알리고, 이름을 바꿀지 묻는다.
3. `vault/00_system/02_now.md`의 `## 목표`가 비어 있으면 사용자에게 프로젝트 목표를 묻고 채운다.
4. 등록된 agent마다 `vault/10_agents/NN_<이름>/profile.md`에 역할이 "(역할 미정)"이면 agent 정의 파일을 읽고 3~5줄로 요약해 채운다.
5. agent가 하나도 없으면 목표에 맞는 agent 2~3개를 제안하고, 사용자가 동의하면 `/smallbrain:hire`로 만든다.
6. `vault/00_system/03_status.md`의 `## 현재 상태`를 갱신한다.
