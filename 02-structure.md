# 구성 구조

| 영역 | 원본 | 적용·데이터 |
|---|---|---|
| 사용자 지침 | instructions/AGENTS.md | Codex 홈 AGENTS.md |
| 코딩 스킬 | skills/ | 사용자 .agents/skills |
| 모델 규칙 | 11-working-method.md | `$CODEX_HOME/working-method.md`에서 앱 작업에 적용 |
| 모델 식별자 | config/models.json | `$CODEX_HOME/models.json`에서 앱 위임 인자로 사용 |
| 도구 버전·의존성 | inventories/*lock* | 비공개 codex-setup/tools |
| 기억 | 정책·연결 방법만 Setup에 저장 | GAM 독립 Vault와 OS 데이터 경로 |
| 코드 인덱스 | 초기화·사용 절차 | 각 repo .codegraph |
| 검증 기준·실행 결과 | 12에 기준만 게시 | 실행 기록은 Git 밖 비공개 상태 경로 |

세부 경로는 13-environment-components.md가 정본이다. Git 밖 부모 지침의 자동 상속을 가정하지 않는다.
프로젝트별 지침·계정·포트·연결 설정은 각 프로젝트 또는 사용자 환경에서 별도로 관리한다.
