"""Author the canine blade in the existing grip frame; bake PBR and icon input."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

P=Path(__file__).resolve().parent
SOURCE=P.parent/'KukriBladeSurfaceV220261026/Kukri_Blade_SurfaceV2_Editable.blend'
sys.path.insert(0,str(P.parent/'KukriComponentVariants20261026'))
from asset_tools import node, put, op, mix, make_mat, bake, export, smooth
for folder in ('Textures','Export','Icons','Before'):(P/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
with bpy.data.libraries.load(str(SOURCE),link=False) as (available,loaded):
    loaded.objects=['SM_Kukri_Blade_FoldedBalanced']
blade=loaded.objects[0];scene.collection.objects.link(blade)
blade.name='SM_Kukri_Blade_Canine';blade.matrix_world=Matrix.Identity(4)
mesh=blade.data;mesh.name='SM_Kukri_Blade_Canine'
root=.066
original_tip=max(v.co.z for v in mesh.vertices)
sys.path.insert(0,str(P))
from serrate_mesh import serrate
serrations=serrate(blade)
mesh=blade.data

mat,nt,bs,out=make_mat('Author_Canine_SatinSteel')
field=node(nt,'ShaderNodeVertexColor',layer_name='SurfaceField')
sep=node(nt,'ShaderNodeSeparateColor');nt.links.new(field.outputs['Color'],sep.inputs[0])
edge=sep.outputs[1]
coord=node(nt,'ShaderNodeTexCoord')
scale=node(nt,'ShaderNodeVectorMath',operation='MULTIPLY')
nt.links.new(coord.outputs['Object'],scale.inputs[0]);scale.inputs[1].default_value=(3800,2600,95)
grain=node(nt,'ShaderNodeTexNoise');grain.inputs['Scale'].default_value=1;grain.inputs['Detail'].default_value=2
nt.links.new(scale.outputs[0],grain.inputs['Vector'])
body=mix(nt,grain.outputs['Fac'],(.17,.18,.19,1),(.21,.22,.23,1))
color=mix(nt,edge,body,(.44,.455,.47,1))
rough=mix(nt,edge,op(nt,'ADD',.31,op(nt,'MULTIPLY',grain.outputs['Fac'],.055)),(.22,.22,.22,1))
packed=node(nt,'ShaderNodeCombineColor');packed.inputs[0].default_value=1
put(nt,packed.inputs[1],rough);packed.inputs[2].default_value=.98
height=op(nt,'MULTIPLY',grain.outputs['Fac'],.000006)
bump=node(nt,'ShaderNodeBump');bump.inputs['Distance'].default_value=1;bump.inputs['Strength'].default_value=.6
nt.links.new(height,bump.inputs['Height'])
for socket,value in [('Base Color',color),('Roughness',rough),('Metallic',.98),('Normal',bump.outputs[0])]:put(nt,bs.inputs[socket],value)
mesh.materials.clear();mesh.materials.append(mat)
for poly in mesh.polygons:poly.material_index=0
maps=bake(blade,[(mat,{'BaseColor':color,'ORM':packed.outputs[0]},bs,out)],'T_Kukri_Canine',P/'Textures',2048)
blade.data.materials[0].name='M_Kukri_Canine'
fbx=P/'Export/SM_Kukri_Blade_Canine.fbx';export(blade,fbx)
pts=[v.co for v in mesh.vertices]
bounds=[[min(v[i] for v in pts),max(v[i] for v in pts)] for i in range(3)]
entry={'id':'canine_blade','name':'犬牙刀身','kind':'Canine','object':blade.name,
       'source':str(SOURCE),'blend':str(P/'Kukri_Canine_Editable.blend'),'fbx':str(fbx),'textures':maps,
       'root_fixed_through_cm':root*100,'exposed_length_scale':1.0,'serrations':serrations,
       'original_exposed_length_cm':(original_tip-root)*100,'exposed_length_cm':(bounds[2][1]-root)*100,
       'bounds':bounds,'trace_base_cm':[.6,0,8.],'trace_tip_cm':[6.18,0,.2629*100],
       'material_slot':'M_Kukri_Canine','icon_key':'ue_kukri_blade_1_canine_blade'}
(P/'canine.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'blade-layout-source.json').write_text(json.dumps([{'kind':'Canine','blend':entry['blend'],
    'object':blade.name,'bounds':bounds}],indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=entry['blend'])
print('CANINE_MODEL_AND_PBR_SAVED',flush=True)

# This is production source imagery for the requested menu icon, not an in-game test.
blade.rotation_euler=(0,-math.pi/2,0)
bpy.context.view_layer.update()
corners=[blade.matrix_world@Vector(v) for v in blade.bound_box]
center=sum(corners,Vector())/len(corners);blade.location-=center
width=max(v.x for v in corners)-min(v.x for v in corners)
bpy.ops.object.camera_add(location=(0,-1,0));camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=width/0.78;scene.camera=camera
world=bpy.data.worlds.new('CanineIconStudio');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.3,.3,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,location,energy,size in [('Key',(-.25,-.4,.45),32,.55),('Fill',(.35,-.25,.1),10,.4),('Edge',(.1,.25,.35),20,.35)]:
    bpy.ops.object.light_add(type='AREA',location=location);light=bpy.context.object;light.name=name
    light.data.energy=energy;light.data.shape='DISK';light.data.size=size
    light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.filepath=str(P/'Icons/Canine_Model_Reference.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Canine_IconSource.blend'))
print('CANINE_ICON_REFERENCE_SAVED',flush=True)
