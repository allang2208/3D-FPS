import bpy,json,pathlib,math
from mathutils import Matrix,Vector
O=pathlib.Path(__file__).parent;R=O.parent
src=O/'PKM_Gameplay_Editable.blend'
if not src.exists():src=R/'Integration04/PKM_Gameplay_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(src))
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
rows={}
for clip,f in [('PKM_Game_idle',0),('PKM_Reload_Normal',65),('PKM_Reload_Normal',156),('PKM_Reload_Normal',282)]:
 a=bpy.data.actions[clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
 W=r.pose.bones['WPN_root'].matrix;inv=(W@fit).inverted()
 bones={b.name:[round(v,5) for v in inv@b.matrix.translation] for b in r.pose.bones if any(b.name.startswith(p) for p in ['hand_','upperarm_','lowerarm_','index_','middle_','thumb_','pinky_'])}
 up=W.to_3x3()@Vector((0,0,1));rows[clip+str(f)]={'up':list(up),'roll_deg':math.degrees(math.atan2(up.x,up.z)),'bones':bones}
 if f==0:
  dg=bpy.context.evaluated_depsgraph_get();parts=[]
  for ob in s.objects:
   if ob.type!='MESH' or ob.name.startswith('New_'):continue
   ev=ob.evaluated_get(dg);pts=[inv@(ev.matrix_world@v.co) for v in ev.data.vertices]
   parts.append({'name':ob.name,'bone':ob.get('mechanical_bone'),'materials':[m.name for m in ob.data.materials], 'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]})
  rows['parts']=parts
(O/('pose_after.json' if src.parent==O else 'pose_before.json')).write_text(json.dumps(rows,indent=2))
print('PKM_POSE_READ_DONE')
