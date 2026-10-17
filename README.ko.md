# SmallBrain

[English](README.md)

Claude Code에서 agent 여러 개를 같이 굴릴 때, Obsidian vault(그냥 md 파일 폴더)를 걔네들 공용 뇌로 쓰게 해 주는 플러그인이다.

## 왜 만들었나

Claude Code로 agent 팀을 만들어서 게임을 만들어 본 적이 있다. 내가 대화하는 메인 Claude가 팀장 역할을 하고, 기획, 개발, QA 같은 agent들한테 일을 나눠 주는 식이었다. 기록은 전부 Obsidian vault에 남기라고 규칙을 적어 뒀다.

처음엔 잘 됐다. 그런데 며칠 지나니까 규칙이 슬슬 안 지켜졌다.

- 팀장이 "너 이거 고쳐라" 하고 vault에 적어 놔도, 정작 그 agent는 그 노트를 안 읽었다. 같은 실수를 또 했다.
- 목차 노트가 낡았다. 이미 폐기한 게임이 아직 "기준 게임"으로 남아 있었다.
- 그날그날 남기라던 로그가 첫날 이후로 하나도 없었다.

원인은 하나였다. 규칙이 글로만 있었다. 글로 적은 규칙은 Claude가 까먹으면 끝이다.

그래서 이번엔 규칙을 글이 아니라 장치로 만들었다. agent가 기억할 필요 없이, Claude Code가 알아서 읽혀 주고, 막고, 확인하게 했다.

## 먼저 용어 몇 개

- **supervisor**: 내가 직접 대화하는 메인 Claude. 팀장이다.
- **sub-agent**: supervisor가 일을 맡기는 다른 Claude들. `.claude/agents/` 안에 하나씩 정의돼 있다.
- **vault**: md 파일이 들어 있는 폴더. Obsidian으로 열면 보기 편하지만, Obsidian이 없어도 동작한다. agent들은 그냥 파일로 읽고 쓴다.
- **hook**: Claude Code가 특정 순간(세션 시작, agent 시작, 파일 쓰기 직전, 끝나기 직전)마다 자동으로 실행해 주는 스크립트. 이 플러그인의 핵심이 이거다.

## 실제로 뭘 해 주나

**agent가 일을 시작할 때** 필요한 걸 알아서 넣어 준다. 지금 목표가 뭔지, 자기 역할이 뭔지, 전에 실수해서 생긴 원칙이 뭔지, 자기 답을 기다리는 회의가 있는지. agent한테 "작업 전에 이거 읽어"라고 부탁할 필요가 없다. 그래서 까먹을 수도 없다.

**agent가 파일을 쓰려고 할 때** 검사한다. agent는 자기 폴더(작업 일지, 반성 노트)랑 회의에서 자기 발언 파일에만 쓸 수 있다. 남의 파일이나 공용 파일을 건드리려고 하면 막고, 왜 막혔는지 알려 준다. 이미 있는 파일은 못 고치고 새 파일만 만들 수 있다. 그래서 agent 여러 개가 동시에 돌아도 서로 덮어쓸 일이 없다.

**agent가 일을 끝내려고 할 때** 기록을 남겼는지 본다. 작업 일지든 회의 발언이든 하나도 안 남겼으면 "기록 남기고 끝내"라고 한 번 돌려보낸다.

**supervisor가 대답을 끝내려고 할 때** vault 목차를 새로 만든다. 목차는 사람이나 Claude가 손으로 고치는 게 아니라 스크립트가 매번 다시 만드니까 낡을 수가 없다. 그리고 이번 대화에서 vault가 바뀌었는데 사람용 상태 페이지가 그대로면 "상태 페이지 갱신해"라고 한다.

**반성은 근거가 있을 때만 남긴다.** 테스트가 깨졌거나 리뷰에서 지적받았을 때처럼 실제로 뭔가 틀렸을 때다. 반성 노트에 근거(어떤 테스트, 어떤 지적)를 안 적으면 저장 자체가 안 된다. 같은 교훈이 두 번 나오면 supervisor가 그걸 원칙으로 올리고, 그 원칙은 다음부터 그 agent가 시작할 때마다 자동으로 들어간다. 기존 원칙이랑 부딪히는 건 내 승인을 받는다. 내가 7일 동안 안 보면 자동으로 치워진다.

## 사람은 뭘 보면 되나

`vault/00_system/03_status.md` 하나만 보면 된다. 안에는 세 가지만 있다.

- 지금 어디까지 했는지
- 최근에 뭘 했는지 (원본 노트 링크 포함)
- 내가 결정해 줘야 하는 것

나머지 노트는 agent들 뇌라서 굳이 안 봐도 된다. 궁금하면 링크 타고 들어가면 된다.

## 설치

필요한 건 Claude Code랑 `python3`뿐이다. 따로 설치할 라이브러리는 없다.

쓰고 싶은 프로젝트 폴더에서 이렇게 띄운다.

```bash
cd your-project
claude --plugin-dir /path/to/smallbrains
```

## 쓰는 법

### 처음 한 번: vault 만들기

```
/smallbrain:init
```

이거 하나면 된다. 하는 일은 두 가지다.

1. 프로젝트 안에 `vault/` 폴더를 만들고, 이 프로젝트 목표가 뭔지 물어본다.
2. `.claude/agents/`에 이미 있는 agent들을 전부 vault에 등록한다. agent마다 `vault/10_agents/11_<이름>/` 같은 개인 폴더가 생긴다. **기존 agent 정의 파일은 하나도 안 건드린다.**

