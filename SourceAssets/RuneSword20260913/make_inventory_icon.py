"""Produce the inventory icon asset, not an acceptance preview."""
import bpy,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'Export/SM_AzureRunesword.fbx'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48
obj=next(o for o in s.objects if o.type=='MESH')
mat=bpy.data.materials.new('RuneSwordIconMaterial');mat.use_nodes=True;obj.data.materials.clear();obj.data.materials.append(mat)
nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');source=next((P/'Original').rglob('*.fbx'))
for suffix,socket in [('', 'Base Color'),('_metallic','Metallic'),('_roughness','Roughness'),('_normal','Normal'),('_emission','Emission Color')]:
    im=bpy.data.images.load(str(source.with_name(source.stem+suffix+'.png')));im.colorspace_settings.name='sRGB' if suffix in ['', '_emission'] else 'Non-Color'
    n=nt.nodes.new('ShaderNodeTexImage');n.image=im
    if suffix=='_normal':
        normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(n.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],bs.inputs[socket])
    else:nt.links.new(n.outputs['Color'],bs.inputs[socket])
bs.inputs['Emission Strength'].default_value=3.5
points=[obj.matrix_world@Vector(c) for c in obj.bound_box];center=sum(points,Vector())/8
camdata=bpy.data.cameras.new('InventoryIconCamera');cam=bpy.data.objects.new('InventoryIconCamera',camdata);s.collection.objects.link(cam);s.camera=cam
cam.location=center+Vector((.22,-3,.06));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=1.56
for name,loc,power,size in [('Key',(-2,-3,3),550,3),('Fill',(2,-2,.4),300,2),('Rim',(-1,2,2),800,2)]:
    ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);s.collection.objects.link(lo);lo.location=loc;lo.rotation_euler=(center-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.shape='DISK';ld.size=size
s.world=bpy.data.worlds.new('InventoryIconWorld');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.16,.21,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.6
s.render.resolution_x=384;s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.film_transparent=True
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='AgX'
s.render.filepath=str(P.parents[1]/'Content/ColdSteelData/Icons/ue_rune_sword.png');bpy.ops.render.render(write_still=True)
