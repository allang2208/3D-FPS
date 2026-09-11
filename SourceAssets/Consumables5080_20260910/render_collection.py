import bpy,math
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True)
for i,asset in enumerate(['hp_potion','mp_potion','ammo_556','ammo_762']):
 before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(P/(asset+'_candidate_v02.glb')))
 objs=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
 for o in objs:
  matrix=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Identity(4);o.data.transform(matrix)
 coords=[v.co for o in objs for v in o.data.vertices];lo=Vector(tuple(min(v[k] for v in coords) for k in range(3)));hi=Vector(tuple(max(v[k] for v in coords) for k in range(3)));h=hi.z-lo.z
 center=Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,lo.z))
 for o in objs:
  for v in o.data.vertices:v.co=(v.co-center)/h
  o.rotation_euler.z=-.16;o.location.x=(i-1.5)*1.35
 s=bpy.context.scene
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='Studio ground'
m=bpy.data.materials.new('Studio grey');m.diffuse_color=(.24,.25,.26,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.24,.25,.26,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8;floor.data.materials.append(m)
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True;s.render.resolution_x=2000;s.render.resolution_y=850;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Bright studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.6,.65,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for pos,power,size in [((-3,-4,6),1400,5),((4,-1,5),1100,4),((0,3,5),1800,4)]:
 bpy.ops.object.light_add(type='AREA',location=pos);a=bpy.context.object;a.data.energy=power;a.data.size=size;aim(a,(0,0,.5))
bpy.ops.object.camera_add(location=(0,-8,3.8));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=5.9;s.camera=cam;aim(cam,(0,0,.46))
s.view_settings.view_transform='AgX';s.render.filepath=str(P/'collection_preview.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'collection_preview.blend'))
