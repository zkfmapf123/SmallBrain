# SmallBrain

[English](README.md)

Obsidian vault를 supervisor(메인 세션)와 sub-agent들의 공용 뇌로 쓰게 하는 Claude Code plugin입니다.

agent가 노트를 읽고 쓰는 걸 기억할 필요가 없습니다. agent가 시작할 때 hook이 필요한 맥락을 넣어 주고, 누가 어디에 쓸 수 있는지 검사하고, 기록을 남기지 않으면 작업을 끝내지 못하게 합니다.

## 동작 방식

| hook | 하는 일 |
|---|---|
| `SessionStart` | supervisor에게 현재 목표, 사람용 상태, 열린 스레드, 규칙을 넣어 줍니다 |
| `SubagentStart` | hire된 agent에게 짧은 digest를 넣어 줍니다: 현재 목표, 역할, 원칙, 나에게 온 스레드, 쓰기 규칙 |
| `PreToolUse` | `agent_type`으로 vault 쓰기를 검사합니다. agent는 자기 `journal/`, `reflections/`, 자기 이름의 스레드 turn에만 새 파일을 만들 수 있습니다. frontmatter는 필수이고, reflection에는 `signal`이 있어야 합니다 |
| `SubagentStop` | journal이나 turn을 남기지 않은 agent의 종료를 한 번 막습니다 |
| `Stop` | index를 다시 만들고, 7일 넘게 승인 대기 중인 노트를 archive하고, vault가 바뀌었으면 supervisor에게 `03_status.md` 갱신을 요구합니다 |

## 필요한 것

- plugin을 지원하는 Claude Code
- `python3` (표준 라이브러리만 사용)
- Obsidian은 선택입니다. 사람이 vault를 볼 때만 필요합니다

## 설치

사용할 프로젝트 폴더에서 로컬로 불러옵니다:

```bash
cd your-project
claude --plugin-dir /path/to/smallbrains
```

## 사용법

### 1. vault 만들기

```
/smallbrain:init
```

프로젝트에 `vault/`를 만들고 프로젝트 목표를 묻습니다. 다른 위치를 쓰려면 `SMALLBRAIN_VAULT` 환경변수를 설정합니다(프로젝트 루트 기준 상대 경로).

### 2. agent 고용

```
/smallbrain:hire builder 기능 구현 담당
/smallbrain:hire reviewer 코드와 테스트 리뷰 담당
```

호출할 때마다 `.claude/agents/<이름>.md`와 `vault/10_agents/NN_<이름>/`가 생깁니다. 새 agent가 보이지 않으면 세션을 다시 시작하세요.

### 3. 평소처럼 일 시키기

supervisor에게 "로그인 페이지 만들어 줘"처럼 지시합니다. supervisor가 hire된 agent에게 일을 맡기고, 맥락 주입과 기록은 hook이 처리합니다.

### 4. 여러 의견이 필요하면 회의

```
/smallbrain:meeting 인증 방식 결정
```

supervisor가 `vault/20_threads/`에 스레드를 열고 최대 3라운드를 돌립니다. 각 agent는 자기 turn 파일을 쓰고, 결정은 `40_knowledge/41_decisions/`에 남습니다.

### 5. 교훈 승격

```
/smallbrain:reflect
```

같은 교훈이 agent의 `reflections/`에 두 번 나오면 supervisor가 원칙(`status: trial`)으로 만듭니다. 기존 원칙과 충돌하면 `pending-approval`이 되어 상태 페이지에 뜹니다.

### 6. 상태 확인

Obsidian에서 `vault/00_system/03_status.md`를 엽니다. 현재 상태, 최근 한 일, 내가 결정할 것 세 섹션이 있습니다. 승인 대기 원칙은 여기서 승인하거나 거절합니다. 7일 동안 처리하지 않으면 자동으로 archive됩니다.

## vault 구조

```
vault/
├─ 00_system/
│  ├─ 00_index.md      # 자동 생성, 직접 수정 금지
│  ├─ 01_rules.md      # vault 규칙
│  ├─ 02_now.md        # agent용: 목표, 진행 상태, 다음 할 일
│  └─ 03_status.md     # 사람용: supervisor가 덮어씀
├─ 10_agents/NN_<이름>/
│  ├─ profile.md       # 역할
│  ├─ principles/      # 승격된 원칙 (supervisor만 씀)
│  ├─ reflections/     # 실패 신호에서 얻은 교훈
│  └─ journal/         # 작업 기록
├─ 20_threads/<YYYY-MM-DD-주제>/
│  ├─ index.md         # 안건, 합의 요약 (supervisor)
│  └─ turns/YYYYMMDD-HHMM-<이름>.md
├─ 30_projects/
├─ 40_knowledge/{41_decisions,42_lessons}/
└─ 90_archive/
```

## 디버깅

```bash
python3 scripts/brain.py digest builder   # builder가 시작할 때 받는 내용
python3 scripts/brain.py digest           # supervisor가 받는 내용
python3 scripts/brain.py index            # index 다시 만들기
python3 tests/test_brain.py               # 테스트 실행
```

## 한계

- `Write`/`Edit`만 검사합니다. Bash로 쓰는 파일은 쓰기 규칙을 우회합니다.
- 아직 없는 것: 라운드별 git commit, trial에서 active로 자동 전환, consolidate skill.
