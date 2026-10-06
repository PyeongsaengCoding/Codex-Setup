"""Bounded local process groups: a timeout cannot leave a coding child writing."""
import os,signal,subprocess

def run_bounded(argv,*,input_text,stdout,stderr,timeout):
 process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,text=True,start_new_session=True)
 try:
  process.communicate(input_text,timeout=timeout)
  return process.returncode
 except (subprocess.TimeoutExpired,KeyboardInterrupt) as error:
  try:os.killpg(process.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:
   try:os.killpg(process.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   process.wait()
  # Parent exit does not prove its descendants exited. Reap the owned process group too.
  try:os.killpg(process.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  if isinstance(error,KeyboardInterrupt):raise
  return 124
