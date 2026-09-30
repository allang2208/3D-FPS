"""Requested upper-pouch diagnosis using the existing model, no engine launch."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;(O/'Inspection').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False)
src=bpy.data.objects['AmmoBag'];mesh=src.data.copy();obj=bpy.data.objects.new('Current_AmmoBag',mesh)
scene=bpy.data.scenes.new('C45_RequestedInspection');scene.collection.objects.link(obj);bpy.context.window.scene=scene
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
report={'vertices':len(mesh.vertices),'triangles':sum(len(p.vertices)-2 for p in mesh.polygons),'bounds':[[min(v.co[i] for v in mesh.vertices),max(v.co[i] for v in mesh.vertices)] for i in range(3)],'uv_layers':[x.name for x in mesh.uv_layers],'boundary_edges':sum(e.is_boundary for e in bm.edges),'upper_boundary_edges':sum(e.is_boundary and min(v.co.z for v in e.verts)>-.045 for e in bm.edges),'materials':[m.name for m in mesh.materials]}
(O/'Inspection/source.json').write_text(json.dumps(report,indent=2));bm.free()
gray=bpy.data.materials.new('DiagnosticNeutral');gray.diffuse_color=(.38,.38,.38,1);gray.use_nodes=True;bs=next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.38,.38,.38,1);bs.inputs['Roughness'].default_value=.65
original=list(mesh.materials);mesh.materials.clear();mesh.materials.append(gray)
for p in mesh.polygons:p.material_index=0
center=Vector(tuple(sum(x)*.5 for x in report['bounds']));size=.19
cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=size
for name,delta,power in [('Key',(1,-1,2),22),('Fill',(-1,-.7,.6),9),('Rim',(.3,1,1.5),16)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=.3;lamp=bpy.data.objects.new(name,ld);scene.collection.objects.link(lamp);lamp.location=center+Vector(delta)*.3;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('NeutralWorld');scene.world.use_nodes=True;next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.12,.12,.12,1)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=850;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
for name,delta in [('upper',(1,-1,1.4)),('broad',(0,-1,.45)),('top',(0,0,1))]:
    cam.location=center+Vector(delta)*.35;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/'Inspection'/('before_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('C45_SOURCE_READ',json.dumps(report),flush=True)
