"""Play isolated source clips on the reloaded candidate; inspect actual mesh morph weights."""
import json
from pathlib import Path
import unreal as u
base=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117')
out=base/'R4_PoseRefined';review=out/'Review'
record=json.loads((out/'variant_saved.json').read_text())
mesh=u.load_asset(record['asset']);names=record['morphs']
clips=json.loads((review/'clips.json').read_text())['poses']
observed={}
for key in ['Rifle.Idle_0.15','Rifle.Reload_0.45','Melee.FullBody.Slash1_0.15','Melee.FullBody.Slash1_0.45']:
    frame=clips[key]
    weights=list(u.JasonReviewGraph.sample_morphs(mesh,u.load_asset(frame['asset']),frame['time'],names))
    observed[key]={'post_curves':weights[:4],'active_mesh_morph_weights':weights[4:]}
    print('R4_DRIVER_RESULT',key,weights)
(review/'ue_driver_check.json').write_text(json.dumps(observed,indent=2))
if any(len(v['active_mesh_morph_weights'])!=4 for v in observed.values()):raise ValueError('No post process evaluation')
for i,name in enumerate(names):
    if max(f['active_mesh_morph_weights'][i] for f in observed.values())<.05:raise ValueError('Inactive '+name)
