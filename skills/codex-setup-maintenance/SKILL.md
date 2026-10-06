---
name: codex-setup-maintenance
description: Maintain this Mac's Codex configuration and shared skills when adding, changing, installing or removing user-level Codex setup components.
---

# Codex 구성 변경

관리 원본은 설치 영수증 `~/Library/Application Support/codex-setup/installation.json`의 `setup_root`가 가리키는 Codex-Setup 저장소다. 경로가 없어졌다면 사용자의 최신 체크아웃을 찾거나 공개 저장소에서 다시 받는다. 먼저 README와 05-change-management.md를 읽는다. 포맷 후 macOS MacBook의 실제 사용자 홈 구성은 10-new-machine.md, 스킬 선택은 03-skills.md, 작업·모델 기준은 11-working-method.md를 필요한 범위에서 읽는다. Setup 위치는 현재 Mac의 지속할 체크아웃을 사용하고 다른 컴퓨터에 과거 절대 경로를 강제하지 않는다. 빈 임시 홈 설치 결과를 실제 설치 완료로 보고하지 않는다. 프로젝트별 지침·계정 지도·연결·포트 배정은 설치하거나 공개 원본으로 수집하지 않는다. 모델·앱·도구 복원 범위는 13-environment-components.md다. GAM 프로그램은 공식 `uv tool install`의 기본 경로를 사용하고 Setup 상태 경로에 별도 Python 환경을 만들지 않는다. 제품별 지침·지식·전용 스킬은 제품 repo가 소유한다.

1. `scripts/audit_setup.py`로 현재 차이를 확인한다. 외부 설치물이 새로 생겼다고 자동으로 채택하거나 삭제하지 않는다.
2. 직접 관리하는 공용 지침·스킬은 원본부터 고친다. 공용 지침은 `scripts/apply_managed.py`의 계획을 확인하고 `--apply`로 적용한다. 핵심 스킬은 `scripts/install_core_skills.py`로 사용자 스킬 경로에 독립 복사본을 설치·갱신한다. 변경 전 설치물을 비공개 상태 경로에 백업하고, 사용자가 수정한 복사본은 보존한다. 설치 영수증으로 복구할 때는 이 스크립트의 `restore --backup-receipt <경로>`를 사용한다.
3. 설정 파일은 선택한 공식 지원 키만 수정한다. config 원문·인증·세션·메모리·로그·플러그인 캐시는 원본 저장소에 복사하지 않는다.
4. 파일 적용, Codex의 발견, 실제 과제 성공을 구분해 원장과 관련 문서를 갱신한다. 설치물 변경을 검토한 후에만 원장을 갱신한다.
5. 로컬 커밋과 GitHub push는 현재 사용자 요청 범위에 맞게 수행한다. 파일 감시·주기 자동화가 설치됐다고 가정하지 않는다.
