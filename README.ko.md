# SmallBrain

[English](README.md)

Claude Code에서 supervisor 하나와 agent 여러 개로 일하는 프로젝트에 설치하는 플러그인이다. 설치하면 agent들이 Obsidian vault(md 파일 폴더)를 공용 뇌로 쓴다. 할 일을 기억하고, 서로 결과를 넘기고, 실수에서 배운 걸 다음 작업에 가져간다.

## 왜 만들었나

예전에 Claude Code로 agent 팀을 꾸려서 게임을 만들었다. 내가 대화하는 메인 Claude가 팀장이고, 기획, 개발, QA agent들한테 일을 나눠 줬다. 기록은 전부 Obsidian vault에 남기라고 규칙을 적어 뒀다.

며칠 지나니까 규칙이 안 지켜졌다.

- 팀장이 "너 이거 고쳐라"를 vault에 적어 놔도, 그 agent는 그 노트를 안 읽었다. 같은 실수를 또 했다.
- 목차 노트가 낡았다. 이미 폐기한 게임이 아직 "기준 게임"으로 남아 있었다.
- 매일 남기라던 로그가 첫날 이후로 없었다.

규칙이 글로만 있어서 그랬다. Claude가 까먹으면 끝이다.

그래서 SmallBrain은 규칙을 글 대신 장치로 만들었다. agent가 기억하지 않아도 Claude Code가 알아서 읽혀 주고, 막고, 확인한다.

## 용어

- **supervisor**: 내가 직접 대화하는 메인 Claude. 팀장이다.
- **agent**: supervisor가 일을 맡기는 다른 Claude들. `.claude/agents/`에 파일 하나씩으로 정의한다.
- **vault**: md 파일이 들어 있는 폴더. Obsidian으로 열면 보기 편하지만 Obsidian이 없어도 동작한다.
- **hook**: 특정 순간(세션 시작, agent 시작, 파일 쓰기 직전, 작업 끝나기 직전)에 Claude Code가 자동으로 실행하는 스크립트. SmallBrain은 대부분 hook으로 동작한다.

## 설치

필요한 건 Claude Code와 `python3`뿐이다.

**정식 설치 (추천: project scope)**

SmallBrain을 쓸 프로젝트 폴더에서 실행한다.

```bash
claude plugin install smallbrain --marketplace zkfmapf123/SmallBrain --scope project
```

`--scope project`로 설치하면 그 프로젝트에서만 켜진다. 설정은 `.claude/settings.json`에 들어가서 git으로 팀과 같이 쓸 수 있다. `--scope user`로 설치하면 모든 프로젝트에서 켜진다. 동작에는 문제가 없지만, vault가 없는 프로젝트에서도 세션을 시작할 때마다 "vault가 없다"는 안내가 한 줄 붙는다.

**설치 없이 한번 써 보기**

```bash
cd your-project
claude --plugin-dir /path/to/SmallBrain
```

이렇게 띄운 세션에서만 켜지고, 끄면 사라진다.

## 시작하기

설치한 프로젝트에서 한 번만 실행한다.

```
/smallbrain:init
```

1. 프로젝트 안에 `vault/` 폴더를 만들고, 프로젝트 목표를 물어본다.
2. 이미 만들어 둔 agent(`.claude/agents/`)를 전부 등록한다. agent마다 vault 안에 개인 폴더(`vault/10_agents/11_<이름>/`)가 생긴다. agent 정의 파일은 수정하지 않는다.

이게 설치 후 해야 할 전부다. vault 위치를 바꾸고 싶으면 `SMALLBRAIN_VAULT` 환경변수에 경로를 넣는다.

## 평소에 쓰는 법

따로 명령을 칠 필요가 없다. supervisor한테 평소처럼 "로그인 페이지 만들어 줘"라고 하면 된다. 그 뒤로는 이렇게 흘러간다.

1. supervisor가 일을 나눠서 agent한테 맡긴다.
2. agent가 시작할 때, hook이 그 agent한테 필요한 걸 넣어 준다. 지금 목표, 자기 역할, 전에 실수해서 생긴 원칙, 자기 답을 기다리는 회의.
3. agent가 파일을 쓸 때, hook이 검사한다. agent는 자기 개인 폴더와 회의 발언 파일에만 새 파일을 만들 수 있다. 다른 곳을 건드리면 막히고, 왜 막혔는지 안내를 받는다. 기존 파일은 못 고치고 새 파일만 만들 수 있어서, agent 여러 개가 동시에 일해도 서로 덮어쓰지 않는다.
4. agent가 일을 끝낼 때, hook이 기록을 남겼는지 본다. 작업 일지가 없으면 "기록 남기고 끝내"라고 한 번 돌려보낸다.
5. supervisor가 대답을 끝낼 때, hook이 vault 목차를 새로 만든다. 그리고 이번에 vault가 바뀌었는데 사람용 상태 페이지가 그대로면 갱신하라고 한다.

