---
name: init
description: 프로젝트에 SmallBrain vault를 만든다. "smallbrain 시작", "vault 만들어줘", /smallbrain:init 요청에 사용.
---
# SmallBrain init

1. vault를 만든다. 위치는 기본 `<project>/vault`이고, 바꾸려면 `SMALLBRAIN_VAULT` 환경변수를 설정한다.
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brain.py" init
   ```
2. 사용자에게 이 프로젝트의 목표를 묻고 `vault/00_system/02_now.md`의 `## 목표`를 채운다.
3. 목표에 필요한 agent 2~3개(예: builder, reviewer)를 제안하고, 사용자가 동의하면 `/smallbrain:hire`로 만든다.
4. `vault/00_system/03_status.md`의 `## 현재 상태`를 갱신한다.
