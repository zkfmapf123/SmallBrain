# SmallBrain

[English](README.md)

Claude Code에서 팀장 하나와 agent 여러 개로 일하는 프로젝트에 설치하는 플러그인이다. 설치하면 agent들이 Obsidian vault(md 파일 폴더)를 공용 뇌로 쓴다. 할 일을 기억하고, 서로 결과를 넘기고, 실수에서 배운 걸 다음 작업에 가져간다.

## 왜 만들었나

예전에 Claude Code로 agent 팀을 꾸려서 게임을 만들었다. 내가 대화하는 메인 Claude가 팀장이고, 기획, 개발, QA agent들한테 일을 나눠 줬다. 기록은 전부 Obsidian vault에 남기라고 규칙을 적어 뒀다.

며칠 지나니까 규칙이 안 지켜졌다.

- 팀장이 "너 이거 고쳐라"를 vault에 적어 놔도, 그 agent는 그 노트를 안 읽었다. 같은 실수를 또 했다.
- 목차 노트가 낡았다. 이미 폐기한 게임이 아직 "기준 게임"으로 남아 있었다.
- 매일 남기라던 로그가 첫날 이후로 없었다.

규칙이 글로만 있어서 그랬다. Claude가 까먹으면 끝이다.

그래서 SmallBrain은 규칙을 글 대신 장치로 만들었다. agent가 기억하지 않아도 Claude Code가 알아서 읽혀 주고, 기록하고, 막는다.

## 용어

- **팀장**: agent들에게 일을 나눠 주는 쪽. 내가 대화하는 메인 Claude(메인 세션)일 수도 있고, 다른 agent를 부르는 agent일 수도 있다.
- **agent**: 팀장이 일을 맡기는 다른 Claude. `.claude/agents/`에 파일 하나씩으로 정의한다.
- **vault**: md 파일이 들어 있는 폴더. Obsidian으로 열면 보기 편하지만 Obsidian이 없어도 동작한다.
- **hook**: 특정 순간(세션 시작, agent 시작, 파일 쓰기 직전, agent 끝남, 대답 끝나기 직전)에 Claude Code가 자동으로 실행하는 스크립트. SmallBrain은 대부분 hook으로 동작한다.

## 두 가지 팀 구조를 다 지원한다

```
구조 A: 메인 세션이 팀장          구조 B: 팀장도 agent
메인 세션 (팀장)                  메인 세션 (전달)
  ├ builder                        └ supervisor agent (팀장)
  └ reviewer                           ├ researcher
                                       ├ proponent
                                       └ critic
```

둘 다 흔한 구조다. SmallBrain은 어느 쪽인지 알아서 판단하고 그에 맞게 동작한다. 판단 기준은 간단하다. **다른 agent를 부르는 agent가 팀장**이다. 메인 세션은 어느 구조든 팀장 권한을 가진다.

## 설치

필요한 건 Claude Code와 `python3`뿐이다.

**정식 설치 (추천: project scope)**

SmallBrain을 쓸 프로젝트 폴더에서 실행한다.

```bash
claude plugin install smallbrain --marketplace zkfmapf123/SmallBrain --scope project
```

`--scope project`로 설치하면 그 프로젝트에서만 켜진다. 설정이 `.claude/settings.json`에 들어가서 git으로 팀과 같이 쓸 수 있다. `--scope user`로 설치하면 모든 프로젝트에서 켜지는데, vault가 없는 프로젝트에서도 세션을 시작할 때마다 "vault가 없다"는 안내가 한 줄 붙는다.

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

init이 하는 일은 프로젝트 상태에 따라 다르다.

**agent가 하나도 없으면**, 구조 A로 팀을 만들어 준다. 프로젝트 목표를 묻고, 목표에 맞는 일꾼 agent 2~3개를 제안하고, 동의하면 `.claude/agents/`에 만든다. 팀장은 메인 세션이 맡는다.

**agent가 이미 있으면**, 그 구조를 읽는다. agent 정의 파일의 `tools`에 `Agent`가 있으면 그 agent를 팀장으로, 나머지는 일꾼으로 등록한다. agent 정의 파일은 하나도 고치지 않는다. `tools`를 안 적은 agent는 일꾼으로 시작하고, 실제로 다른 agent를 부르는 순간 hook이 팀장으로 바꿔 준다. 역할을 직접 정하고 싶으면 `python3 scripts/brain.py role <이름> supervisor` 또는 `worker`.

그리고 두 경우 모두 이걸 한다.

- 프로젝트 안에 `vault/` 폴더를 만든다.
- `CLAUDE.md` 끝에 SmallBrain 안내 블록을 한 번 붙인다. "채팅 출력만 해라" 같은 기존 규칙이 vault 기록까지 막지 않게, 그런 규칙은 결과물 파일 이야기라고 적어 둔다. 기존 `CLAUDE.md`에 겹칠 수 있는 줄이 있으면 init이 보여 준다.

**init이 agent 파일을 새로 만들었으면 세션을 한 번 껐다 켜야 한다.** Claude Code는 agent 정의를 세션 시작 때만 읽기 때문이다. vault 위치를 바꾸고 싶으면 `SMALLBRAIN_VAULT` 환경변수에 경로를 넣는다.

## 평소에 쓰는 법

