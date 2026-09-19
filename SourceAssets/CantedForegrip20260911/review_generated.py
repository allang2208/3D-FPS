import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O/'canted_grip_textured_00002_.glb'))
obs=[o for o in bpy.context.scene.objects if o.type=='MESH']; pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]; lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)));center=(lo+hi)/2
(O/'generated_bounds.json').write_text(json.dumps({'min':list(lo),'max':list(hi),'objects':[(o.name,len(o.data.vertices),sum(len(p.vertices)-2 for p in o.data.polygons)) for o in obs]},indent=2))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=900;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.5
c=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=max(hi-lo)*1.4
for pos in [(3,-4,5),(-3,2,2)]:
 d=bpy.data.lights.new('Area','AREA');d.energy=700;d.size=4;o=bpy.data.objects.new('Area',d);s.collection.objects.link(o);o.location=center+Vector(pos);o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos in [('front',(0,-4,0)),('side',(4,0,0)),('hero',(3,-4,2))]:
 c.location=center+Vector(pos);c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/('generated_'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'CantedForegrip_5080_Candidate.blend'))

