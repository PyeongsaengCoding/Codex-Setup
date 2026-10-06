"""Run with the installed GAM Python. All writes target a disposable vault/repository."""
import argparse,asyncio,json,os,subprocess,tempfile,uuid
from pathlib import Path
from contextlib import asynccontextmanager
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from setup_runtime import state_root,write_json
def require(condition,message):
 if not condition:raise RuntimeError(message)

@asynccontextmanager
async def connect(command,args,env=None):
 async with stdio_client(StdioServerParameters(command=command,args=args,env=env)) as (r,w):
  async with ClientSession(r,w) as session:
   await session.initialize();yield session
async def call(session,name,args):
 r=await session.call_tool(name,args)
 data=r.structuredContent
 if data is None:
  data=json.loads(next(c.text for c in r.content if hasattr(c,'text')))
 if r.isError or (isinstance(data,dict) and data.get('ok') is False):raise RuntimeError(name+': '+str(data))
 return data
async def probe(tools):
 results={}
 with tempfile.TemporaryDirectory(prefix='codex-tools-') as d:
  root=Path(d);vault=root/'vault';state=root/'state';config=root/'gam.toml'
  config.write_text('vault_path = '+json.dumps(str(vault))+'\n[embeddings]\nenabled = false\n[search]\ndefault_mode = "keyword"\n')
  # Direct stdio initializes services with isolated state; no daemon or real memory is used.
  args=['--direct','--config',str(config),'--state',str(state),'--token-file',str(root/'unused-token')]
  async with connect(tools['gam_mcp'],args) as s:
   available={x.name for x in (await s.list_tools()).tools};require('memory_remember' in available, "Probe requirement failed: 'memory_remember' in available")
   for project in ('setup-personal','setup-company'):
    await call(s,'memory_projects',{'action':'add','request_id':str(uuid.uuid4()),'payload':{'name':project,'roots':[str(root/project)]}})
   candidate=await call(s,'memory_remember',{'request_id':str(uuid.uuid4()),'title':'Setup probe unique','content':'ZEBRA_SETUP_761 is the fixture decision.','type':'fact','scope':'project','project':'setup-personal','force':True})
   results['gam_candidate_response']=candidate
   # Derive the actual id from structured data; never assume an upstream response shape.
   def find_id(x):
    if isinstance(x,dict):
     if isinstance(x.get('id'),str) and x['id'].startswith('mem_'):return x['id']
     for v in x.values():
      got=find_id(v)
      if got:return got
    if isinstance(x,list):
     for v in x:
      got=find_id(v)
      if got:return got
   ident=find_id(candidate);require(ident, 'Probe requirement failed: ident')
   before=await call(s,'memory_search',{'query':'ZEBRA_SETUP_761','project':'setup-personal'})
   require(ident not in json.dumps(before), 'Candidate leaked into active search')
   await call(s,'memory_approve',{'id':ident,'request_id':str(uuid.uuid4())})
   found=await call(s,'memory_search',{'query':'ZEBRA_SETUP_761','project':'setup-personal'})
   require(ident in json.dumps(found), 'Approved memory not found')
   other=await call(s,'memory_search',{'query':'ZEBRA_SETUP_761','project':'setup-company'})
   require(ident not in json.dumps(other), 'Project memory leaked')
   await call(s,'memory_archive',{'id':ident,'reason':'fixture cleanup','request_id':str(uuid.uuid4()),'hard_delete':False})
   archived=await call(s,'memory_search',{'query':'ZEBRA_SETUP_761','project':'setup-personal'})
   require(ident not in json.dumps(archived), 'Archived memory still active')
   results.pop('gam_candidate_response');results['gam']={'mcp':True,'candidate_hidden':True,'approved_recalled':True,'project_scope':True,'archive_hidden':True}
   temporary=await call(s,'memory_remember',{'request_id':str(uuid.uuid4()),'title':'Expired temp','content':'Temporary fixture note','type':'fact','scope':'project','project':'setup-personal','tags':['temporary','expires:2020-01-01'],'force':True})
   temp_id=find_id(temporary);require(temp_id, 'Probe requirement failed: temp_id')
   await call(s,'memory_approve',{'id':temp_id,'request_id':str(uuid.uuid4())})
  maintenance_state=root/'maintenance';write_json(maintenance_state/'tools.json',tools)
  from maintain import maintain
  cleanup=await maintain(maintenance_state,vault,True,config,state)
  require(cleanup['archived']==1, cleanup)
  results['maintenance_expired_archive']=True
  repo=root/'repo';repo.mkdir();subprocess.run(['git','init','-q',str(repo)],check=True)
  (repo/'cart.py').write_text('def checkout(value):\n    return value + 1\n\ndef caller():\n    return checkout(2)\n')
  env=dict(os.environ,CODEGRAPH_NO_DAEMON='1',CODEGRAPH_NO_WATCH='1')
  def cg(*args):return subprocess.run([tools['codegraph'],*args],cwd=repo,env=env,capture_output=True,text=True,check=True).stdout
  cg('init','--yes');q=cg('query','checkout');require('checkout' in q, "Probe requirement failed: 'checkout' in q")
  (repo/'cart.py').write_text('def replacement_symbol(value):\n    return value\n');cg('sync');q=cg('query','replacement_symbol');require('replacement_symbol' in q, "Probe requirement failed: 'replacement_symbol' in q")
  (repo/'cart.py').unlink();cg('sync');q=cg('query','replacement_symbol');require('cart.py' not in q, "Probe requirement failed: 'cart.py' not in q")
  async with connect(tools['codegraph'],['serve','--mcp','--path',str(repo),'--no-watch'],env) as s:
   defs=(await s.list_tools()).tools;names=[x.name for x in defs];require(names, 'Probe requirement failed: names')
   target=next((x for x in defs if x.name=='codegraph_explore'),defs[0])
   props=target.inputSchema.get('properties',{})
   args={'query':'status'} if 'query' in props else {}
   if 'projectPath' in props:args['projectPath']=str(repo)
   reply=await s.call_tool(target.name,args);require(not reply.isError, str(reply))
   results['codegraph_mcp_called']=target.name
  results['codegraph']={'created_searched':True,'modified_searched':True,'deleted_removed':True,'mcp_tool_count':len(names)}
 return results
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,default=state_root());a=p.parse_args()
 result=asyncio.run(probe(json.loads((a.state/'tools.json').read_text())));write_json(a.state/'receipts/tools-probe.json',result);print(json.dumps(result,indent=2))
