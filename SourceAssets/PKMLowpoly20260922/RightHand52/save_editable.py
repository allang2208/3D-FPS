"""Editable native-rig source: current bare arms, weapon, all five corrected clips."""
from pathlib import Path
import bpy,json,numpy as np
from mathutils import Matrix,Quaternion
P=Path(__file__).resolve().parent;d=json.loads((P/'Inputs/bare.json').read_text());d.update({k:v for k,v in json.loads((P/'Authored/BarePalmV7.json').read_text()).items() if k in ['positions','weights','triangles']});bones=d['bones'];idx={v['index']:n for n,v in bones.items()};parents={n:idx.get(v['parent']) for n,v in bones.items()};F=np.diag([1.,-1.,1.]);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0

def matrix(t):
 q=t['q'];m=np.eye(4);m[:3,:3]=np.array(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())*np.array(t['s']);m[:3,3]=t['p'];return m
rest={n:matrix(v) for n,v in bones.items()};localrest={n:np.linalg.inv(rest[parents[n]])@m if parents[n] else m for n,m in rest.items()};invlocal={n:np.linalg.inv(m) for n,m in localrest.items()}
arm=bpy.data.armatures.new('PKM_Native');rig=bpy.data.objects.new('PKM_RightHand52',arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for n,m in rest.items():
 b=arm.edit_bones.new(n);x=np.eye(4);x[:3,:3]=F@m[:3,:3]@F;x[:3,3]=F@m[:3,3]*.01;b.matrix=Matrix(x);b.length=.025
for n in bones:
 if parents[n]:arm.edit_bones[n].parent=arm.edit_bones[parents[n]]
bpy.ops.object.mode_set(mode='OBJECT')
for label,data in [('BarePalmV7',d),('Weapon',json.loads((P.parent/'LeftState50/Input/Weapon.json').read_text()))]:
 mesh=bpy.data.meshes.new(label);faces=data['triangles']
 if label=='Weapon':faces=[f for f,mi in zip(faces,data['triangle_materials']) if mi not in (1,2) and '__Old' not in data['materials'][mi]]
 mesh.from_pydata((np.array(data['positions'])*[.01,-.01,.01]).tolist(),[],faces);mesh.update();obj=bpy.data.objects.new(label,mesh);bpy.context.collection.objects.link(obj);obj.parent=rig;obj.modifiers.new('Native skin','ARMATURE').object=rig
 mat=bpy.data.materials.new(label);mat.diffuse_color=(.62,.43,.30,1) if label=='BarePalmV7' else (.15,.17,.18,1);mesh.materials.append(mat)
 for f in mesh.polygons:f.use_smooth=label=='BarePalmV7'
 for n in {n for ws in data['weights'] for n in ws}:obj.vertex_groups.new(name=n)
 for vi,ws in enumerate(data['weights']):
  for n,w in ws.items():obj.vertex_groups[n].add([vi],w,'REPLACE')
rig.animation_data_create()
for family in ['base','vertical','canted','prism','angled']:
 clip=json.loads((P/'Inputs'/f'{family}.json').read_text());edit=json.loads((P/'Authored'/f'{family}.json').read_text());action=bpy.data.actions.new('PKM52_'+family+'_reload_empty');action.use_fake_user=True;rig.animation_data.action=action
 for b in rig.pose.bones:
  b.rotation_mode='QUATERNION'
  for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
 curves={(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
 data={n:[] for n in bones};previous={n:None for n in bones}
 for i,row in enumerate(clip['frames']):
  world={n:matrix(v) for n,v in row.items()}
  for n in bones:
   local=matrix(edit['tracks'][n][i]) if n in edit['tracks'] else (np.linalg.inv(world[parents[n]])@world[n] if parents[n] else world[n]);basis=invlocal[n]@local;x=np.eye(4);x[:3,:3]=F@basis[:3,:3]@F;x[:3,3]=F@basis[:3,3]*.01;loc,q,scale=Matrix(x).decompose()
   if previous[n] is not None and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();data[n].append((loc,q,scale))
 for n,values in data.items():
  for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   for axis in range(count):
    c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(values));c.keyframe_points.foreach_set('co',[v for i,row in enumerate(values) for v in (i,row[field][axis])])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 print('PKM52_EDITABLE_ACTION',family,flush=True)
s=bpy.context.scene;s.render.fps=120;s.frame_start=0;s.frame_end=792;rig.animation_data.action=bpy.data.actions['PKM52_base_reload_empty'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];s.frame_set(558);rig['Source']='Current UE raw poses plus RightHand52/Authored; native rig, centimetres converted to metres; neutral materials for editing.'
(P/'Editable').mkdir(exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Editable/PKM_RightHand52.blend'));print('PKM52_EDITABLE_COMPLETE',flush=True)

