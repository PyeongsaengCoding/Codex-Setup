# macOS MacBook 설치 구성과 데이터 위치

아래 경로는 검증된 macOS 설치의 실제 사용자 홈이다. WSL2에서는 스킬·작업 기준을 재사용할 수 있으나 Linux 홈과 서비스 방식에 맞춰 별도로 설치·검증한다. 설정 저장소의 권장 위치는 `$HOME/Downloads/Codex-Setup`이며, 이미 다른 경로에 받은 체크아웃도 사용할 수 있다.

| 대상 | macOS 위치 | 성격 |
|---|---|---|
| Codex 설정 | `$CODEX_HOME/config.toml`, 기본 `~/.codex/config.toml` | 비공개 사용자 설정 |
| 모델 분담·식별자 | `$CODEX_HOME/working-method.md`, `$CODEX_HOME/models.json` | 설치 후 로컬에서 읽는 작업 기준 |
| 스킬 59개 | `~/.agents/skills/<스킬명>/` | 핵심·외부 스킬 모두 독립 복사본; 항목별 원본은 [전체 표](03-skills.md); 잠금 기록은 `~/Library/Application Support/codex-setup/` |
| 설치 상태·실행 기록·백업 | `~/Library/Application Support/codex-setup/` | `installation.json`, `tools.json`, `managed-backups/`, `backups/` 등; Git 밖 비공개 |
| GAM 실행 파일 | `$(uv tool dir --bin)/global-memory-mcp` | 공식 `uv tool install`이 관리 |
| GAM 프로그램 환경 | `$(uv tool dir)/global-memory-mcp/` | `uv` 기본 도구 경로, Setup이 경로를 지정하지 않음 |
| CodeGraph 실행 파일 | `~/Library/Application Support/codex-setup/tools/codegraph/node_modules/.bin/codegraph` | 독립 Node 설치 |
| GAM 기억 원본 | `~/Documents/Global Agent Memory/` | Markdown Vault |
| GAM 설정·DB·벡터 | `~/Library/Application Support/global-memory/` | 도구 관리 |
| GAM 로그 | `~/Library/Logs/global-memory/` | 도구 관리 |
| Ollama 실행 파일·모델 | `$(brew --prefix)/bin/ollama`, `~/.ollama/models/` | Ollama 관리; 실제 경로를 확인해 보고 |
| GAM 사용자 서비스 | `~/Library/LaunchAgents/com.global-memory.plist` | macOS launchd; 실행 상태 별도 확인 |
| CodeGraph 인덱스 | 각 Git 루트의 `.codegraph/` | 재생성 가능한 로컬 색인 |
| 제품 지식·계약 | 해당 제품 repo | 제품이 소유 |

Setup에는 실제 기억·DB·인증·대화·토큰·로그를 커밋하지 않는다. 설치할 Mac의 실제 홈과 Codex 홈을 탐지해 적용한다. 빈 다른 홈에 적용한 결과는 설치 완료가 아니다. CodeGraph와 GAM 실행 경로는 설치 상태의 tools.json을 사용하며 PATH 변경을 강제하지 않는다. GAM 프로그램은 `~/Library/Application Support/codex-setup/tools/`에 설치하지 않는다.

GAM 기본 검색은 키워드+의미 혼합이다. Ollama의 `nomic-embed-text` 모델이 기억과 질문의 임베딩 벡터를 생성하고, GAM은 이를 의미 검색에 사용한다. GAM 공식 설치에서 Ollama는 선택 항목이므로 Codex-Setup 설정 절차가 설정된 Ollama·모델을 별도로 설치·시작하고 실제 벡터 응답을 확인한다. GAM 업데이트 후에도 이 검사를 다시 수행한다. Ollama 모델 파일은 Ollama의 사용자 데이터 영역에 저장하며 GAM Vault나 Setup 저장소에 복사하지 않는다. Ollama가 멈추면 GAM의 키워드 검색과 기억 관리 기능은 계속 사용할 수 있지만, 그 상태를 전체 검색 완료로 보고하지 않는다. project 범위는 프로젝트별 작업에 사용한다. organization/global 레이블은 엄격한 계정 격리가 아니므로 개인·회사 계약을 공용 범위에 저장하지 않는다. 강제 보안 격리가 필요한 계정은 별도 Vault/프로세스 설계를 검증한 뒤 연결한다.

기록 보존 정책은 config/retention.json이다. 영구 기억·백업 자동 삭제는 기본 비활성이다. 임시 기억은 temporary와 expires:YYYY-MM-DD 태그를 명시한 project 활성 항목만 보관 대상으로 선정한다. 설치 로그·검사 영수증은 도구가 소유한 정해진 하위 경로만 정리한다. Codex의 내부 세션·내부 기억은 정리 대상이 아니다.
