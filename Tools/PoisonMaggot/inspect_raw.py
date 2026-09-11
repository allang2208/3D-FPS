import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME'); out=root/'SourceAssets/PoisonMaggot20260911'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root/'Saved/Hunyuan3D/Candidates/poison_maggot_v01/asset_01.glb'))
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
report=[]
for o in objs:
 report.append({'name':o.name,'verts':len(o.data.vertices),'faces':len(o.data.polygons),'dims':list(o.dimensions),'bounds':[list(o.matrix_world@Vector(v)) for v in o.bound_box],'materials':[m.name for m in o.data.materials]})
print(json.dumps(report)); (out/'raw_inspection.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'raw_source.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100
world=bpy.data.worlds.new('Studio');s.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.2,.2,.2,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
for pos,power,size in [((2,-3,4),500,4),((-3,-1,1),300,3),((0,3,3),400,3)]:
 d=bpy.data.lights.new('Softbox','AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new('Softbox',d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos in [('front',(2,-3,1.6)),('back',(-2,3,1.6)),('side',(3,0,.5))]:
 d=bpy.data.cameras.new(name);c=bpy.data.objects.new(name,d);s.collection.objects.link(c);c.location=pos;c.rotation_euler=(-c.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=2.35;s.camera=c;s.render.filepath=str(out/f'raw_{name}.png');bpy.ops.render.render(write_still=True)
