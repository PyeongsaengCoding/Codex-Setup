# macOS MacBook 설치 기준

이 문서는 검증된 macOS 설치의 완료 기준이다. WSL2는 [README](README.md)의 안내처럼 AI가 스킬·작업 기준을 재사용할 수 있으나 Linux에 맞는 설치·검증이 필요하다. macOS에서는 사용자가 README의 요청문만 보낸다. 이 문서는 설정을 맡은 AI의 **완료 조건**이며 고정 명령 순서가 아니다. AI는 대상 MacBook·계정·앱에서 가능한 방법을 선택하고, 필요한 준비·검사·오류 수정을 수행한다.

## 버전 선택

- Codex 앱에서 실제 사용할 수 있는 Sol·Astra·Luna 최신 모델을 확인한다. [모델 분류와 추론 수준](11-working-method.md#모델-역할)은 유지하고, 사용할 수 없는 조합을 임의 대체하지 않는다.
- AI가 [Homebrew 공식 안내](https://brew.sh/)를 확인해 Homebrew가 없으면 설치한다. 이어서 Python·uv·CodeGraph 호환 Node LTS·Ollama의 최신 안정판을 Homebrew로 준비하고 실행 경로를 확인한다. Homebrew 설치에 필요한 macOS 관리자 인증은 실제 사용자 절차로 처리한다. 도구가 이미 있다면 최신 안정판·호환성을 대조해 갱신한다.
- GAM·CodeGraph의 공식 최신 안정 릴리스와 설치 방식을 확인한다. GAM은 공식 안내의 `uv tool install`과 `uv` 기본 도구 경로를 사용한다. 59개 스킬도 각각 최신 안정 릴리스 또는 최신 검토된 upstream 커밋을 확인한다. 출시 버전이 없는 스킬은 변경 내용·라이선스·호환성을 검토한다. upstream에서 없어진 스킬은 옛 버전을 최신이라고 표시하지 않고 대체 경로 또는 보존 사유를 기록한다.
- `inventories/tools.lock.json`, CodeGraph 의존성 잠금 파일, `config/models.json`은 **마지막으로 검증한 기준**이다. 더 새롭고 호환되는 버전이 있으면 잠금 파일을 갱신해 격리 설치와 관련 회귀·실제 도구 검사를 통과시킨 뒤 적용한다. 새 버전이 실패하면 검증된 기준으로 복귀하고 선택 이유를 보고한다. 버전 번호만 보고 설치 성공으로 간주하지 않는다.
- `scripts/setup_runtime.py apply`는 검증해 기록한 버전을 사용한다. 더 새롭고 호환되는 버전을 선택했다면 **적용 전에** 도구 잠금 파일과 의존성 명세를 갱신한다. 필요한 Homebrew·Python·uv·Node는 AI가 먼저 준비하므로 누락 오류를 사용자 작업으로 넘기지 않는다. GAM 업데이트만으로 Ollama가 설치·업데이트되지는 않는다. 설정 절차가 Ollama 서비스·모델과 임베딩 응답을 별도로 확인한다. 주기적인 무검증 자동 업그레이드는 설정하지 않는다.
- 외부 스킬을 이미 설치한 계정에서는 최신 upstream을 검토한 뒤 `scripts/install_external_skills.py --all --apply --refresh`로 대조한다. README의 설치 요청문처럼 기존 스킬까지 최신화를 요청받았다면 `--replace-existing`을 추가해 대상 폴더 전체를 각각 백업하고 최신 원본으로 교체한다. 새 파일·출처 기록·백업 영수증을 확인하고, 실패한 항목은 복구 후 미완료로 보고한다.

## 완료 조건

| 영역 | 확인할 결과 |
|---|---|
| 로컬 접근 | ChatGPT 앱의 현재 작업이 대상 컴퓨터의 파일·명령에 접근한다. 불가능하면 설정을 진행할 수 있는 로컬 작업 경로를 찾고 필요한 사용자 조치만 알린다. |
| 사용자 홈 적용 | 저장소를 `$HOME/Downloads/Codex-Setup`에 받거나 이미 받은 체크아웃을 확인해 사용하고, 로그인한 사용자의 실제 홈과 `$CODEX_HOME`에 적용한다. 다른 `--home`이나 빈 경로의 성공을 완료로 계산하지 않는다. 사용자 설정·인증·기억·무관한 파일을 보존하고 변경 전 백업·복구 경로를 만든다. Hermes·OMH 실행 환경·Graft를 설치하지 않는다. |
| Codex 설정 자유도 | 사용자 `config.toml`의 모델·추론·개인 설정을 보존하고 GAM·CodeGraph 연결 블록만 갱신한다. 사용자가 수정한 전역 `AGENTS.md`는 보존한다. 핵심 스킬은 사용자 홈의 독립 복사본으로 설치하고 모델 분담 문서는 `$CODEX_HOME/working-method.md`, 실제 모델 식별자는 `$CODEX_HOME/models.json`에 둔다. |
| 도구 | GAM은 공식 `uv tool install`로 `uv` 기본 경로에 설치하고, Vault·로컬 Ollama·임베딩 모델·GAM 백그라운드 서비스와 CodeGraph를 준비해 Codex MCP에 연결한다. 실제 사용자 홈의 GAM·Codex 연결 상태와 의미 검색을 확인하고, 작업할 실제 Git 저장소에서 CodeGraph 색인·변경 반영·직접 호출을 검사한다. 기존 기억의 내용은 승인 없이 시험용으로 수정하지 않는다. Ollama가 없으면 설치하고 서비스가 멈췄으면 시작하며 설정된 모델이 없으면 내려받는다. 실제 임베딩 벡터가 반환되지 않거나 의미 검색에 실패하면 GAM 전체 완료로 보고하지 않는다. 작업할 제품 저장소만 필요할 때 색인한다. |
| 스킬 | [전체 목록](03-skills.md)의 59개 스킬을 모두 설치하고 관련 작업에서만 선택한다. [스킬별 과제](inventories/coding-skills.json)로 핵심 스킬의 발견·본문 읽기·선택·행동을 확인하고 업무 스킬의 앱 발견과 대표 사용 조건도 확인한다. 설치 파일의 존재나 CLI 표본만으로 앱의 성공을 판정하지 않는다. |
| 모델·팀장 | [12개 분류](11-working-method.md#모델-역할)에 따라 주 에이전트가 담당·파일 소유권·모델·추론을 실제 배정한다. 가능한 모델·추론 조합의 결과를 회수하고, 격리 코딩 과제에서 구현·독립 리뷰·통합 검사를 확인한다. 요청한 값과 백엔드 관측값을 구분한다. |
| 복구·정리 | 실제 사용자 홈에서 반복 적용에 중복·설정 훼손이 없고 설치 백업의 복구 경로가 유효하다. 만료 임시 기억의 정리와 중요 기억의 보존을 확인한다. 정기 실행은 앱에서 실제 제공되는 기능으로 연결하고 예약 실행의 관측 범위를 보고한다. |
| 앱 재확인 | 새 로컬 코딩 작업에서 스킬과 GAM·CodeGraph 직접 도구가 보이고 실제 응답하는지 확인한다. GAM `memory_status`의 `transport=streamable-http`, `embedding_state=configured`, `keyword_only=false`를 확인한다. 앱 재시작·로그인·macOS 권한이 필요하면 그 단계에서 이어간다. |

## 설치 결과 보고

AI는 사용한 설정 저장소 체크아웃, `$CODEX_HOME`, 스킬 59개, `uv tool dir`과 `uv tool dir --bin`의 실제 GAM 경로, CodeGraph 실행 파일, GAM Vault·설정·로그, Ollama 모델, 사용한 CodeGraph 색인의 **실제 절대 경로**를 보고한다. 각 항목은 설치, 앱 발견, 실제 동작을 구분한다. 경로 기준은 [13-environment-components.md](13-environment-components.md)다.

## 제공 도구

`scripts/setup_runtime.py`는 검증한 버전의 계획·적용·상태·복구를, `scripts/probe_tools.py`는 임시 자료로 MCP 동작을, `scripts/probe_gam_semantic.py`는 독립 임시 Vault에서 의미 검색을, `scripts/evaluate_skills.py`는 선택형 보조 평가를 제공한다. GAM 의미 검색에는 Ollama의 로컬 서비스·`nomic-embed-text` 모델과 GAM의 백그라운드 임베딩 서비스가 필요하다. Codex MCP는 준비된 GAM 서비스에 연결하고 서비스가 없을 때 직접 실행으로 전환한다. 이 검사 도구가 시험 자료를 만들더라도 대상 컴퓨터의 실제 적용·앱 검증을 대체하지 않는다. AI는 필요한 도구를 선택해 사용할 수 있다. 설치·검증의 실제 결과는 [15-local-task-readiness.md](15-local-task-readiness.md) 기준으로 완료와 미확인을 구분해 보고한다. 새 컴퓨터의 앱 검증을 앞선 컴퓨터의 기록으로 대체하지 않는다.
