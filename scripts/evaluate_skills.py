"""Execute synthetic skill evaluations; record observations without inventing semantic passes."""
import argparse,concurrent.futures,datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
from setup_runtime import ROOT,state_root,write_json
from process_control import run_bounded
import re

SCENARIOS={
'coding-plan': '공유 문서는 소유자만 초대 가능하고 viewer는 수정할 수 없다. 초대 이메일 실패를 성공으로 표시하면 안 된다. 기존 DB 구조는 아직 조사하지 않았다.',
'coding-research':'A.md: SQLite는 단일 프로세스 쓰기를 사용하는 로컬 앱 후보다. B.md: Postgres는 동시 쓰기와 원격 접근이 필요한 서버 후보다. 현재 사용자는 로컬 한 명이고 서버 배포 계획은 미정이다. 제공된 문서 범위에서만 판단한다.',
'coding-design-review':'캐시 설계: key = document_id. 사용자 A가 소유한 비공개 문서를 조회하면 본문을 전역 캐시에 저장한다. 사용자 B는 권한 검사 전에 캐시를 읽는다.',
'coding-work':'exporter.py와 importer.py가 shared.py의 포맷 함수를 서로 다른 시그니처로 바꾸려고 한다. 두 작업의 통합 결과는 왕복 변환이 같아야 한다.',
'coding-handoff':'revision abc123. cart.py 음수 수량 버그를 확인했다. test_cart.py의 negative 테스트는 실패. 아직 수정하지 않았다. 네트워크 API는 관련 없음. 결제 배포는 요청 범위 밖.',
'coding-code-review':'요구사항: 저장 실패시 성공을 반환하면 안 된다. PR 변경은 app.py이다. 현재 버전에는 save()가 예외를 잡고 ok=true로 반환하는 코드가 있다. 검토만 수행한다.',
'coding-failure-audit':'요구사항: app.py 저장 실패, 정상 빈 조회, 미확정을 구분한다. 가짜 성공 응답의 경로를 조사한다.',
'coding-ai-slop-review':'ui.txt 줄1: 내부 추론 파이프라인이 작동 중입니다. 줄2: 저장하려면 저장 버튼을 누르세요. 줄3: 저장하려면 저장 버튼을 누르세요. 줄4: 저장하지 못했습니다. 입력 내용은 보존되어 있습니다. 실제 저장 실패 때는 줄4만 표시한다.',
'coding-debt-audit':'app.py에 오류 삼킴이 있고 두 export 함수는 같은 변환을 복제한다. 관련 코드에서 현행 결함과 유지보수 문제를 구분한다.',
'coding-verification':'현재 revision NEW. 검사 기록: revision OLD, python -m unittest 통과. NEW에서 예외 처리 코드를 수정했으나 검사를 아직 실행하지 않았다. 배포 기록 없음.',
'coding-repair':'결제 POST가 타임아웃. 서버 처리 결과 미확인. idempotency key 없이 자동 재시도 제안이 있다. 로컬 수정은 남아 있고 결제 상태 API 조회는 아직 하지 않았다.',
'coding-status':'A: prepared, 실행 ID 없음. B: 실행 ID b-1, 테스트 exit 1. C: 실행 ID c-1, 로컬 테스트 exit 0, 배포/외부 계정 미확인. 토큰 정보 없음.',
'gam-memory':'현재 과제는 합성 자료의 정책 판단이다. 실제 기억을 쓰지 않는다. 회사 tenant별 결제 설정은 다른 계정에 적용할 수 없다. 왜 global 승격이 부적절한지 설명하고 대안을 제시한다.',
'coding-maintenance':'정책: 임시 로그30일, 중요 결정 자동삭제 없음. 메모 A=important 300일. B=in-progress 100일. C=temporary expires:2026-01-01. D=도구소유 log 40일. 실제 파일 삭제는 요청하지 않았다.',
'product-design-review':'사용자 요청: 주어진 HTML 로그인 화면의 표시·접근성 문제를 검토해줘. 구현은 하지 마. index.html은 label 없는 이메일 input과 텍스트 없는 button을 갖고 있다. 실제 브라우저 검수가 가능하지 않다면 그 부분은 미확인으로 구분한다.',
'codex-setup-maintenance':'이 과제는 설치 실행이 아닌 제공된 구성 변경안 검토다. 계획: 사용자 config 전체를 Git에 복사하고 원본 스킬을 건너뛰어 홈 파일만 변경한다. 부적절한 점과 올바른 원본→적용→검증 경로를 설명한다.',
'codegraph-context':'checkout의 호출자는 app.py이다. 이 fixture는 인덱스 없는 작은 repo다. 도구를 사용할 수 없으면 rg와 실제 원본으로 추적하고 CodeGraph 검증은 미확인으로 밝혀라.',
'ponytail':'표준 json 모듈이 있는 Python 프로젝트에 JSON 파일 읽기를 추가한다. 새 프레임워크나 플러그인 계층이 필요한지 판단하고 최소 구현을 제안한다.',
'writing-for-agents':'AGENTS-input.md에는 항상 적용할 계정 분리 원칙과 Azure 배포 상세50단계, 문서 오탈자 검사 순서가 한 파일에 있다. 조건부 참조로 나눌 구조를 제안한다.',
'diagnosing-bugs':'cart.py total은 sum(prices)에서 마지막 항목을 한 번 더 더한다. 테스트는 [10,20] 합계가30이어야 한다. 원인을 재현하고 수정한다.',
 'tdd':'cart.py total([])은0, total([10,20])은30이어야 한다. 음수 가격은 ValueError로 거부해야 한다. 테스트 먼저 실행해 실패 확인 후 구현한다.'}

