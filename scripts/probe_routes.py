"""Run each distinct family/effort pair once; link all categories to its observed execution."""
import concurrent.futures,datetime,json,subprocess
from pathlib import Path
from setup_runtime import ROOT,routes,state_root,write_json

def probe(pair):
 model,effort=pair
 argv=['codex','exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-m',model,'-c','model_reasoning_effort='+json.dumps(effort),'--json','-']
 try:r=subprocess.run(argv,input='Reply exactly ROUTE_READY. Do not use tools.',capture_output=True,text=True,timeout=120)
 except subprocess.TimeoutExpired:return {'model_requested':model,'effort_requested':effort,'status':'timeout'}
 events=[]
 for line in r.stdout.splitlines():
  try:events.append(json.loads(line))
  except ValueError:pass
 answer=' '.join(e.get('item',{}).get('text','') for e in events if e.get('item',{}).get('type')=='agent_message')
 return {'model_requested':model,'effort_requested':effort,'exit_code':r.returncode,'reply':answer,'status':'passed' if r.returncode==0 and answer.strip()=='ROUTE_READY' else 'failed','model_backend_observed':None,'effort_backend_observed':None}
if __name__=='__main__':
 models=json.loads((ROOT/'config/models.json').read_text())['families'];pairs=sorted({(models[v['family']],v['effort']) for v in routes().values()})
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(probe,pairs))
 out={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pairs':results,'categories':{k:{'model':models[v['family']],'effort':v['effort']} for k,v in routes().items()}}
 write_json(state_root()/'receipts/routing-probe.json',out);print(json.dumps(out,indent=2));raise SystemExit(0 if all(r['status']=='passed' for r in results) else 1)
