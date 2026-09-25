"""Produce inventory icon PNGs and rigid dropped-item models from the authored equipment."""
import bpy, math
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
ICON=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/Icons/ModularOutfit20260924');ICON.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Body_Equipment.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
shirt=bpy.data.objects['Shirt_Body'];glove=bpy.data.objects['Gloves_Body']
def standalone(obj,name):
    copy=obj.copy();copy.data=obj.data.copy();bpy.context.collection.objects.link(copy)
    copy.name=name;copy.parent=None;copy.matrix_world=Matrix.Identity(4)
    copy.modifiers.clear();copy.vertex_groups.clear()
    return copy
s=standalone(shirt,'SM_FieldSweater_Pickup')
zmid=sum(v.co.z for v in s.data.vertices)/len(s.data.vertices)
for v in s.data.vertices:
    p=v.co.copy();v.co=Vector((p.x,(p.z-zmid),-p.y*.35))
g=standalone(glove,'SM_FieldGloves_Pickup')
frames={}
for side in ('l','r'):
    h=rig.matrix_world@rig.data.bones['hand_'+side].head_local
    forward=(rig.matrix_world@rig.data.bones['middle_03_'+side].head_local-h).normalized()
    across=(rig.matrix_world@rig.data.bones['index_01_'+side].head_local-rig.matrix_world@rig.data.bones['pinky_01_'+side].head_local).normalized()
    normal=across.cross(forward).normalized();across=forward.cross(normal).normalized()
    frames[side]=(h,forward,across,normal)
for v in g.data.vertices:
    side='l' if v.co.x>0 else 'r';h,f,a,n=frames[side];p=v.co-h
    v.co=Vector((p.dot(a)+(.062 if side=='l' else -.062),p.dot(f)-.04,p.dot(n)))
for obj in (s,g):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Exports'/(obj.name+'.fbx')),use_selection=True,
        object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')

for o in list(bpy.data.objects):
    if o not in (s,g):bpy.data.objects.remove(o,do_unlink=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('SoftStudio');scene.world.use_nodes=True
worldnodes=scene.world.node_tree.nodes;worldnodes.clear()
background=worldnodes.new('ShaderNodeBackground');output=worldnodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(background.outputs[0],output.inputs['Surface'])
background.inputs['Color'].default_value=(.25,.28,.34,1)
background.inputs['Strength'].default_value=.5
camdata=bpy.data.cameras.new('ItemCamera');cam=bpy.data.objects.new('ItemCamera',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO'
for name,pos,power,size in [('Key',(-1,-1,2),160,2),('Fill',(1,.2,1.5),90,1.5),('Rim',(0,1,1.2),130,1)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
def material(color,rough):
    m=bpy.data.materials.new('ItemSurface');m.use_nodes=True
    tree=m.node_tree;tree.nodes.clear();p=tree.nodes.new('ShaderNodeBsdfPrincipled');out=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(p.outputs['BSDF'],out.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    noise=tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=220
    bump=tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.0003
    tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m
for name,obj,color,rough in [('ue_field_sweater',s,(.115,.135,.08),.91),('ue_field_sweater_charcoal',s,(.045,.053,.065),.91),('ue_field_gloves',g,(.18,.085,.035),.72),('ue_field_gloves_black',g,(.026,.03,.034),.72)]:
    s.hide_render=obj!=s;g.hide_render=obj!=g
    obj.data.materials.clear();obj.data.materials.append(material(color,rough))
    span=max(max(v.co[i] for v in obj.data.vertices)-min(v.co[i] for v in obj.data.vertices) for i in (0,1))
    cam.location=(span*.12,-span*.20,span*2);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=span*1.22
    scene.render.filepath=str(ICON/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'ItemPresentation.blend'))
print('OUTFIT_ITEM_PRESENTATION_SAVED')
