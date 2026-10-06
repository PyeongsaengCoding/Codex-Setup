---
name: codegraph-context
description: 코드 위치·호출 관계·변경 영향이 불명확할 때 CodeGraph로 관련 소스를 좁힌다.
---

# 코드 구조

실제 Git 루트를 확인한다. CodeGraph 설치 위치는 codex-setup 상태의 tools.json에서 찾거나 PATH의 codegraph를 사용한다.
codegraph status로 상태를 확인한다. 최초 작업에서는 대상 Git 루트에서 codegraph init --yes, 변경분이 남았으면 codegraph sync를 실행한다. codegraph query 또는 explore로 심볼·호출자·영향을 좁히고 해당 원본 파일을 읽는다. CLI 구문은 설치 버전 --help로 확인한다.
그래프 결과가 없거나 동적 호출을 다루면 rg와 원본 추적을 함께 사용한다. 인덱스 검색 결과를 정확성이나 테스트 통과 증거로 취급하지 않는다. 무관한 저장소나 홈 전체를 색인하지 않는다.

모델·추론 선택은 적용된 공통 AGENTS가 가리키는 모델·추론 정본을 따른다. 이 스킬은 실행 모델을 변경하지 않는다.
