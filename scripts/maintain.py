"""Bounded retention: own logs only; explicitly expired temporary GAM notes are archived."""
import argparse,asyncio,datetime,json,os,sys
from pathlib import Path
from setup_runtime import ROOT,state_root,write_json

def expired_memory(meta,now,policy):
 tags=set(meta.get('tags',[]))
 if meta.get('scope')!='project' or meta.get('status')!='active' or 'temporary' not in tags:return False
 if tags.intersection(policy['protect_tags']) or meta.get('type') in ('decision','preference','convention') or float(meta.get('importance',1))>=0.8:return False
 dates=[]
 for tag in tags:
  if tag.startswith('expires:'):
   try:dates.append(datetime.date.fromisoformat(tag[8:]))
   except ValueError:return False
 return len(dates)==1 and dates[0]<now.date()

def log_candidates(state,now,policy):
 state=Path(state).resolve();out=[]
 for sub,days in [('logs',policy['owned_log_days']),('receipts',policy['receipt_days'])]:
  base=state/sub
  if base.is_symlink():continue
  for p in base.glob('*'):
   if p.is_symlink() or not p.is_file():continue
   if p.suffix not in ('.json','.jsonl','.log'):continue
   if (now.timestamp()-p.stat().st_mtime)>days*86400:out.append(p)
 # Completed, reviewed evaluations own these raw logs. Keep pending/failed cases intact.
 evaluations=state/'evaluations'
 if evaluations.is_dir() and not evaluations.is_symlink():
  for run in evaluations.iterdir():
   if run.is_symlink() or not run.is_dir() or (run/'.keep').exists():continue
   for case in run.iterdir():
    if case.is_symlink() or not case.is_dir() or (case/'.keep').exists():continue
    receipt=case/'receipt.json'
    if not receipt.is_file() or receipt.is_symlink():continue
    try:record=json.loads(receipt.read_text())
    except (ValueError,OSError):continue
    if record.get('semantic_verdict')!='passed' or record.get('execution_status')!='executed':continue
    for name in ('events.jsonl','stderr.log','prompt.txt'):
     path=case/name
     if path.is_file() and not path.is_symlink() and now.timestamp()-path.stat().st_mtime>policy['owned_log_days']*86400:out.append(path)
 runs=state/'runs'
 if runs.is_dir() and not runs.is_symlink():
  for run in runs.iterdir():
   if run.is_symlink() or not run.is_dir() or (run/'.keep').exists():continue
   receipt=run/'receipt.json'
   if not receipt.is_file() or receipt.is_symlink():continue
   try:record=json.loads(receipt.read_text())
   except (ValueError,OSError):continue
   if record.get('status')!='executed_not_verified' or record.get('exit_code')!=0 or record.get('disposable_logs') is not True:continue
   for name in ('events.jsonl','stderr.log'):
    path=run/name
    if path.is_file() and not path.is_symlink() and now.timestamp()-path.stat().st_mtime>policy['owned_log_days']*86400:out.append(path)
 return out
async def maintain(state,vault,apply=False,config=None,gam_state=None):
 import yaml
 from probe_tools import connect,call
 policy=json.loads((ROOT/'config/retention.json').read_text());now=datetime.datetime.now(datetime.timezone.utc)
 state=Path(state);vault=Path(vault).resolve();tools=json.loads((state/'tools.json').read_text());candidates=[]
 from global_memory.config import load_settings,get_platform_paths
 config=Path(config) if config else get_platform_paths().config_file
 if load_settings(config).vault_path.resolve()!=vault:raise RuntimeError('Requested vault does not match GAM configuration')
 args=['--direct','--token-file',str(get_platform_paths().auth_token),'--config',str(config)]
 if gam_state:args += ['--state',str(gam_state)]
 for path in vault.rglob('*.md'):
  if path.is_symlink() or not path.resolve().is_relative_to(vault):continue
  text=path.read_text()
  if not text.startswith('---\n'):continue
  try:meta=yaml.safe_load(text.split('---',2)[1])
  except (yaml.YAMLError,IndexError):continue
  if isinstance(meta,dict) and expired_memory(meta,now,policy):candidates.append((meta['id'],meta.get('updated_at')))
 logs=log_candidates(state,now,policy);result={'apply':apply,'memory_archive_candidates':len(candidates),'log_candidates':len(logs),'archived':0,'logs_deleted':0}
 if apply:
  async with connect(tools['gam_mcp'],args) as s:
   for ident,version in candidates:
    current=await call(s,'memory_get',{'id':ident})
    def metadata(x):
     if isinstance(x,dict):
      if x.get('id')==ident and 'status' in x:return x
      for v in x.values():
       m=metadata(v)
       if m:return m
    m=metadata(current)
    if not m or not expired_memory(m,now,policy):continue
    if datetime.datetime.fromisoformat(str(m.get('updated_at')).replace('Z','+00:00'))!=datetime.datetime.fromisoformat(str(version).replace('Z','+00:00')):continue
    await call(s,'memory_archive',{'id':ident,'request_id':'setup-expiry-'+ident+'-'+now.date().isoformat(),'reason':'Explicit temporary expiry policy','hard_delete':False});result['archived']+=1
  for p in logs:
   if p in log_candidates(state,now,policy):p.unlink();result['logs_deleted']+=1
  write_json(state/'receipts/maintenance-latest.json',dict(result,at=now.isoformat()))
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,default=state_root());p.add_argument('--vault',type=Path,default=Path.home()/'Documents/Global Agent Memory');p.add_argument('--apply',action='store_true');a=p.parse_args()
 print(json.dumps(asyncio.run(maintain(a.state,a.vault,a.apply)),indent=2))
