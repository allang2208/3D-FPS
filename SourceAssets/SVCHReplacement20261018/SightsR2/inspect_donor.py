import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/HK416SlapSights20261001/HK416_ModularSights_Editable.blend'),load_ui=False)
ob=next(o for o in bpy.context.scene.objects if o.get('HK416_SourceObject')=='ironsight_low')
for o in bpy.context.scene.objects:
 if o.type in ('MESH','ARMATURE'):o.hide_render=o!=ob
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST'
v=np.array([list(ob.matrix_world@x.co) for x in ob.data.vertices]);ob.data.calc_loop_triangles()
report={'object':ob.name,'matrix':list(map(list,ob.matrix_world)),'bounds':[v.min(0).tolist(),v.max(0).tolist()],'materials':[m.name for m in ob.data.materials],'custom_normals':ob.data.has_custom_normals,'vertices':len(v),'triangles':len(ob.data.loop_triangles),'uvs':[u.name for u in ob.data.uv_layers]}
for material in ob.data.materials:
 report['material_nodes']=[{'type':n.type,'image':n.image.filepath if n.type=='TEX_IMAGE' and n.image else None} for n in material.node_tree.nodes]
np.savez(O/'donor_geometry.npz',v=v,t=np.array([t.vertices[:] for t in ob.data.loop_triangles]))
(O/'donor_inventory.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
# Scoped diagnostic rendering requested by the user: actual donor geometry.
mat=bpy.data.materials.new('DiagnosticSteel');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(bs.outputs[0],out.inputs[0]);bs.inputs['Base Color'].default_value=(.16,.18,.20,1);bs.inputs['Metallic'].default_value=.5;bs.inputs['Roughness'].default_value=.35
ob.data.materials.clear();ob.data.materials.append(mat)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=40;sc.cycles.use_denoising=True;sc.render.resolution_x=1300;sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.film_transparent=False
w=bpy.data.worlds.new('DiagnosticWorld');w.use_nodes=True;w.node_tree.nodes.clear();bg=w.node_tree.nodes.new('ShaderNodeBackground');wo=w.node_tree.nodes.new('ShaderNodeOutputWorld');w.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.04,.05,.065,1);bg.inputs[1].default_value=.45;sc.world=w
for name,point,power,size in [('Key',(1.,0.,1.),80,.7),('Fill',(-.8,0.,.5),55,.7)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;light=bpy.data.objects.new(name,d);sc.collection.objects.link(light);light.location=point;light.rotation_euler=(Vector(v.mean(0))-light.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('DiagnosticCamera',bpy.data.cameras.new('DiagnosticCamera'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO'
for label,sel in [('rear',v[:,1]<np.median(v[:,1])),('front',v[:,1]>=np.median(v[:,1]))]:
 a=v[sel];c=Vector((a.min(0)+a.max(0))*.5);cam.location=c+Vector((.12,-.16,.10));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=max(a.max(0)-a.min(0))*1.45;sc.render.filepath=str(O/('donor_'+label+'.png'));bpy.ops.render.render(write_still=True)
