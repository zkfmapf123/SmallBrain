---
name: reflect
description: SmallBrain agent의 반성 노트를 원칙으로 승격하거나 원칙을 정리할 때 쓴다. 같은 교훈이 두 번 나왔을 때, 사용자가 원칙을 승인/거절할 때, 원칙이 너무 많을 때. /smallbrain:reflect 요청에 사용.
---
# SmallBrain reflect

supervisor(메인 세션)가 실행한다. sub-agent는 `principles/`를 쓸 수 없다.

1. 대상 agent의 `vault/10_agents/NN_<이름>/reflections/`를 읽고 원인이나 다음 규칙이 같은 것이 2번 이상 나온 것을 찾는다. 한 번뿐이면 승격하지 않는다.
2. 원칙 노트를 만든다: `vault/10_agents/NN_<이름>/principles/YYYY-MM-DD-<slug>.md`
   ```markdown
   ---
   type: principle
   author: supervisor
   status: trial
   created: YYYY-MM-DD
   title: 한 줄 규칙 (digest에는 이 줄만 들어간다)
   ---
   근거: [[반성1]], [[반성2]]
   ```
   기존 원칙과 충돌하면 `status: pending-approval`로 만든다. 그러면 `03_status.md`의 "사람 결정 필요"에 뜨고, 7일 동안 처리되지 않으면 자동으로 archive된다.
3. 여러 agent에 공통이면 `vault/40_knowledge/42_lessons/`에 같은 형식으로 만든다.
4. 사용자가 승인하면 `status: trial`로, 거절하면 `90_archive/`로 옮긴다.
5. trial 원칙인데 같은 실수가 다시 reflections에 나오면 원칙을 고치거나 지운다. 재발 없이 여러 작업을 지났으면 `active`로 바꾼다.
6. 한 agent의 원칙이 10개를 넘으면 겹치는 것을 합친다.
