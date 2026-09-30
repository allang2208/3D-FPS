"""Native editable FK scene containing the two base drum reloads; no rendering."""
import bpy,bmesh,json,gzip
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());B=S['rigs']['201']['bones'];AN=json.loads((O/'animations.json').read_text());bpy.context.preferences.filepaths.save_version=0
def ue(v):return Matrix.LocRotScale(Vector(v['p']),Quaternion((v['q'][3],*v['q'][:3])),Vector(v['s']))
def convert(m):
 p,q,s=m.decompose();return Matrix.LocRotScale(Vector((p.x,-p.y,p.z))*.01,Quaternion((q.w,-q.x,q.y,-q.z)),s*.01)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/Current201.fbx'),use_anim=False)
old=next(a for a in bpy.data.objects if a.type=='ARMATURE');meshes=[a for a in bpy.data.objects if a.type=='MESH']
for a in meshes:
 world=a.matrix_world.copy();a.parent=None;a.modifiers.clear();a.data.transform(world);a.matrix_world=Matrix.Identity(4)
 # Factory magazines and both cloth sets are separate option identities.
 hidden=[i for i,s in enumerate(S['rigs']['201']['slots']) if s['name'].startswith(('M_LMG201_Magazine','M_LMG201_Feed__','M_LMG201_Cloth33__'))]
 bm=bmesh.new();bm.from_mesh(a.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in hidden],context='FACES');bm.to_mesh(a.data);bm.free()
bpy.data.objects.remove(old,do_unlink=True)
data=bpy.data.armatures.new('201NativeFK');rig=bpy.data.objects.new('201_Drum46_NativeFK',data);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for n,v in B.items():
 b=data.edit_bones.new(n);b.matrix=convert(ue(v));b.length=.02
for n,v in B.items():
 if v['parent']:data.edit_bones[n].parent=data.edit_bones[v['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
for a in meshes:a.parent=rig;a.modifiers.new('Native skin','ARMATURE').object=rig
with bpy.data.libraries.load(str(O/'LMG201_Drum46.blend'),link=False) as (src,dst):dst.objects=['SM_LMG201_LargeDrum']
drum=dst.objects[0];bpy.context.collection.objects.link(drum);drum.data.transform(data.bones['WPN_SOCKET_Magazine'].matrix_local);drum.parent=rig;group=drum.vertex_groups.new(name='WPN_SOCKET_Magazine');group.add(list(range(len(drum.data.vertices))),1.,'REPLACE');drum.modifiers.new('Magazine contact track','ARMATURE').object=rig
rest={b.name:b.matrix_local.copy() for b in data.bones};localrest={b.name:b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in data.bones}
rig.animation_data_create();scene=bpy.context.scene;scene.render.fps=120;scene.frame_start=0
for key in ['reload','reload_empty']:
 info=AN['clips']['base/'+key]
 with gzip.open(info['keys'],'rt') as f:tracks=json.load(f)
 with gzip.open(S['clips']['201_base_'+key]['file'],'rt') as f:source=json.load(f)
 action=bpy.data.actions.new('A_LMG201_base_drum_'+key);rig.animation_data.action=action;rig.pose.bones['WPN_root'].keyframe_insert(data_path='location',frame=0);bag=action.layers[0].strips[0].channelbags[0]
 for c in list(bag.fcurves):bag.fcurves.remove(c)
 rows={n:[] for n in B};last={}
 for i,frame in enumerate(source):
  world={}
  def evaluate(n):
   if n not in world:
    v=ue(tracks[n][i] if n in tracks else frame[n]['local']);p=B[n]['parent'];world[n]=evaluate(p)@v if p else v
   return world[n]
  posed={n:convert(evaluate(n)) for n in B}
  for n in B:
   p=B[n]['parent'];m=localrest[n].inverted()@(posed[p].inverted()@posed[n] if p else posed[n]);loc,q,scale=m.decompose()
   if n in last and q.dot(last[n])<0:q.negate()
   last[n]=q.copy();rows[n].append((tuple(loc),tuple(q),tuple(scale)))
 for n,values in rows.items():
  rig.pose.bones[n].rotation_mode='QUATERNION'
  for prop,count,col in [('location',3,0),('rotation_quaternion',4,1),('scale',3,2)]:
   for j in range(count):
    c=bag.fcurves.new(data_path='pose.bones["'+n+'"].'+prop,index=j);c.keyframe_points.add(len(values));c.keyframe_points.foreach_set('co',[x for i,v in enumerate(values) for x in (i,v[col][j])])
    for p in c.keyframe_points:p.interpolation='LINEAR'
    c.update()
 action.use_fake_user=True;print('DRUM46_EDITABLE_ACTION',key,flush=True)
rig.animation_data.action=bpy.data.actions['A_LMG201_base_drum_reload'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_end=400
for name,f in [('Old drum released',36),('Replacement appears',112),('Insert',195),('Seat',220),('Open fingers normal',236),('Support returned normal',300)]:scene.timeline_markers.new(name,frame=f)
rig['AuthoringSource']='Current201 live export + current installed AKM PalmGripV3 + current 201 reload/right hand';rig['OtherGripFamilies']=str(O/'Keys');rig['Visibility']='Hide socket drum between frames 36 and 112; dropped physical prop is runtime only';scene.frame_set(0);bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Drum46_Animated.blend'),compress=True);print('DRUM46_EDITABLE_SAVED',flush=True)
