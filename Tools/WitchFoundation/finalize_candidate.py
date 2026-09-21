"""Bind the isolated mesh after the newly built native authoring helper is loaded."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchFoundation20260920')
BASE='/Game/Monsters/WitchFoundation'
mesh=u.load_asset(BASE+'/SK_WitchFoundation')
skeleton=u.load_asset(BASE+'/SKEL_WitchFoundation')
u.WitchMotionCandidate.assign_foundation_skeleton(mesh,skeleton)
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Candidate binding could not be saved')
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8'))
report['pending_native_binding']=False
report['status']='native integration and candidate assets authored; user runtime test pending'
report['f6']={'id':'WitchFoundation','label':'巫婆·动作基础候选','class':'/Script/FPSGAME.WitchMotionCandidate'}
report['runtime_tested']=False
(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SAVED isolated Quinn mesh / skeleton binding; F6 native candidate ready for user test')
