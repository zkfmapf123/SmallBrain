---
name: meeting
description: 여러 SmallBrain agent의 의견을 모아 결정할 때 쓴다. 팀장(메인 세션이나 팀장 agent)이 vault에 스레드를 열고 라운드를 돌린다. /smallbrain:meeting <주제> 요청에 사용.
---
# SmallBrain meeting

인자: 주제, 참석 agent. 참석자를 안 정했으면 `.claude/agents/`에 정의된 agent 중 주제에 맞는 것을 고른다.
팀장 agent가 따로 있는 팀이면(`vault/00_system/00_index.md`의 agents에서 `(supervisor)`), 회의를 그 agent에게 맡겨도 된다. 팀장 agent는 같은 절차를 digest로 받는다.

1. 스레드를 연다: `vault/20_threads/YYYY-MM-DD-<주제-slug>/index.md`
   ```markdown
   ---
   type: thread
   author: <내 이름, 메인 세션이면 supervisor>
   status: open
   participants: [builder, reviewer]
   created: YYYY-MM-DD
   title: <주제>
   ---
   ## 안건
   ## 합의
   ## 남은 질문
   ```
2. 라운드마다 참석자를 부른다. 서로의 이번 라운드 답이 필요 없으면 병렬로 불러도 된다. 프롬프트:
   > `20_threads/<스레드>/`의 index.md와 지금까지의 발언을 읽고 안건에 대한 의견을 내라. 다른 참석자 의견에는 동의/반대를 근거와 함께 밝혀라.
3. 각 참석자의 보고는 hook이 그 agent의 `journal/`에 자동 저장한다. 쓰기 도구가 있는 agent는 `turns/YYYYMMDD-HHMM-<이름>.md`를 직접 남기기도 한다. 다음 라운드 참석자에게 앞 발언 내용을 프롬프트로 넘기거나 파일 경로를 알려 준다.
4. 라운드가 끝나면 `index.md`의 `## 합의`와 `## 남은 질문`을 갱신하고, 각 발언(turn 파일이나 journal)을 `[[링크]]`로 단다.
5. 최대 3라운드. 남은 질문이 없거나 입장이 굳으면 멈춘다. 의견이 갈리면 팀장이 근거를 적고 결정한다.
6. 결정을 `vault/40_knowledge/41_decisions/YYYY-MM-DD-<주제>.md`에 남긴다(frontmatter `type: decision`, 본문 배경 / 선택지 / 결정 / 근거, 스레드 링크). `index.md`를 `status: resolved`로 바꾼다.
7. `00_system/02_now.md`와 `00_system/03_status.md`를 갱신한다.