따로 명령을 칠 필요가 없다. 평소처럼 "로그인 페이지 만들어 줘"라고 하면 된다. 그 뒤로는 이렇게 흘러간다.

1. 팀장이 일을 나눠서 agent에게 맡긴다.
2. **agent가 시작할 때**, hook이 그 agent에게 필요한 걸 넣어 준다. 지금 목표, 자기 역할, 전에 실수해서 생긴 원칙, 자기 답을 기다리는 회의, 지금 시각. 같은 agent가 background에서 다시 깨어날 때는 다시 넣지 않는다.
3. **agent가 파일을 쓸 때**, hook이 검사한다. 일꾼은 자기 반성 노트와 회의 발언 파일만 새로 만들 수 있다. 공용 파일을 건드리면 막히고 이유를 안내받는다. Bash로 vault에 쓰는 것도 막는다. 팀장은 vault 어디든 쓸 수 있다.
4. **agent가 일을 끝내면**, hook이 그 agent의 최종 보고를 `journal/`에 자동으로 저장한다. agent가 따로 기록할 필요가 없고, 쓰기 도구가 없는 agent의 보고도 남는다.
5. **메인 세션이 대답을 끝낼 때**, hook이 vault 목차를 새로 만든다. 이번에 vault가 바뀌었는데 사람용 상태 페이지가 그대로면, 상태 페이지 갱신을 한 번 요청한다. 결정이 나왔으면 결정 노트도 남기라고 같이 알려 준다.

## agent를 추가할 때

평소처럼 `.claude/agents/`에 agent 파일을 만들면 된다. 직접 써도 되고 `/agents` 명령으로 만들어도 된다. SmallBrain 등록은 그 agent가 처음 일을 받을 때 자동으로 된다. 새 파일은 세션을 다시 시작해야 Claude Code가 인식한다.

Explore, Plan 같은 Claude Code 기본 agent는 등록하지 않는다. 이 agent들은 vault에 쓰려고 하면 막힌다. 결과는 팀장에게 돌려주고, 기록은 팀장이 한다.

## 회의

같은 주제로 agent 2명 이상의 의견을 모으면 회의이고, 회의는 반드시 스레드를 만든다. 내가 "논의해 줘", "토론해 줘", "회의해 줘", "의견 모아 줘"처럼 요청하면 hook이 이걸 논의 요청으로 보고 팀장에게 회의 스레드로 진행하라고 알려 준다. 끝났는데 스레드가 없으면 한 번 더 요청한다. 직접 열고 싶으면 이렇게 친다.

```
/smallbrain:meeting 인증 방식 정하기
```

1. 팀장이 `vault/20_threads/` 아래에 회의 노트를 만든다.
2. 팀장이 참석 agent를 부른다. 각 agent는 지금까지의 발언을 읽고 자기 의견을 낸다. 의견은 hook이 그 agent의 journal에 자동으로 저장한다.
3. 라운드가 끝날 때마다 팀장이 합의된 것과 남은 질문을 정리하고, 각 발언을 링크로 단다.
4. 최대 3라운드. 결론은 `40_knowledge/41_decisions/`에 결정 노트로 남긴다.

팀장이 agent인 구조 B에서는 그 팀장 agent가 회의를 진행한다. 회의 절차는 팀장 agent가 시작할 때 hook이 같이 넣어 준다.

## 반성과 원칙

- 실제로 뭔가 틀렸을 때(테스트 실패, 리뷰 지적, 내가 정정했을 때) 반성을 남긴다. 근거(어떤 테스트, 어떤 지적)가 없는 반성은 저장되지 않는다.
- 쓰기 도구가 있는 agent는 자기 `reflections/`에 직접 쓴다. 없는 agent는 보고 끝에 `반성:`을 적고, 팀장이 반성 노트로 옮긴다.
- 같은 교훈이 두 번 나오면 팀장이 원칙으로 올린다. 한 번은 우연일 수 있어서 안 올린다. 직접 시키고 싶으면 `/smallbrain:reflect`.
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
│  ├─ 02_now.md        팀이 보는 현재 목표, 진행 상황
│  └─ 03_status.md     사람이 보는 상태 페이지
├─ 10_agents/11_builder/
│  ├─ profile.md       역할 (role: supervisor 또는 worker)
│  ├─ principles/      원칙 (팀장만 쓴다)
│  ├─ reflections/     반성 노트
│  └─ journal/         작업 보고 (hook이 자동 저장)
├─ 20_threads/2026-10-17-인증-방식/
│  ├─ index.md         안건과 합의 정리
│  └─ turns/           직접 남긴 발언
├─ 30_projects/        산출물 문서
├─ 40_knowledge/       결정, 공통 교훈
└─ 90_archive/         치운 노트
```

폴더 번호는 기능별로 10단위다. agent별로 나누면 회의나 결정처럼 여럿이 같이 쓰는 노트를 둘 곳이 애매해서 이렇게 나눴다.

## 문제가 있을 때

agent가 시작할 때 실제로 받는 내용을 볼 수 있다.

```bash
python3 scripts/brain.py digest builder   # builder가 받는 내용
python3 scripts/brain.py digest           # 메인 세션이 받는 내용
python3 scripts/brain.py index            # 목차 다시 만들기
python3 tests/test_brain.py               # 테스트
```
