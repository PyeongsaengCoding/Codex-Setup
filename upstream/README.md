# 차용 출처

[OMH 원본 저장소](https://github.com/rlaope/oh-my-hermes)와 [고정 커밋의 모델 라우팅 표](https://github.com/rlaope/oh-my-hermes/blob/c8b94d0431db3b49d5df040acd7f29a241065ff0/README.md#recommended-models)를 참조한다. 12개 분류·추론을 Codex 모델에 매핑하고 작업 원칙·핵심 절차를 Codex용으로 재작성했다. 원본 스킬 그대로의 실행 호환성을 주장하지 않는다. 원본 커밋과 파일 해시는 inventories/coding-skills.json 및 tools.lock.json에 있다. OMH MIT 라이선스는 /upstream-LICENSE-OMH에 보존한다.

Codex가 직접 작업하며 Hermes 도구, OMH CLI, ~/.omh, ~/.hermes 의존성은 없다. 원본의 준비/실행/검증 구분, 파일 소유권, 요구사항 대조를 보존했다. 강제 반복 승인, 원문 프롬프트 출력, 특정 호스트 상태 명령은 이식하지 않았다.

선별한 tdd·diagnosing-bugs·writing-for-agents는 mattpocock/skills, ponytail은 DietrichGebert/ponytail에서 도입한 사용자 승인 조정본이다. 내용과 출처 잠금은 skill-files.lock.json에서 확인한다. 소스 업데이트는 고정 버전 diff 검토→행동 평가→적용 순서로 수행한다. 새 원본이 나왔다는 이유만으로 덮어쓰지 않는다.
