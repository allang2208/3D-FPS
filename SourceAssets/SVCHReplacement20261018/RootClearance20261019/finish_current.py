"""Refresh current inputs, author the small pose layer, then save under one gate."""
import json,shutil,subprocess,sys
from pathlib import Path
O=Path(__file__).parent
# Preserve the first input/recipe before refreshing the independently updated V9.
previous=O/'PreviousInput';previous.mkdir(exist_ok=True)
for name in ('arms.json.gz','manifest.json','profile_before.json'):
    p=O/'Inputs'/name
    if p.exists() and not (previous/name).exists():shutil.copy2(p,previous/name)
for name in ('authoring_recipe.json','profile_root_clearance.json'):
    if (O/name).exists() and not (previous/name).exists():shutil.copy2(O/name,previous/name)
def run_script(name):
    f=O/name;exec(compile(f.read_text(encoding='utf-8'),str(f),'exec'),{'__file__':str(f),'__name__':'__main__'})
run_script('collect_inputs.py')
with (O/'author-current.log').open('w',encoding='utf-8') as log:
    result=subprocess.run(['py','-3.11',str(O/'author_root_clearance.py')],cwd=str(O),stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
if result.returncode:raise RuntimeError('Current V9 support authoring failed; profile not written. See author-current.log')
run_script('install_profile.py')
print('SVCH_CURRENT_ROOT_CLEARANCE_COMPLETE',flush=True)
