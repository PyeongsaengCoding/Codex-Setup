import unittest,tempfile,subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CleanInstallTests(unittest.TestCase):
 def test_isolated_plan_supports_an_empty_user_namespace(self):
  with tempfile.TemporaryDirectory() as d:
   r=subprocess.run([sys.executable,str(ROOT/'scripts/setup_runtime.py'),'plan','--isolated','--home',d,'--state',str(Path(d)/'state'),'--codex-home',str(Path(d)/'.codex')],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
   result=json.loads(r.stdout);self.assertTrue(result['isolated']);self.assertFalse((Path(d)/'.codex').exists())
if __name__=='__main__':unittest.main()
