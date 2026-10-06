"""Explicit Codex dispatch with canonical category/effort. Prompts travel via stdin."""
import argparse,datetime,json,subprocess,sys
from pathlib import Path
from setup_runtime import ROOT,routes,state_root,write_json
from process_control import run_bounded

def command(category,model,repo):
 route=routes()[category]
 return ['codex','exec','--json','--approve-for-me','-C',str(repo),'-m',model,'-c','model_reasoning_effort='+json.dumps(route['effort']),'-']
def main():
 p=argparse.ArgumentParser();p.add_argument('category',choices=routes());p.add_argument('--repo',type=Path,required=True);p.add_argument('--prompt-file',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--timeout',type=int,default=1800);p.add_argument('--disposable-logs',action='store_true');p.add_argument('--state',type=Path,default=state_root());a=p.parse_args()
 mapping=json.loads((ROOT/'config/models.json').read_text());r=routes()[a.category];model=mapping['families'][r['family']];argv=command(a.category,model,a.repo)
 receipt={'category':a.category,'requested_model':model,'requested_effort':r['effort'],'observed_model':None,'observed_effort':None,'status':'prepared','argv':argv}
 if a.execute:
  folder=a.state/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f');folder.mkdir(parents=True,mode=0o700)
  # Keep task content and events private. Observed backend model is unknown if the host does not expose it.
  if a.timeout<1:raise ValueError('timeout must be positive')
  receipt.update(status='running',disposable_logs=a.disposable_logs)
  write_json(folder/'receipt.json',receipt)
  code=130
  try:
   with (folder/'events.jsonl').open('w') as out,(folder/'stderr.log').open('w') as err:
    code=run_bounded(argv,input_text=a.prompt_file.read_text(),stdout=out,stderr=err,timeout=a.timeout)
  finally:
   receipt.update(exit_code=code,status='execution_failed' if code else 'executed_not_verified')
   write_json(folder/'receipt.json',receipt)
  for line in (folder/'events.jsonl').read_text().splitlines():
   try:e=json.loads(line)
   except ValueError:continue
   if e.get('type')=='thread.started':receipt['thread_id']=e.get('thread_id')
  write_json(folder/'receipt.json',receipt);print(json.dumps(receipt,indent=2));sys.exit(code)
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
