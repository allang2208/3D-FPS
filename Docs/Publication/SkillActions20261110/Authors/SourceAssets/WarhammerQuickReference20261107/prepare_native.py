import bpy,json
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path('D:/FPS3D/FPSGAME/SourceAssets/WarhammerQuickReference20261107')
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/SteelWarhammer20261014/QuickCombatLeftWristV7/Warhammer_QuickCombat_LeftWristV7_Editable.blend')
r=bpy.data.objects['SK_RusticPickaxe_Rig'];data=json.loads((P/'native-idle.json').read_text());parents={b.name.lower():b.parent.name.lower() if b.parent else 'sk_rusticpickaxe_rig' for b in r.data.bones};parents['sk_rusticpickaxe_rig']=None
world={};C=Matrix.Diagonal(Vector((1,-1,1)))
def solve(n):
 if n not in world:
  k=data['bones'][n];local=Matrix.LocRotScale(Vector(k['p']),Quaternion(k['q']),Vector(k['s']));p=parents[n];world[n]=solve(p)@local if p else local
 return world[n]
for n in data['bones']:solve(n)
out={n:{'p':list(C@m.translation*.01),'q':list((C@m.to_quaternion().to_matrix()@C).to_quaternion()),'s':list(m.to_scale())} for n,m in world.items()}
(P/'native-author-inputs.json').write_text(json.dumps(dict(parents=parents,world=out,blender_names={n.lower():n for n in r.data.bones.keys()})))
print('AUTHOR_FRAME',json.dumps({n:out[n]['p'] for n in ['wpn_root','hand_l','hand_r','upperarm_l']}))