def fixture(path):
 path.mkdir(parents=True,exist_ok=True);subprocess.run(['git','init','-q',str(path)],check=True)
 files={'app.py':'def save(storage):\n    try:\n        storage.write()\n    except Exception:\n        pass\n    return {"ok": True}\n\ndef checkout(value):\n    return value\n\ndef caller():\n    return checkout(2)\n\ndef export_a(x):\n    return str(x).strip()\n\ndef export_b(x):\n    return str(x).strip()\n', 'cart.py':'def total(prices):\n    return sum(prices) + (prices[-1] if prices else 0)\n','test_cart.py':'import unittest\nfrom cart import total\nclass Tests(unittest.TestCase):\n    def test_sum(self): self.assertEqual(total([10,20]),30)\n','index.html':'<html><body><input type="email"><button></button></body></html>','ui.txt':'내부 추론 파이프라인이 작동 중입니다.\n저장하려면 저장 버튼을 누르세요.\n저장하려면 저장 버튼을 누르세요.\n저장하지 못했습니다. 입력 내용은 보존되어 있습니다.\n','A.md':'SQLite: local single writer.','B.md':'Postgres: concurrent remote clients.','AGENTS-input.md':'계정 분리 원칙. Azure 배포 50단계. 문서 오탈자 검사 순서.'}
 for name,text in files.items():(path/name).write_text(text)
 skills=path/'.agents/skills';skills.mkdir(parents=True)
 for source in (ROOT/'skills').iterdir():
  if (source/'SKILL.md').is_file():(skills/source.name).symlink_to(source,target_is_directory=True)
 (path/'AGENTS.md').write_text('이곳은 합성 검증 저장소다. 관련 스킬을 선택하고 본문을 읽어 수행한다. 제공된 scenario.md와 실제 소스를 근거로 작업한다. 현재 과제만 수행하며 외부 계정, 실제 기억, 사용자 설정을 변경하지 않는다. 최종 답변은 한국어로 결과와 미확인 사항을 구분한다.\n')
 return files

def evaluate(item,root,negative=False):
 name=item['name'];folder=root/(name+('-negative' if negative else '-positive'));repo=folder/'repo';files=fixture(repo)
 (repo/'scenario.md').write_text(SCENARIOS.get(name,''))
 prompt=(item['negative_prompt'] if negative else item['positive_prompt'])+'\nscenario.md에 합성 자료가 있다. 최종 답변에 과제 결과와 실제 확인한 근거를 제시해줘.'
 if negative:prompt='안녕하세요라고만 답해줘. 파일이나 도구를 사용할 필요가 없어.'
 argv=['codex','exec','--ignore-user-config','--ephemeral','--json','--sandbox','workspace-write','-C',str(repo),'-m','gpt-6.1-sol','-c','model_reasoning_effort="medium"','-o',str(folder/'answer.txt'),'-']
 (folder/'prompt.txt').write_text(prompt)
 with (folder/'events.jsonl').open('w') as out,(folder/'stderr.log').open('w') as err:
  code=run_bounded(argv,input_text=prompt,stdout=out,stderr=err,timeout=240)
 tool_events=[];turn_complete=False
 for line in (folder/'events.jsonl').read_text().splitlines():
  try:event=json.loads(line)
  except ValueError:continue
  if event.get('type')=='turn.completed':turn_complete=True
  it=event.get('item',{})
  if it.get('type') in ('command_execution','mcp_tool_call','tool_call'):tool_events.append(it)
 text=json.dumps(tool_events,ensure_ascii=False)
 skill_body=(ROOT/'skills'/name/'SKILL.md').read_text().split('---',2)[-1]
 anchors=[line.strip() for line in skill_body.splitlines() if len(line.strip())>=35 and not line.startswith('#')][:2]
 observed_read=bool(anchors) and any(e.get('exit_code')==0 and (name+'/SKILL.md') in e.get('command','') and all(anchor in e.get('aggregated_output','') for anchor in anchors) for e in tool_events)
 changed=[f for f,t in files.items() if (repo/f).read_text()!=t]
 result={'name':name,'mode':'negative' if negative else 'positive','exit_code':code,'turn_completed':turn_complete,'skill_read_observed':observed_read,'tool_events':len(tool_events),'fixture_changed':changed,'answer':str(folder/'answer.txt'),'rubric':item['rubric'],'semantic_verdict':'not_reviewed'}
 if code or not turn_complete:result['execution_status']='failed'
 else:result['execution_status']='executed'
 if negative:result['non_selection_pass']=code==0 and turn_complete and not tool_events
 if name in ('coding-code-review','coding-debt-audit','coding-ai-slop-review') and changed:result['scope_violation']=True
 write_json(folder/'receipt.json',result);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--state',type=Path,default=state_root());p.add_argument('--only',nargs='*');p.add_argument('--workers',type=int,default=2);p.add_argument('--negative',action='store_true');a=p.parse_args()
 items=json.loads((ROOT/'inventories/coding-skills.json').read_text())['skills'];items=[x for x in items if not a.only or x['name'] in a.only]
 if not a.execute:print(json.dumps(items,ensure_ascii=False,indent=2));return
 root=a.state/'evaluations'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S');root.mkdir(parents=True,mode=0o700);results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(a.workers,3))) as pool:
  futs=[pool.submit(evaluate,item,root,a.negative) for item in items]
  for future in concurrent.futures.as_completed(futs):
   result=future.result();results.append(result);write_json(root/'summary.json',results);print(json.dumps(result,ensure_ascii=False),flush=True)
 print('Evidence: '+str(root));sys.exit(1 if any(x['execution_status']=='failed' for x in results) else 0)
if __name__=='__main__':main()
