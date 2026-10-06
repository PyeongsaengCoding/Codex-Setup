import sys,unittest,tempfile,json,datetime,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import setup_runtime as s
from maintain import expired_memory,log_candidates
from route_task import command

class RuntimeTests(unittest.TestCase):
 def test_config_preserves_user_keys_and_is_idempotent(self):
  src='model = "user-choice"\n[projects."/sample"]\ntrust_level = "trusted"\n'
  block=s.config_block({'codegraph':'/path with space/cg','gam_mcp':'/gam'})
  first=s.managed_config(src,block)
  self.assertEqual(s.managed_config(first,block),first)
  self.assertIn('model = "user-choice"',first)
  self.assertNotIn('--direct',block)
  self.assertIn('default_mode = "hybrid"',s.gam_profile(Path.home()))
 def test_unmanaged_mcp_conflict_is_refused(self):
  with self.assertRaises(RuntimeError):s.managed_config('[mcp_servers.codegraph]\ncommand="mine"','')
 def test_restore_preserves_later_user_edits(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config';p.write_text('before');backup=s.backup_write(p,b'after',Path(d)/'state')
   p.write_text('user change')
   with self.assertRaises(RuntimeError):s.restore(backup)
   self.assertEqual(p.read_text(),'user change')
   p.write_text('after');s.restore(backup);self.assertEqual(p.read_text(),'before')
 def test_routes_all_exact_effort(self):
  expected={'ultrabrain':'xhigh','architect':'xhigh','deep':'high','visual-engineering':'high','artistry':'high','deep-work':'high','writing':'medium','capable':'medium','unspecified-high':'medium','quick':'low','simple-work':'low','unspecified-low':'low'}
  self.assertEqual({k:v['effort'] for k,v in s.routes().items()},expected)
  for k,e in expected.items():self.assertIn('model_reasoning_effort='+json.dumps(e),command(k,'test-model','/repo'))
 def test_expiry_protects_valuable_memories(self):
  policy=json.loads((s.ROOT/'config/retention.json').read_text());now=datetime.datetime(2026,10,5,tzinfo=datetime.timezone.utc)
  m={'scope':'project','status':'active','type':'fact','importance':0.5,'tags':['temporary','expires:2026-10-01']}
  self.assertTrue(expired_memory(m,now,policy))
  for patch in [{'scope':'global'},{'status':'candidate'},{'type':'decision'},{'importance':0.9},{'tags':m['tags']+['pinned']},{'tags':['temporary']}]:self.assertFalse(expired_memory(m|patch,now,policy))
 def test_cleanup_does_not_follow_symlinks_or_touch_unknown_files(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);logs=root/'logs';logs.mkdir();outside=root/'outside.log';outside.write_text('keep')
   (logs/'link.log').symlink_to(outside);(logs/'keep.txt').write_text('keep');old=logs/'old.log';old.write_text('expired');os.utime(old,(0,0))
   policy={'owned_log_days':30,'receipt_days':180}
   self.assertEqual(log_candidates(root,datetime.datetime.now(datetime.timezone.utc),policy),[old.resolve()])
 def test_skills_have_real_refs_and_no_runtime_dependency(self):
  manifest=json.loads((s.ROOT/'inventories/coding-skills.json').read_text())
  for item in manifest['skills']:
   p=s.ROOT/'skills'/item['name']/'SKILL.md';t=p.read_text();self.assertIn('description:',t)
   if item['name'].startswith('coding-') or item['name'] in ['gam-memory','codegraph-context']:
    self.assertNotIn('omh runtime',t);self.assertNotIn('~/.hermes',t)
if __name__=='__main__':unittest.main()
