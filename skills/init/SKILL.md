---
name: init
description: 프로젝트에 SmallBrain vault를 만들고 이미 정의된 agent를 등록한다. "smallbrain 시작", "vault 만들어줘", /smallbrain:init 요청에 사용.
---
# SmallBrain init

1. 실행한다. vault 골격을 만들고, 프로젝트와 사용자 `.claude/agents/`에 정의된 agent를 전부 vault에 등록한다(정의 파일은 수정하지 않음). 다시 실행해도 이미 등록된 agent는 건너뛴다. vault 위치는 기본 `<project>/vault`이고, 바꾸려면 `SMALLBRAIN_VAULT` 환경변수를 쓴다.
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brain.py" init
   ```
2. 출력에 "건너뜀"이 있으면 이름이 소문자 kebab-case가 아닌 agent다. 사용자에게 알리고 이름을 바꿀지 묻는다.
3. `vault/00_system/02_now.md`의 `## 목표`가 비어 있으면 사용자에게 프로젝트 목표를 묻고 채운다.
4. 등록된 agent의 `vault/10_agents/NN_<이름>/profile.md`가 "(역할 미정)"이면 agent 정의 파일을 읽고 역할을 3~5줄로 요약해 채운다.
5. `vault/00_system/03_status.md`의 `## 현재 상태`를 갱신한다.
