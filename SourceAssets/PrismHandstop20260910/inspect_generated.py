import bpy, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
candidate=P.parents[1]/'Saved/Hunyuan3D/Candidates/prism_handstop_v01'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(next(candidate.glob('*.glb'))))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={o.name:{'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'dimensions':list(o.dimensions),'materials':[m.name for m in o.data.materials]} for o in meshes}
report['textures']={m.name:[{'node':n.name,'image':n.image.name,'size':list(n.image.size)} for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] for m in bpy.data.materials if m.use_nodes}
(P/'raw_inspection.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'PrismHandstop_Raw.blend'))
pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)])
center=(lo+hi)/2;span=max(hi-lo)
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.25,.25,1)
def aim(o):o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.25;s.camera=cam
for loc,power in [((1,-2,3),500),((-2,-1,1),350),((0,2,2),600)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(loc)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.size=span*2;aim(o)
for name,loc in [('front',(0,-3,0)),('side',(3,0,0)),('beauty',(2,-3,1)),('back',(0,3,0))]:
 cam.location=center+Vector(loc)*span;aim(cam);s.render.filepath=str(P/('raw_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('PRISM_RAW_INSPECT_PASS')
