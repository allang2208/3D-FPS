"""Read the actual Jason lips and bottle rims for offline contact authoring."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/Consume20261006'
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mesh=u.load_asset(cfg['heads'][cfg['default_head']]['mesh'])
ref=mesh.skeleton.get_reference_pose()
def xyz(v):return [v.x,v.y,v.z]
anatomy={}
for n in u.AnimPoseExtensions.get_bone_names(ref):
    name=str(n)
    if name=='head' or ('lip' in name.lower() and ('_C_' in name or 'upper' in name.lower() or 'lower' in name.lower())):
        t=u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)
        anatomy[name]=xyz(t.translation)
data=dict(head_mesh=mesh.get_path_name(),anatomy=anatomy,tiers=[])
visuals=json.loads((ROOT/'Content/ColdSteelData/potion_visuals.json').read_text(encoding='utf-8-sig'))
for v in visuals['tiers']:
    shell=u.load_asset(v['shell'])
    b=shell.get_bounds()
    data['tiers'].append(dict(tier=v['tier'],definitions=v['definitions'],shell=v['shell'],grip_height=v['grip_height_cm'],
        rim=[b.origin.x,b.origin.y,b.origin.z+b.box_extent.z],bottom=b.origin.z-b.box_extent.z))
(OUT/'contact-anatomy.json').write_text(json.dumps(data,indent=2))
print('CONSUME_ANATOMY_SAVED '+json.dumps(data))