이미 supervisor랑 agent 여러 개로 굴러가는 팀에 설치하는 거라면 여기서 끝이다. 등록이 왜 필요하냐면, hook은 vault에 개인 폴더가 있는 agent만 SmallBrain agent로 본다. 등록 안 된 agent는 digest도 못 받고, vault에 쓰려고 하면 막힌다.

vault 위치를 바꾸고 싶으면 `SMALLBRAIN_VAULT` 환경변수에 경로를 넣으면 된다.

### 평소: 그냥 일 시키기

평소엔 `/smallbrain` 명령을 칠 일이 없다. supervisor한테 "로그인 페이지 만들어 줘"라고 하면 끝이다. 누구한테 맡길지는 supervisor가 정하고, 맥락 넣어 주기, 쓰기 검사, 기록 챙기기는 hook이 알아서 한다.

회의(`meeting`)랑 원칙 올리기(`reflect`)도 내가 안 쳐도 된다. 둘 다 skill이라서 supervisor가 필요하다고 판단하면 스스로 꺼내 쓴다. 내가 직접 시키고 싶을 때만 아래처럼 치면 된다.

```
/smallbrain:meeting 인증 방식 정하기
/smallbrain:reflect
```

- **meeting**: supervisor가 `vault/20_threads/` 아래에 회의방을 연다. agent들이 각자 발언 파일을 쓰고, supervisor는 라운드마다 합의된 것과 남은 질문을 정리한다. 최대 3라운드, 결론은 `40_knowledge/41_decisions/`에 남긴다.
- **reflect**: agent 반성 노트에서 같은 교훈이 두 번 이상 나온 걸 원칙으로 만든다. 한 번 나온 건 우연일 수 있으니까 안 올린다.

### agent끼리 직접 대화는 못 한다

Claude Code에서 sub-agent는 다른 sub-agent를 부를 수 없다. 이건 Claude Code 자체의 제약이다. 그래서 agent끼리 대화는 파일로 한다. 회의방에 각자 발언 파일을 남기고, supervisor가 다음 사람을 불러 주면 그 사람이 앞 발언들을 읽고 답한다. 직접 말을 주고받는 게 아니라 같은 노트를 돌려 쓰는 셈이다.

### agent를 새로 추가할 때

```
/smallbrain:hire builder 기능 구현 담당
```

agent 정의 파일(`.claude/agents/builder.md`)이랑 vault 개인 폴더를 한 번에 만든다. 예전에 agent는 뽑아 놓고 명단 정리를 까먹은 적이 있어서 둘을 같이 만들게 했다. agent 파일을 직접 만들었다면 `/smallbrain:init`을 한 번 더 돌려도 된다. 이미 등록된 건 건너뛰고 새로 생긴 것만 등록한다. 새 agent가 목록에 안 보이면 세션을 한 번 껐다 켜면 된다.

### 기존 vault가 있다면

예전에 쓰던 vault가 있어도 구조가 다르면 그대로 이어 쓸 수는 없다. SmallBrain은 자기 구조(아래 참고)를 기대한다. 새 vault를 따로 만들고, 필요한 노트만 옮기는 걸 추천한다.

## vault 안은 이렇게 생겼다

```
vault/
├─ 00_system/
│  ├─ 00_index.md      목차. 스크립트가 만든다. 손대지 말 것
│  ├─ 01_rules.md      vault 규칙
│  ├─ 02_now.md        agent들이 보는 현재 목표, 진행 상황
│  └─ 03_status.md     사람이 보는 상태 페이지
├─ 10_agents/11_builder/
│  ├─ profile.md       역할
│  ├─ principles/      원칙 (supervisor만 쓴다)
│  ├─ reflections/     반성 노트
│  └─ journal/         작업 일지
├─ 20_threads/2026-10-17-인증-방식/
│  ├─ index.md         안건이랑 합의 정리
│  └─ turns/           발언 하나당 파일 하나
├─ 30_projects/        산출물 문서
├─ 40_knowledge/       결정, 공통 교훈
└─ 90_archive/         치운 노트
```

번호는 기능별로 10단위다. agent별로 나누면 회의나 결정처럼 여럿이 같이 쓰는 노트를 어디 둘지 애매해져서 이렇게 했다.

## 뭔가 이상할 때

agent가 시작할 때 실제로 뭘 받는지 미리 볼 수 있다.

```bash
python3 scripts/brain.py digest builder   # builder가 받는 내용
python3 scripts/brain.py digest           # supervisor가 받는 내용
python3 scripts/brain.py index            # 목차 다시 만들기
python3 tests/test_brain.py               # 테스트
```

## 아직 부족한 점

- 파일 쓰기 검사는 Claude의 Write/Edit 도구만 본다. agent가 터미널 명령으로 파일을 쓰면 못 막는다. 실제로 그렇게 우회하는 게 보이면 그때 막을 생각이다.
- 이게 정말 효율적인지는 아직 숫자로 확인 안 했다. 예전 게임 프로젝트 기록(작업별 토큰, 걸린 시간)이랑 비교해 보는 중이다.
- 회의 라운드마다 git commit 하기, 원칙이 잘 지켜지면 자동으로 확정하기, 오래된 노트 요약해서 치우기는 아직 없다.
