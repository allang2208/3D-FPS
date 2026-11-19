"""Geometry-only working preview while the current-asset export is queued."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from muscle_shape import MuscleShape,neck_seam
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets')
OUT=ROOT/'JasonStrong20261117/R1'
body=json.loads((ROOT/'JasonPlayer20261003/Jason.json').read_text())
layout=json.loads((ROOT/'JasonPlayer20261003/base_fitted.json').read_text())
head=json.loads((ROOT/'JasonPlayer20261003/head_geometry.json').read_text())
triangles=[t for t,m in zip(body['triangles'],layout['triangle_materials']) if m not in (5,6)]
seam=neck_seam({'positions':body['positions'],'triangles':triangles})
shape=MuscleShape(body['bones'],seam_segments=seam)
strong=[shape.deform(p,w) for p,w in zip(body['positions'],body['weights'])]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
s.cycles.device='GPU';s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.18,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.4
mat=bpy.data.materials.new('Clay');mat.use_nodes=True;mat.node_tree.nodes.clear();bs=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(bs.outputs[0],out.inputs['Surface']);bs.inputs['Base Color'].default_value=(.42,.42,.42,1);bs.inputs['Roughness'].default_value=.6
for name,positions,ts,x in [('Original',body['positions'],triangles,.68),('Strong',strong,triangles,-.68),('OriginalFace',head['positions'],head['triangles'],.68),('StrongFace',head['positions'],head['triangles'],-.68)]:
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([[v*.01 for v in p] for p in positions],[],ts);mesh.update();ob=bpy.data.objects.new(name,mesh);s.collection.objects.link(ob);ob.location.x=x;mesh.materials.append(mat)
    for f in mesh.polygons:f.use_smooth=True
for name,point,power in [('Key',(-3,4,4),650),('Fill',(3,2,2.8),420),('Rim',(0,-3,3.5),800)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=3
    ob=bpy.data.objects.new(name,light);s.collection.objects.link(ob);ob.location=point;ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=2.8;cam.location=(0,6,1.);cam.rotation_euler=(Vector((0,0,.88))-cam.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(OUT/'shape_draft.png');bpy.ops.render.render(write_still=True)
