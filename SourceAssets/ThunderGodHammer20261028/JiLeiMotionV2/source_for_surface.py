import bpy,json
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'JiLeiMotionV2_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
native=json.loads((P/'native-mesh.json').read_text());names=list(native['bones'])
C=Matrix.Diagonal((1,-1,1,1));out={}
for kind in ['Charge','Release']:
 a=bpy.data.actions['A_ThunderHammer_Call'+kind];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];frames=[]
 for frame in range(round(a.frame_range[1])+1):
  scene.frame_set(frame);row=[]
  for name in names:
   b=rig.pose.bones.get(name)
   if b:
    m=C@b.matrix@C;q=m.to_quaternion();v=m.translation*100
    row.append([*v,q.x,q.y,q.z,q.w,100,100,100])
   else:row.append(native['bones'][name]['transform'])
  frames.append(row)
 out[kind]=dict(names=names,fps=240,frames=frames)
(P/'native-poses.json').write_text(json.dumps(out,separators=(',',':')))
print('JI_LEI_SOURCE_SURFACE_POSES',flush=True)
