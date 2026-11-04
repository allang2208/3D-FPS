"""Author the axe-only long grip from its real factory mating surfaces."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;SA=P.parents[1]
BASE=P.parent/'Textures';SOURCE=P.parent/'ModulesV1/TacticalHatchet_Modules_Editable.blend'
DEST='/Game/Weapons/TacticalHatchet20261101/ModulesV1'
for folder in ['Export','Textures','IconInputs','Icons','Before']:(P/folder).mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(SA/'KukriComponentVariants20261026'))
from asset_tools import *
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
for obj in scene.objects:obj.hide_render=True;obj.hide_set(True)
source=bpy.data.objects['SM_TacticalHatchet_Grip_Factory'].data
EXTENSION=.08;START=-.165;END=-.1875;BOTTOM=-.1925-EXTENSION

def deform(p):
    q=p.copy()
    q.z-=EXTENSION*(1-smooth(END,START,p.z))
    # The upper contact zone and the last 5 mm of the lower joint remain rigid.
    region=smooth(BOTTOM+.005,BOTTOM+.012,q.z)*(1-smooth(START-.008,START,q.z))
    side=smooth(.0045,.0068,abs(p.y))
    ribs=sum(math.exp(-((q.z-z)/.00065)**2) for z in (-.204,-.239))
    q.y-=math.copysign(.00028*region*side*ribs,p.y)
    return q

name='SM_TacticalHatchet_GripLong'
obj=derived_mesh(source,name,deform,levels=0)
unwrap(obj)
m,nt,bs,out=make_mat('Author_Hatchet_GripLong')
tc=node(nt,'ShaderNodeTexCoord');xyz=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],xyz.inputs[0])
x,y,z=xyz.outputs
def ramp(value,a,b):
    n=node(nt,'ShaderNodeMapRange');put(nt,n.inputs['Value'],value)
    n.inputs['From Min'].default_value=a;n.inputs['From Max'].default_value=b
    n.interpolation_type='SMOOTHSTEP';n.clamp=True;return n.outputs['Result']
def noise(scale):
    n=node(nt,'ShaderNodeTexNoise');nt.links.new(tc.outputs['Object'],n.inputs['Vector'])
    n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=2;return n.outputs['Fac']
region=op(nt,'MULTIPLY',ramp(z,BOTTOM+.002,BOTTOM+.008),op(nt,'SUBTRACT',1,ramp(z,START-.012,START)))
side=ramp(op(nt,'ABSOLUTE',y),.0045,.0068)
bands=0.
for height in (-.204,-.239):
    bands=op(nt,'MAXIMUM',bands,op(nt,'SUBTRACT',1,ramp(op(nt,'ABSOLUTE',op(nt,'SUBTRACT',z,height)),.0007,.0015)))
panel=op(nt,'MULTIPLY',side,op(nt,'SUBTRACT',1,bands))
a=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',op(nt,'ADD',x,z),1600)))
b=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',op(nt,'SUBTRACT',x,z),1600)))
checker=op(nt,'POWER',op(nt,'MULTIPLY',a,b),.48)
fine=noise(1700);broad=noise(110)
rubber=mix(nt,checker,(.012,.016,.018,1),(.03,.036,.039,1))
steel=mix(nt,fine,(.065,.071,.077,1),(.115,.122,.13,1))
color=mix(nt,panel,steel,rubber)
rough=mix(nt,panel,(.31,.31,.31,1),(.62,.62,.62,1))
metal=op(nt,'MULTIPLY',.94,op(nt,'SUBTRACT',1,panel))
original=tex(nt,BASE/'source_image_01.png',True,'SourceUV')
oldtex=tex(nt,BASE/'source_image_02.png',False,'SourceUV')
old=node(nt,'ShaderNodeSeparateColor');nt.links.new(oldtex.outputs[0],old.inputs[0])
base=mix(nt,region,original.outputs[0],color)
roughness=mix(nt,region,old.outputs[1],rough)
metallic=mix(nt,region,old.outputs[2],(0,0,0,1))
metallic=op(nt,'ADD',metallic,op(nt,'MULTIPLY',region,metal))
packed=node(nt,'ShaderNodeCombineColor');packed.inputs[0].default_value=1.
put(nt,packed.inputs[1],roughness);put(nt,packed.inputs[2],metallic)
oldnormal=tex(nt,BASE/'source_image_00.png',False,'SourceUV')
nm=node(nt,'ShaderNodeNormalMap',uv_map='SourceUV');nt.links.new(oldnormal.outputs[0],nm.inputs['Color'])
geom=node(nt,'ShaderNodeNewGeometry');normal=mix(nt,region,nm.outputs[0],geom.outputs['Normal'])
bump=node(nt,'ShaderNodeBump');bump.inputs['Distance'].default_value=.00012
put(nt,bump.inputs['Strength'],op(nt,'MULTIPLY',region,panel));put(nt,bump.inputs['Height'],checker);put(nt,bump.inputs['Normal'],normal)
micro=node(nt,'ShaderNodeBump');micro.inputs['Distance'].default_value=.000015
put(nt,micro.inputs['Strength'],region);put(nt,micro.inputs['Height'],fine);nt.links.new(bump.outputs[0],micro.inputs['Normal'])
for socket,value in [('Base Color',base),('Metallic',metallic),('Roughness',roughness),('Normal',micro.outputs[0])]:put(nt,bs.inputs[socket],value)
obj.data.materials.append(m)
scene.render.engine='CYCLES';scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
maps=bake(obj,[(m,{'BaseColor':base,'ORM':packed.outputs[0]},bs,out)],'T_TacticalHatchet_GripLong',P/'Textures',2048)
activate(obj);obj.location=(0,0,0)
fbx=P/'Export'/(name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False,bake_anim=False)
entry={'id':'hatchet_grip_long','name':'长柄握把','slot':'grip','object':name,'mesh':DEST+'/'+name+'.'+name,
       'fbx':str(fbx),'origin_cm':[0,0,11.5],'pommel_offset_cm':[0,0,-8.0],
       'factory_grip_length_cm':19.25,'grip_length_cm':27.25,'extension_cm':8.0,
       'frozen_hand_zone_local_min_z_cm':START*100,'frozen_bottom_interface_length_cm':.5,
       'material_slot':obj.data.materials[0].name,'textures':maps,
       'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
       'stats':{'range_mult':1.25,'physical_damage_mult':1.10,'stamina_mult':1.10,'attack_speed_mult':.95},
       'normal_convention':'OpenGL tangent bake; one UE green-channel flip','runtime_tested':False}
(P/'long_grip.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
obj.location=(0,0,.115)
for key in ['SM_TacticalHatchet_Head_Factory','SM_TacticalHatchet_Pommel_Factory']:
    part=bpy.data.objects[key];part.hide_set(False);part.hide_render=False
bpy.data.objects['SM_TacticalHatchet_Pommel_Factory'].location=(0,0,-.0775-EXTENSION)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_LongGrip_Editable.blend'))
print('HATCHET_LONG_GRIP_AUTHORED extension_cm=8',flush=True)
