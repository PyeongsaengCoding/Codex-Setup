"""Initialize GAM through its pinned API with explicit paths, without replacing HOME."""
import argparse
from pathlib import Path
from global_memory.config import load_settings,PlatformPaths
from global_memory.vault.initialize import initialize
p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--data',type=Path,required=True);a=p.parse_args()
settings=load_settings(a.config)
paths=PlatformPaths(config_dir=a.config.parent,data_dir=a.data,log_dir=a.home/'Library/Logs/global-memory',runtime_dir=a.data/'run')
r=initialize(settings,paths)
print('GAM vault initialized' if r.created else 'GAM vault ready')
