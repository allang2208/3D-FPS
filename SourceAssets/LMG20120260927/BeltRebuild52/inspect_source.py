"""Local model inspection of the rebuilt chain and the measured live enclosure."""
import bpy,json,gzip
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_BeltRebuild52.blend'),use_scripts=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40
scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Inspection world');scene.world.color=(.2,.2,.2);scene.view_settings.view_transform='AgX'
for ob in list(bpy.data.objects):
 if ob.name.startswith('New_') or ob.name.startswith('Old_06_'):ob.hide_render=True
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
for loc,power,size in [((.15,-.03,.17),8,.15),((-.12,.2,.12),6,.15),((.07,.29,.08),7,.10)]:
 bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.shape='DISK';ob.data.size=size;aim(ob,(.025,.135,.03))
bpy.ops.object.camera_add(location=(.19,.00,.135));cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.125;aim(cam,(.027,.135,.034))
(O/'Inspection').mkdir(exist_ok=True)
def render(name):scene.render.filepath=str(O/'Inspection'/name);bpy.ops.render.render(write_still=True)
render('chain.png')
with gzip.open(O/'context.json.gz','rt') as f:d=json.load(f)
materials={}
for role,color,metal,rough in [('Body',(.085,.095,.105),.8,.42),('Cloth',(.085,.09,.065),0,.86)]:
 m=bpy.data.materials.new('Inspection_'+role);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;materials[role]=m
for si,s in enumerate(d['slots']):
 n=s['name']
 if any(t in n for t in ['Manny','Skin','Glove','Sleeve']):continue
 tris=[r[:3] for r in d['triangles'] if r[3]==si]
 if not tris:continue
 ids=sorted({v for t in tris for v in t});lookup={v:i for i,v in enumerate(ids)}
 me=bpy.data.meshes.new(n);me.from_pydata([d['positions_root_m'][str(i)] for i in ids],[],[[lookup[v] for v in t] for t in tris]);me.update()
 ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(materials['Cloth' if 'OldBox_Cloth' in n else 'Body'])
 if any(t in n for t in ['R38_Interior','R38_Satin','G43_LidCoat']):ob.hide_render=True
cam.location=(.21,-.01,.17);cam.data.ortho_scale=.175;aim(cam,(.014,.135,.035))
render('feed_cutaway.png')
for ob in bpy.data.objects:
 if any(t in ob.name for t in ['R38_Interior','R38_Satin','G43_LidCoat']):ob.hide_render=False
render('feed_closed.png')
print('BELT52_SOURCE_INSPECTION_SAVED',flush=True)