## agent를 추가할 때

평소처럼 `.claude/agents/`에 agent 파일을 만들면 된다. 직접 써도 되고 `/agents` 명령으로 만들어도 된다. SmallBrain 등록은 그 agent가 처음 일을 받을 때 자동으로 된다.

Explore, Plan 같은 Claude Code 기본 agent는 등록하지 않는다. 이 agent들은 vault에 쓰려고 하면 막힌다. 결과는 supervisor에게 돌려주고, 기록은 supervisor가 한다.

## 회의

여러 agent 의견이 필요하면 supervisor가 회의를 연다. supervisor가 알아서 판단해서 열고, 내가 직접 열고 싶으면 이렇게 친다.

```
/smallbrain:meeting 인증 방식 정하기
```

회의는 supervisor가 진행한다.

1. supervisor가 `vault/20_threads/` 아래에 회의 노트를 만든다.
2. supervisor가 참석 agent를 한 명씩 부른다. 불려 온 agent는 지금까지의 발언을 읽고, 자기 발언을 새 파일로 남긴다.
3. 라운드가 끝날 때마다 supervisor가 합의된 것과 남은 질문을 정리한다.
4. 최대 3라운드. 결론은 `40_knowledge/41_decisions/`에 결정 노트로 남긴다.

agent끼리 직접 부르는 게 아니라 supervisor를 거치는 이유는 Claude Code에서 agent를 부를 수 있는 게 supervisor뿐이기 때문이다.

## 반성과 원칙

- agent는 실제로 뭔가 틀렸을 때(테스트 실패, 리뷰 지적, 내가 정정했을 때) 반성 노트를 남긴다. 근거(어떤 테스트, 어떤 지적)가 없으면 저장되지 않는다.
- 같은 교훈이 두 번 나오면 supervisor가 원칙으로 올린다. 한 번은 우연일 수 있어서 안 올린다. 내가 직접 시키고 싶으면 `/smallbrain:reflect`를 친다.
- 원칙은 그 뒤로 그 agent가 일을 시작할 때마다 자동으로 들어간다.
- 기존 원칙과 부딪히는 원칙은 내 승인이 필요하다. 상태 페이지에 뜨고, 7일 동안 처리하지 않으면 자동으로 치워진다.

## 사람이 볼 곳

`vault/00_system/03_status.md` 하나다. 세 가지만 있다.

- 지금 어디까지 했는지
- 최근에 뭘 했는지 (원본 노트 링크 포함)
- 내가 결정해야 하는 것

나머지 노트는 agent들이 쓰는 기록이라 안 봐도 된다. 궁금하면 링크를 따라가면 된다.

## vault 구조

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
│  ├─ index.md         안건과 합의 정리
│  └─ turns/           발언 하나당 파일 하나
├─ 30_projects/        산출물 문서
├─ 40_knowledge/       결정, 공통 교훈
└─ 90_archive/         치운 노트
```

폴더 번호는 기능별로 10단위다. agent별로 나누면 회의나 결정처럼 여럿이 같이 쓰는 노트를 둘 곳이 애매해서 이렇게 나눴다.

## 문제가 있을 때

agent가 시작할 때 실제로 받는 내용을 볼 수 있다.

```bash
python3 scripts/brain.py digest builder   # builder가 받는 내용
python3 scripts/brain.py digest           # supervisor가 받는 내용
python3 scripts/brain.py index            # 목차 다시 만들기
python3 tests/test_brain.py               # 테스트
```

## 아직 부족한 점

- 파일 쓰기 검사는 Claude의 Write/Edit 도구만 본다. agent가 터미널 명령으로 파일을 쓰면 못 막는다.
- 이 방식이 실제로 더 효율적인지는 아직 숫자로 확인하지 않았다. 지금 실측하는 중이다.
- 아직 없는 기능: 회의 라운드마다 git commit, 잘 지켜진 원칙 자동 확정, 오래된 노트 요약 정리.
