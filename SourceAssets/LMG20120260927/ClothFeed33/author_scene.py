"""Store all five contact/return families as editable Blender actions."""
import bpy,json,gzip
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).parent;d=json.loads((O/'inputs.json').read_text())['meshes']['201'];info=json.loads((O/'motion.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_Cloth33_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0;rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='POSE';rig.animation_data_create()
names=d['names'];parents={n:names[i] if i>=0 else None for n,i in zip(names,d['parents'])}
def ue(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],v[3],v[4],v[5])),Vector(v[7:10]))
def blender(m):
 p,q,s=m.decompose();return Matrix.LocRotScale(Vector((p.x,-p.y,p.z))*.01,Quaternion((q.w,-q.x,q.y,-q.z)),s*.01)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};localrest={b.name:b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
sc=bpy.context.scene;sc.render.fps=120;sc.frame_start=0;sc.frame_end=744
for family in ('base','vertical','canted','prism','angled'):
 with gzip.open(O/(family+'_tracks.json.gz'),'rt',encoding='utf8') as f:tracks=json.load(f)
 action=bpy.data.actions.new('A_LMG201_Cloth33_'+family+'_reload');rig.animation_data.action=action
 rig.pose.bones['WPN_root'].keyframe_insert(data_path='location',frame=0)
 bag=action.layers[0].strips[0].channelbags[0]
 for curve in list(bag.fcurves):bag.fcurves.remove(curve)
 rows={n:[] for n in rest};last={}
 for i in range(745):
  worlds={}
  for n in names:
   m=ue(tracks[n][i]);worlds[n]=worlds[parents[n]]@m if parents[n] else m
  targets={n:blender(worlds[n]) for n in rest}
  for n in rest:
   parent=rig.data.bones[n].parent;m=localrest[n].inverted()@(targets[parent.name].inverted()@targets[n] if parent else targets[n]);p,q,s=m.decompose()
   if n in last and q.dot(last[n])<0:q.negate()
   last[n]=q.copy();rows[n].append((tuple(p),tuple(q),tuple(s)))
 for n,values in rows.items():
  rig.pose.bones[n].rotation_mode='QUATERNION'
  for prop,components,col in [('location',3,0),('rotation_quaternion',4,1),('scale',3,2)]:
   for j in range(components):
    curve=bag.fcurves.new(data_path='pose.bones["'+n+'"].'+prop,index=j);curve.keyframe_points.add(len(values))
    curve.keyframe_points.foreach_set('co',[x for i,v in enumerate(values) for x in (i,v[col][j])])
    for k in curve.keyframe_points:k.interpolation='LINEAR'
    curve.update()
 action.use_fake_user=True;print('CLOTH33_EDITABLE_ACTION',family,flush=True)
rig.animation_data.action=bpy.data.actions['A_LMG201_Cloth33_base_reload']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
for key in ['cover_open','box_out','box_seat','belt_seat','cover_close']:
 sc.timeline_markers.new(key,frame=round(info['phases'][key]*120))
sc.frame_set(0);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Cloth33_Animated.blend'))
print('CLOTH33_ANIMATED_SOURCE_SAVED',flush=True)
