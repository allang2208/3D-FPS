import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Belt08/PKM_Gameplay_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene;a=bpy.data.actions['PKM_Game_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);W=r.pose.bones['WPN_root'].matrix@fit;B=r.data.bones['WPN_root'].matrix_local@fit
result={'arm':{},'rest':{},'geometry':{},'finger_basis':{}}
for side in ['l','r']:
 for n in ['clavicle','upperarm','lowerarm','hand']:
  name=n+'_'+side;result['arm'][name]=list(W.inverted()@r.pose.bones[name].matrix.translation);result['rest'][name]=[list(row) for row in r.data.bones[name].matrix_local]
 for digit in ['thumb','index','middle','ring','pinky']:
  for j in range(1,4):
   name=f'{digit}_{j:02}_{side}';b=r.pose.bones[name];localrest=b.parent.bone.matrix_local.inverted()@b.bone.matrix_local
   result['finger_basis'][name]=[list(row) for row in (localrest.inverted()@b.parent.matrix.inverted()@b.matrix)]
 for digit in ['index','middle','pinky','thumb']:
  name=digit+'_01_'+side;result['rest'][name]=list(r.data.bones['hand_'+side].matrix_local.inverted()@r.data.bones[name].matrix_local.translation)
for bone in ['PKM_Cover','PKM_Box','PKM_Charge','PKM_Latch']:
 verts=[B.inverted()@o.matrix_world@v.co for o in s.objects if o.type=='MESH' and o.get('mechanical_bone')==bone for v in o.data.vertices]
 result['geometry'][bone]=[list(Vector(min(v[k] for v in verts) for k in range(3))),list(Vector(max(v[k] for v in verts) for k in range(3)))]
(O/'rig_inputs.json').write_text(json.dumps(result,indent=2));print(json.dumps({'arm':result['arm'],'geometry':result['geometry']},indent=2))
