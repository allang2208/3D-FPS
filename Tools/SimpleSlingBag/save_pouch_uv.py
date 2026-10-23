"""Save planar UVs on the two newly closed strap interfaces only."""
import json,runpy
from pathlib import Path
from datetime import datetime
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SimpleSlingBag20261022'
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('Finish PIE before saving the pouch')
    if any(p.get_path_name()=='/Game/Characters/SimpleSlingBag20261022/SM_SimpleSlingPouch' for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Pouch has unsaved editor edits')
status=R/'integration_job_status.json';state=json.loads(status.read_text())
state.update(state='saving_seam_uv',updated_at=datetime.now().isoformat(timespec='seconds'))
status.write_text(json.dumps(state,indent=2))
try:
    ns=runpy.run_path(str(P/'Tools/SimpleSlingBag/save_assets.py'))
    ns['static']('Pouch','SM_SimpleSlingPouch')
    ns['saved']['seam_uv']='planar mapping on two new cap faces; original surface UVs preserved'
    ns['receipt']()
    state.pop('pending',None)
    state.update(state='completed',updated_at=datetime.now().isoformat(timespec='seconds'))
    status.write_text(json.dumps(state,indent=2));print('SLING_SEAM_UV_SAVED',flush=True)
except Exception as error:
    state.update(state='failed',error=str(error));status.write_text(json.dumps(state,indent=2));raise
