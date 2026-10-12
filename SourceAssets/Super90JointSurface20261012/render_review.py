"""Neutral offline geometry review, using UE saved mesh and compressed poses."""
import bpy,sys,json
import numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
d=np.load(O/('review_'+mode+'.npz'));shots=json.loads((O/'shots.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Neutral');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.16,.16,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.7;s.view_settings.view_transform='AgX'
def material(name,c,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=rough;return m
skin=material('Neutral clay: geometry only',(.42,.30,.23),.55);gun=material('Gun',(.035,.043,.05),.36)
me=bpy.data.meshes.new('Exact saved surface');me.from_pydata((d['p0']*[1,-1,1]/100).tolist(),[],d['triangles'].tolist());me.update()
ob=bpy.data.objects.new('UE compressed pose geometry',me);s.collection.objects.link(ob);me.materials.append(gun);me.materials.append(skin)
for i,f in enumerate(me.polygons):f.use_smooth=True;f.material_index=int(int(d['materials'][i]) in (1,2,3))
for i,loc in enumerate([(-.6,.05,.8),(.7,.8,.15),(-.3,1,.6)]):
 li=bpy.data.lights.new('Area'+str(i),'AREA');li.energy=[60,35,50][i];li.shape='DISK';li.size=.8
 lo=bpy.data.objects.new(li.name,li);s.collection.objects.link(lo);lo.location=loc;lo.rotation_euler=(Vector((0,.3,-.2))-lo.location).to_track_quat('-Z','Y').to_euler()
c=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',c);s.collection.objects.link(co);s.camera=co;c.clip_start=.001;c.lens=28
for i,row in enumerate(shots):
 me.vertices.foreach_set('co',(d['p'+str(i)]*[1,-1,1]/100).ravel());me.update()
 co.location=(0,0,0);co.rotation_euler=(Vector((0,.4,-.22))-co.location).to_track_quat('-Z','Y').to_euler();c.type='PERSP'
 s.render.filepath=str(O/(mode+'_'+str(i)+'.png'));bpy.ops.render.render(write_still=True)
 if i==0:
  center=np.array(row['bones']['lowerarm_l']['position'])*[1,-1,1]/100
  co.location=Vector(center)+Vector((.10,-.30,.20));co.rotation_euler=(Vector(center)-co.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=.27
  s.render.filepath=str(O/(mode+'_elbow.png'));bpy.ops.render.render(write_still=True)
print('SUPER90_REVIEW_RENDERED',mode)
