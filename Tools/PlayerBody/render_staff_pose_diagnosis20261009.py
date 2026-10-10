"""View UE-evaluated final CPU skin geometry; neutral materials, not a game screenshot."""
import bpy,json,sys,os
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion

ROOT=Path(os.environ.get('STAFF_DIAG_ROOT','D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonStaffCheck20261009'))
d=json.loads((ROOT/'poses.json').read_text())
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['idle']
bpy.ops.wm.read_factory_settings(use_empty=True)
def material(name,color,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.42
 return m
mats={'body':[material('Body',(.32,.25,.19))],
 'ue_chainmail_shirt':[material('Mail',(.26,.29,.33),.3)],
 'ue_steel_gauntlets':[material('Glove backing',(.06,.08,.10)),material('Steel plates',(.5,.55,.6),.7)],
 'staff':[material('Shaft',(.21,.09,.032))]}
objects={}
def create(name,p,faces,ids=None):
 # Reflect Y from UE coordinates and reverse winding to retain outward normals.
 me=bpy.data.meshes.new(name);me.from_pydata((p*[1,-1,1]/100).tolist(),[],faces[:,[0,2,1]].tolist());me.update()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 for m in mats[name]:me.materials.append(m)
 for i,f in enumerate(me.polygons):f.use_smooth=True;f.material_index=int(ids[i])%len(mats[name]) if ids is not None else 0
 objects[name]=ob
for name in d['meshes']:
 p=np.fromfile(ROOT/f'{args[0]}.{name}.vertices',dtype='<f4').reshape(-1,3)
 create(name,p,np.fromfile(ROOT/f'{name}.indices',dtype='<u4').reshape(-1,3),np.fromfile(ROOT/f'{name}.materials',dtype='<u4'))
staff=np.fromfile(ROOT/'staff.vertices',dtype='<f4').reshape(-1,3)
create('staff',staff,np.fromfile(ROOT/'staff.indices',dtype='<u4').reshape(-1,3))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=24
s.render.resolution_x=900;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Inspection');s.world.color=(.20,.20,.20);s.view_settings.view_transform='AgX'
for i,loc in enumerate([(-2,-3,4),(3,-1,2),(0,3,3)]):
 li=bpy.data.lights.new(f'Area{i}','AREA');li.energy=450;li.size=3
 ob=bpy.data.objects.new(li.name,li);s.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,1.1))-ob.location).to_track_quat('-Z','Y').to_euler()
c=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',c);s.collection.objects.link(co);s.camera=co;c.type='ORTHO';c.clip_start=.01;c.clip_end=100
for label in args:
 row=next(x for x in d['samples'] if x['label']==label)
 for name in d['meshes']:
  p=np.fromfile(ROOT/f'{label}.{name}.vertices',dtype='<f4').reshape(-1,3)*[1,-1,1]/100
  objects[name].data.vertices.foreach_set('co',p.ravel());objects[name].data.update()
 t=row['staff'];q=Quaternion((t[6],t[3],t[4],t[5]));r=np.array(q.to_matrix())
 p=(staff*np.array(t[7:10]))@r.T+np.array(t[:3]);p=p*[1,-1,1]/100
 objects['staff'].data.vertices.foreach_set('co',p.ravel());objects['staff'].data.update()
 hand=np.array(row['bones']['hand_r'][:3])*[1,-1,1]/100
 left=np.array(row['bones']['hand_l'][:3])*[1,-1,1]/100
 arm_centers={side:np.mean([row['bones'][bone+'_'+side][:3] for bone in ['upperarm','lowerarm','hand']],axis=0)*[1,-1,1]/100 for side in ['r','l']}
 for view,center,offset,scale in [
  ('right',(0,0,1.18),(-2,-3,1),1.35),('left',(0,0,1.18),(2,-3,1),1.35),
  ('grip',hand,(-1.5,-2,1),.40),('palm',hand,(1.5,2,.6),.40),
  ('left_hand',left,(1.5,-2,.6),.38),('left_palm',left,(-1.5,2,.6),.38),
  ('shirt_right',arm_centers['r'],(2,-3,.7),.75),('shirt_left',arm_centers['l'],(-2,-3,.7),.75)]:
  objects['body'].hide_render=view in ['grip','palm','left_hand','left_palm'] or view.startswith('shirt_')
  objects['ue_chainmail_shirt'].hide_render=view in ['grip','palm','left_hand','left_palm']
  objects['ue_steel_gauntlets'].hide_render=view.startswith('shirt_')
  objects['staff'].hide_render=view.startswith('shirt_')
  co.location=Vector(center)+Vector(offset);co.rotation_euler=(Vector(center)-co.location).to_track_quat('-Z','Y').to_euler();c.ortho_scale=scale
  s.render.filepath=str(ROOT/f'{label}-{view}.png');bpy.ops.render.render(write_still=True)
 objects['body'].hide_render=False;objects['ue_chainmail_shirt'].hide_render=True;objects['ue_steel_gauntlets'].hide_render=True
 objects['staff'].hide_render=False
 co.location=Vector(hand)+Vector((-1.5,-2,1));co.rotation_euler=(Vector(hand)-co.location).to_track_quat('-Z','Y').to_euler();c.ortho_scale=.40
 s.render.filepath=str(ROOT/f'{label}-bare_right.png');bpy.ops.render.render(write_still=True)
 co.location=Vector(left)+Vector((1.5,-2,.6));co.rotation_euler=(Vector(left)-co.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(ROOT/f'{label}-bare_left.png');bpy.ops.render.render(write_still=True)
 for ob in objects.values():ob.hide_render=False
print('STAFF_DIAGNOSIS_RENDERED',args)
