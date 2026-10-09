import bpy,math
from mathutils import Vector
from pathlib import Path
O=Path(r'D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006');P=O.parents[1];out=P/'Content/ColdSteelData/Icons/Super90Source20261006';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'Super90_Gameplay_Editable.blend'));s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=512;s.render.resolution_y=512;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
r=bpy.data.objects['SK_Super90'];r.animation_data.action=None
from mathutils import Matrix
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
for ob in s.objects:
 if ob.type=='MESH':ob.hide_render=True
world=bpy.data.worlds.new('Super90_IconStudio');s.world=world;world.use_nodes=True;bg=next((n for n in world.node_tree.nodes if n.type=='BACKGROUND'),None) or world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs[0].default_value=(.45,.45,.45,1);bg.inputs[1].default_value=.5;wo=next((n for n in world.node_tree.nodes if n.type=='OUTPUT_WORLD'),None) or world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs[0])
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO'
lights=[]
for pos,power,size in [((1.8,-1.5,2),250,2),((-1,1,1.5),350,2),((0,2,.4),150,1)]:
 bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;lights.append(l)
def render(name,obs,direction,filepath):
 for ob in s.objects:
  if ob.type=='MESH':ob.hide_render=ob not in obs
 bpy.context.view_layer.update();coords=[ob.matrix_world@Vector(c) for ob in obs for c in ob.bound_box];lo=Vector([min(p[i] for p in coords) for i in range(3)]);hi=Vector([max(p[i] for p in coords) for i in range(3)]);center=(lo+hi)/2;extent=max(hi-lo)
 cam.location=center+Vector(direction).normalized()*max(1,extent*3);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=extent*1.22
 for l in lights:l.rotation_euler=(center-l.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(filepath);bpy.ops.render.render(write_still=True)
render('gun',[o for o in s.objects if o.name in ['Super90_body','Super90_bolt','Super90_loading_gate','Super90_trigger']],(1,-.12,.42),P/'Content/ColdSteelData/Icons/ue_super90.png')
render('gloves',[bpy.data.objects['SM_ue_hardknuckle_gloves']],(.4,-1,.7),out/'ue_hardknuckle_gloves.png')
render('sleeves',[bpy.data.objects['SM_ue_st6_sleeves']],(.4,-1,.7),out/'ue_st6_sleeves.png')
render('shell',[bpy.data.objects['SM_Super90_Casing']],(.8,-1,.6),out/'ammo_12g.png')
print('SUPER90_CATALOG_ICONS_SAVED',flush=True)
