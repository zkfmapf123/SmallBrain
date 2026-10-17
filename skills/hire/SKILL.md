---
name: hire
description: SmallBrain agent를 만든다(agent 정의 + vault 폴더를 한 번에). "agent 추가", "builder 고용", /smallbrain:hire <이름> <역할> 요청에 사용.
---
# SmallBrain hire

인자: agent 이름(소문자 kebab-case), 역할 한 줄.

1. 실행한다. `.claude/agents/<이름>.md`와 `vault/10_agents/NN_<이름>/`(profile, principles, reflections, journal)가 생긴다.
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brain.py" hire <이름> "<역할 한 줄>"
   ```
2. `.claude/agents/<이름>.md` 본문에 역할을 구체적으로 적는다: 무엇을 하고 무엇을 하지 않는지, 완료 기준, 필요하면 `model`/`tools` frontmatter. `## Brain` 섹션은 지우지 않는다.
3. `vault/10_agents/NN_<이름>/profile.md`에 같은 역할을 3~5줄로 요약한다. 이 내용이 매번 digest로 주입되므로 짧게 쓴다.
4. 새 agent가 Task의 agent 목록에 보이지 않으면 사용자에게 세션을 다시 시작하라고 알린다.
