import unittest,tempfile,sys,subprocess,os,signal,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from process_control import run_bounded
import setup_runtime as s
class ReviewRegressions(unittest.TestCase):
 def test_restore_accepts_managed_receipt_and_removes_created_link(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);backup=root/'backup';backup.mkdir();f=root/'AGENTS.md';f.write_text('after');(backup/'0').write_text('before');source=root/'skill';source.mkdir();link=root/'link';link.symlink_to(source)
   rows=[{'target':str(f),'kind':'file','backup':str(backup/'0'),'previous_mode':0o600,'applied_sha256':s.digest(f),'link_target':None},{'target':str(link),'kind':'link','backup':None,'previous_mode':None,'applied_sha256':None,'link_target':str(source)}]
   (backup/'receipt.json').write_text(json.dumps(rows));s.restore(backup)
   self.assertEqual(f.read_text(),'before');self.assertFalse(link.is_symlink())
 def test_timeout_kills_ignoring_grandchild(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'pid';out=Path(d)/'output'
   child='import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); open('+repr(str(p))+',"w").write(str(os.getpid())); time.sleep(30)'
   parent='import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'+repr(child)+']); time.sleep(30)'
   pid=None
   try:
    with out.open('w') as stream:rc=run_bounded([sys.executable,'-c',parent],input_text='',stdout=stream,stderr=stream,timeout=1)
    self.assertEqual(rc,124);pid=int(p.read_text());time.sleep(.1)
    alive=True
    for _ in range(20):
     try:os.kill(pid,0)
     except ProcessLookupError:alive=False;break
     time.sleep(.05)
    self.assertFalse(alive,'grandchild remains live')
   finally:
    if pid:
     try:os.kill(pid,signal.SIGKILL)
     except ProcessLookupError:pass
if __name__=='__main__':unittest.main()

class MoreRegressions(unittest.TestCase):
 def test_unicode_mcp_paths(self):
  s.managed_config('',s.config_block({'codegraph':'/tmp/🧪/codegraph','gam_mcp':'/tmp/🧪/gam'}))
 def test_isolated_parent_symlink_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);home=root/'home';outside=root/'outside';home.mkdir();outside.mkdir();(home/'.agents').symlink_to(outside)
   with self.assertRaises(RuntimeError):s.validate_isolated(home,home/'.codex',home/'state')

class InterruptedApplyTests(unittest.TestCase):
 def test_partial_failure_has_restorable_receipt(self):
  from unittest.mock import patch
  import apply_managed as m
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src=root/'source';(src/'instructions').mkdir(parents=True);(src/'skills').mkdir()
   (src/'instructions/AGENTS.md').write_text('new-global');(src/'11-working-method.md').write_text('model roles')
   (src/'config').mkdir();(src/'config/models.json').write_text('{}')
   home=root/'home';(home/'.codex').mkdir(parents=True);(home/'Downloads/Coding').mkdir(parents=True);(home/'Downloads/Coding/AGENTS.md').write_text('old-coding')
   original=os.replace
   def replace(a,b):
    if Path(b).resolve()==(home/'.codex/working-method.md').resolve():raise PermissionError('injected write failure')
    return original(a,b)
   with patch.object(m,'ROOT',src),patch.object(m.os,'replace',side_effect=replace):
    with self.assertRaises(PermissionError):m.apply(home,root/'backups',True)
   receipts=list((root/'backups').glob('*/receipt.json'));self.assertEqual(len(receipts),1)
   s.restore(receipts[0].parent);self.assertFalse((home/'.codex/AGENTS.md').exists());self.assertEqual((home/'Downloads/Coding/AGENTS.md').read_text(),'old-coding')

class RetentionAndBackupTests(unittest.TestCase):
 def test_only_reviewed_or_disposable_completed_raw_logs_expire(self):
  import datetime
  from maintain import log_candidates
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);now=datetime.datetime.now(datetime.timezone.utc);expected=[]
   cases=[('evaluations/a/passed',{'semantic_verdict':'passed','execution_status':'executed'},True),('evaluations/a/pending',{'semantic_verdict':'not_reviewed','execution_status':'executed'},False),('runs/allowed',{'status':'executed_not_verified','exit_code':0,'disposable_logs':True},True),('runs/protected',{'status':'executed_not_verified','exit_code':0,'disposable_logs':False},False),('runs/failed',{'status':'execution_failed','exit_code':124,'disposable_logs':True},False)]
   for name,receipt,expire in cases:
    folder=root/name;folder.mkdir(parents=True);(folder/'receipt.json').write_text(json.dumps(receipt));p=folder/'events.jsonl';p.write_text('evidence');os.utime(p,(now.timestamp()-40*86400,)*2)
    if expire:expected.append(p)
   self.assertEqual(set(log_candidates(root,now,{'owned_log_days':30,'receipt_days':180})),{p.resolve() for p in expected})
 def test_config_crash_before_replace_has_receipt_and_preserves_target(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'config.toml';p.write_text('before')
   with patch.object(s.os,'replace',side_effect=PermissionError('injected')):
    with self.assertRaises(PermissionError):s.backup_write(p,b'after',root/'state')
   receipts=list((root/'state/backups').glob('*/receipt.json'));self.assertEqual(len(receipts),1);s.restore(receipts[0].parent);self.assertEqual(p.read_text(),'before')

class FinalReviewTests(unittest.TestCase):
 def test_isolated_state_leaf_symlink_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);home=root/'home';state=home/'state';state.mkdir(parents=True);outside=root/'outside';outside.write_text('private');(state/'tools.json').symlink_to(outside)
   with self.assertRaises(RuntimeError):s.validate_isolated(home,home/'.codex',state)
 def test_relative_backup_path_is_restorable_from_other_cwd(self):
  from unittest.mock import patch
  import apply_managed as m
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve();src=root/'source';(src/'instructions').mkdir(parents=True);(src/'skills').mkdir();(src/'instructions/AGENTS.md').write_text('new');(src/'11-working-method.md').write_text('model roles');home=root/'home';(home/'.codex').mkdir(parents=True);target=home/'.codex/AGENTS.md';target.write_text('old');before=Path.cwd()
   (src/'config').mkdir();(src/'config/models.json').write_text('{}')
   try:
    os.chdir(root)
    with patch.object(m,'ROOT',src):result=m.apply(home,Path('relative-backups'),True)
    os.chdir(src);s.restore(result['backup']);self.assertEqual(target.read_text(),'old')
   finally:os.chdir(before)
