"""Save the approved pommel, 4K PBR and bounded animated internal magic."""
import ast,json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/ManaOrbPommelV2'
TAG='RuneboundManaOrbOwner';OWNER='ManaOrbPommelV2_20261024'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'complete':False,'assets':[],'tested':False,'editor_ui_started':False}
tree=ast.parse((P.parent/'RuneAndBellRefinement20261024/install_assets.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<material_authoring>','exec'))
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Use the FPSGAME asset host')
record()

_new_material=material
def material(name):
    result=_new_material(name)
    result.set_editor_property('used_with_nanite',False)
    return result

def custom(mat,code,inputs,four=False):
    expr=node(mat,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4 if four else u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    expr.set_editor_property('inputs',pins)
    for key,value in inputs.items():
        source,output=value if isinstance(value,tuple) else (value,'')
        wire(source,expr,key,output)
    return expr

def glow_parameters(mat):
    return node(mat,u.MaterialExpressionTime),node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneAwake',default_value=0.)

def animate_orbit(mat,local,time,seed=None,core=False):
    if core:
        code='float3 q=P-float3(0,0,-8.7); return q*(.08*sin(Age*2.4)+.035*sin(Age*5.3));'
    elif seed is not None:
        code='float3 q=P-float3(0,0,-8.7); float a=Age*(.23+Seed.x*.43); float c=cos(a),s=sin(a); float3 v=float3(c*q.x-s*q.y,s*q.x+c*q.y,q.z); float b=Age*.17; float cb=cos(b),sb=sin(b); v=float3(v.x,cb*v.y-sb*v.z,sb*v.y+cb*v.z); return v-q;'
    else:
        code='float3 q=P-float3(0,0,-8.7); float a=Age*.41; float c=cos(a),s=sin(a); float3 v=float3(c*q.x-s*q.y,s*q.x+c*q.y,q.z); float b=Age*.13; float cb=cos(b),sb=sin(b); return float3(v.x,cb*v.y-sb*v.z,sb*v.y+cb*v.z)-q;'
    inputs={'P':local,'Age':time}
    if seed is not None:inputs['Seed']=seed
    delta=custom(mat,code,inputs)
    transform=node(mat,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(delta,transform,'');L.connect_material_property(transform,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)

textures={}
for suffix in ('BaseColor','ORM','Normal'):
    name='T_ManaOrbV2_'+suffix;tex=existing(name)
    if not tex:
        task=u.AssetImportTask();task.filename=str(P/'Textures'/(name+'.png'));task.destination_path=D;task.destination_name=name
        task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(D+'/'+name)
    if not tex:raise RuntimeError('Texture import failed '+name)
    tex.set_editor_property('srgb',suffix=='BaseColor');tex.set_editor_property('max_texture_size',4096)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal' else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('never_stream',False)
    if suffix=='Normal':tex.set_editor_property('flip_green_channel',True)
    textures[suffix]=save(tex)

materials={};m=material('M_ManaOrbV2_Metal')
c=node(m,u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
orm=node(m,u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
n=node(m,u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
materials['M_ManaOrbV2_Metal']=surface(m,{'basecolor':c,'roughness':(orm,'G'),'metallic':(orm,'B'),'normal':n})

m=material('M_ManaOrbV2_Glass');m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
# A broad tinted shoulder and a thin luminous rim keep the crystal silhouette
# readable even when the display scene supplies no useful glass reflections.
fresnel=node(m,u.MaterialExpressionFresnel,exponent=2.2,base_reflect_fraction=0.)
rim=node(m,u.MaterialExpressionFresnel,exponent=7.,base_reflect_fraction=0.)
opacity=binary(m,u.MaterialExpressionAdd,constant(m,.18),binary(m,u.MaterialExpressionMultiply,fresnel,constant(m,.72)))
edge_glow=binary(m,u.MaterialExpressionAdd,
    binary(m,u.MaterialExpressionMultiply,vector(m,(.24,.055,.60)),binary(m,u.MaterialExpressionMultiply,fresnel,constant(m,.55))),
    binary(m,u.MaterialExpressionMultiply,vector(m,(.55,.22,1.)),binary(m,u.MaterialExpressionMultiply,rim,constant(m,1.65))))
L.connect_material_property(constant(m,1.18),'',u.MaterialProperty.MP_REFRACTION)
materials['M_ManaOrbV2_Glass']=surface(m,{'basecolor':vector(m,(.085,.015,.22)),'roughness':constant(m,.10),'metallic':constant(m,0.),'specular':constant(m,.95),'opacity':opacity,'emissivecolor':edge_glow})

m=material('M_RuneboundManaOrb_GemV2');time,awake=glow_parameters(m)
power=custom(m,'return float3(.10,.004,.28)*(1.+Awake*.9)*(.9+.1*sin(Age*1.9));',{'Age':time,'Awake':awake})
materials['M_ManaOrbV2_Gem']=surface(m,{'basecolor':vector(m,(.065,.002,.18)),'roughness':constant(m,.09),'metallic':constant(m,.32),'specular':constant(m,.8),'emissivecolor':power})

m=material('M_RuneboundManaOrb_RuneV2');time,awake=glow_parameters(m)
power=custom(m,'return float3(.32,.012,.86)*(1.15+Awake*1.15)*(.94+.06*sin(Age*1.65));',{'Age':time,'Awake':awake})
materials['M_ManaOrbV2_Rune']=surface(m,{'basecolor':vector(m,(.06,.002,.18)),'roughness':constant(m,.27),'metallic':constant(m,.12),'emissivecolor':power})

m=material('M_RuneboundManaOrb_VolumeV2');m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
# Raymarching runs in the pixel shader. PreSkinnedPosition is vertex-only in
# this project's SM6 material compiler; use the component's local position.
time,awake=glow_parameters(m)
pos=node(m,u.MaterialExpressionLocalPosition,local_origin=u.LocalPositionOrigin.PRIMITIVE,included_offsets=u.PositionIncludedOffsets.EXCLUDE_OFFSETS)
camera=node(m,u.MaterialExpressionCameraPositionWS)
camera_local=node(m,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
wire(camera,camera_local,'')
cloud=custom(m,(P/'nebula.ush').read_text('utf-8'),{'LocalPos':pos,'CameraLocal':camera_local,'Age':time,'Awake':awake},True)
rgb=node(m,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);wire(cloud,rgb,'')
alpha=node(m,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);wire(cloud,alpha,'')
materials['M_ManaOrbV2_Volume']=surface(m,{'basecolor':vector(m,(0,0,0)),'roughness':constant(m,1),'metallic':constant(m,0),'specular':constant(m,0),'emissivecolor':rgb,'opacity':alpha})

m=material('M_RuneboundManaOrb_CoreV2');time,awake=glow_parameters(m);pos=node(m,u.MaterialExpressionPreSkinnedPosition)
animate_orbit(m,pos,time,core=True)
power=custom(m,'float pulse=.88+.12*sin(Age*2.4)+.035*sin(Age*5.3); return float3(.65,.24,1.)*pulse*(3.8+Awake*2.4);',{'Age':time,'Awake':awake})
materials['M_ManaOrbV2_Core']=surface(m,{'basecolor':vector(m,(.15,.025,.3)),'roughness':constant(m,.3),'metallic':constant(m,0),'emissivecolor':power})

m=material('M_RuneboundManaOrb_FilamentsV2');time,awake=glow_parameters(m);pos=node(m,u.MaterialExpressionPreSkinnedPosition);uv=node(m,u.MaterialExpressionTextureCoordinate)
animate_orbit(m,pos,time)
power=custom(m,'float packet=pow(.5+.5*sin(UV.x*37.6991-Age*3.2),12.); float endFade=smoothstep(0.,.06,UV.x)*smoothstep(0.,.06,1.-UV.x); return (float3(.12,.003,.4)+packet*float3(.65,.17,1.1))*(1.6+Awake)*endFade;',{'UV':uv,'Age':time,'Awake':awake})
materials['M_ManaOrbV2_Filaments']=surface(m,{'basecolor':vector(m,(.02,0,.05)),'roughness':constant(m,.6),'metallic':constant(m,0),'emissivecolor':power})

m=material('M_RuneboundManaOrb_ParticlesV2');time,awake=glow_parameters(m);pos=node(m,u.MaterialExpressionPreSkinnedPosition);seed=node(m,u.MaterialExpressionVertexColor)
animate_orbit(m,pos,time,seed)
power=custom(m,'float twinkle=pow(.5+.5*sin(Age*(1.3+Seed.x*2.)+Seed.x*31.4),3.); return float3(.48,.075,1.)*(.4+2.8*twinkle)*(1.+Awake*.8);',{'Age':time,'Awake':awake,'Seed':seed})
materials['M_ManaOrbV2_Particles']=surface(m,{'basecolor':vector(m,(.03,.001,.08)),'roughness':constant(m,.6),'metallic':constant(m,0),'emissivecolor':power})

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
prod=json.loads((P/'production_receipt.json').read_text('utf-8'));name=prod['mesh'];mesh=existing(name)
if not mesh:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.generate_lightmap_u_vs=False
    opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=prod['fbx'];task.destination_path=D;task.destination_name=name;task.automated=True;task.save=False;task.options=opt
    A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
if not mesh:raise RuntimeError('Cannot import mana-orb pommel')
bindings={}
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    raw=str(slot.material_slot_name);key=re.sub(r'(?:[._]\d{3})+$','',raw)
    mesh.set_material(i,materials[key]);bindings[raw]=materials[key].get_path_name()
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite)
save(mesh)
receipt.update(mesh=mesh.get_path_name(),materials=bindings,effect='server awakening duration +10 seconds',internal_vfx='24-step local nebula, 5 orbiting solid filaments, 32 solid sparks, pulsing core; RuneAwake response; no additional actor tick')
record()
# Icon is a separate production stage so material import does not depend on image generation.
icon='ue_runebound_warhammer_pommel_empowered_mana_orb'
if (P/(icon+'.png')).exists():
    tex=existing(icon)
    if not tex:
        task=u.AssetImportTask();task.filename=str(P/(icon+'.png'));task.destination_path=D;task.destination_name=icon;task.automated=True;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(D+'/'+icon)
    if not tex:raise RuntimeError('Cannot import framed pommel icon')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
    receipt['icon']=tex.get_path_name()
receipt['complete']=True;record();print('MANA_ORB_V2_ASSETS_SAVED')
