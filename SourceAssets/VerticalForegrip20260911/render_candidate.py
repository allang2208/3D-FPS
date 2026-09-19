import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
files=list(P.glob('*textured*.glb'));assert files,'No generated textured model'
bpy.ops.import_scene.gltf(filepath=str(files[0]))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={o.name:{'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'dimensions':list(o.dimensions),'materials':[m.name for m in o.data.materials if m]} for o in meshes}
(P/'inspection.json').write_text(json.dumps(report,indent=2))
points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box];center=sum(points,Vector())/len(points);span=max(max(v[i] for v in points)-min(v[i] for v in points) for i in range(3))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.20,.23,1)
def aim(o):o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.30;s.camera=cam
for loc,power in [((1,-2,3),550),((-2,-1,1),400),((0,2,2),650)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(loc)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.shape='DISK';o.data.size=span*2;aim(o)
for name,loc in [('beauty',(1.3,-2,.8)),('front',(0,-2,0)),('side',(2,0,0)),('back',(0,2,0))]:
 cam.location=center+Vector(loc)*span;aim(cam);s.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=center+Vector((1.3,-2,.8))*span;aim(cam)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'VerticalForegrip_5080_Editable.blend'))
