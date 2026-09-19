import bpy,json,sys
from pathlib import Path
from mathutils import Vector
p=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
clean='--clean' in sys.argv
bpy.ops.import_scene.gltf(filepath=str(p/('Foregrip_5080_Cleaned.glb' if clean else 'foregrip_raw.glb')))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={o.name:{'verts':len(o.data.vertices),'faces':len(o.data.polygons),'dimensions':list(o.dimensions),'bounds':[list(o.matrix_world@Vector(c)) for c in o.bound_box]} for o in meshes}
(p/('cleaned_inspection.json' if clean else 'raw_inspection.json')).write_text(json.dumps(report,indent=2))
for o in meshes:
 if not clean:
  o.data.materials.clear()
  m=bpy.data.materials.new('Raw Clay');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.18,.20,.23,1);o.data.materials.append(m)
points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
center=sum(points,Vector())/len(points);span=max(max(v[i] for v in points)-min(v[i] for v in points) for i in range(3))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.25,.25,1)
def aim(o):o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=center+Vector((1.5,.5,.4))*span);cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.35;aim(cam);s.camera=cam
for loc,power in [((1,-2,3),500),((-2,-1,1),350),((0,2,2),600)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(loc)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.shape='DISK';o.data.size=span*2;aim(o)
s.render.filepath=str(p/('cleaned_preview.png' if clean else 'raw_preview.png'));bpy.ops.render.render(write_still=True)
