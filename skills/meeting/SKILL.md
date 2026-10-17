---
name: meeting
description: 여러 SmallBrain agent의 의견을 모아 결정할 때 쓴다. supervisor(메인 세션)가 vault에 스레드를 열고 라운드를 돌린다. /smallbrain:meeting <주제> 요청에 사용.
---
# SmallBrain meeting

인자: 주제, 참석 agent. 참석자를 안 정했으면 주제에 맞는 hire된 agent를 고른다.

1. 스레드를 연다: `vault/20_threads/YYYY-MM-DD-<주제-slug>/index.md`
   ```markdown
   ---
   type: thread
   author: supervisor
   status: open
   participants: [builder, reviewer]
   created: YYYY-MM-DD
   title: <주제>
   ---
   ## 안건
   ## 합의
   ## 남은 질문
   ```
2. 라운드마다 참석자를 Task로 부른다. 서로의 이번 라운드 답을 볼 필요가 없으면 병렬로 불러도 된다(턴은 각자 새 파일이라 충돌하지 않는다). 프롬프트:
   > `20_threads/<스레드>/`의 index.md와 turns/를 읽고, 안건에 대한 의견을 `turns/YYYYMMDD-HHMM-<이름>.md`로 써라. 다른 참석자 의견에는 동의/반대를 근거와 함께 밝혀라.
3. 라운드가 끝나면 `index.md`의 `## 합의`와 `## 남은 질문`을 갱신한다. 턴 원문은 옮기지 말고 `[[링크]]`만 단다. agent에게는 이 요약이 digest로 주입된다.
4. 최대 3라운드. 남은 질문이 없거나 입장이 굳으면 멈춘다. 의견이 갈리면 supervisor가 근거를 적고 결정한다.
5. 결정을 `vault/40_knowledge/41_decisions/YYYY-MM-DD-<주제>.md`에 남긴다(frontmatter `type: decision`, 본문은 배경 / 선택지 / 결정 / 근거, 스레드 링크). 그 뒤 `index.md`를 `status: resolved`로 바꾼다.
6. `00_system/02_now.md`와 `00_system/03_status.md`를 갱신한다.
