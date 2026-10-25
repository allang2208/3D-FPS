"""Save the approved pommel, 4K PBR and bounded animated internal magic."""
import ast,json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/StarTideCoreV1'
TAG='RuneboundManaOrbOwner';OWNER='StarTideCoreV1_20261024'
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
    return node(mat,u.MaterialExpressionTime),node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneAwake',default_value=0.),node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneImpact',default_value=0.)

def animate_orbit(mat,local,time,seed=None,core=False):
    if core:
        code='float3 q=P-float3(0,0,-8.0); return q*(.08*sin(Age*2.4)+.035*sin(Age*5.3));'
    elif seed is not None:
        code='float3 q=P-float3(0,0,-8.0); float a=Age*(.23+Seed.x*.43); float c=cos(a),s=sin(a); float3 v=float3(c*q.x-s*q.y,s*q.x+c*q.y,q.z); float b=Age*.17; float cb=cos(b),sb=sin(b); v=float3(v.x,cb*v.y-sb*v.z,sb*v.y+cb*v.z); return v-q;'
    else:
        code='float3 q=P-float3(0,0,-8.0); float a=Age*.41; float c=cos(a),s=sin(a); float3 v=float3(c*q.x-s*q.y,s*q.x+c*q.y,q.z); float b=Age*.13; float cb=cos(b),sb=sin(b); return float3(v.x,cb*v.y-sb*v.z,sb*v.y+cb*v.z)-q;'
    inputs={'P':local,'Age':time}
    if seed is not None:inputs['Seed']=seed
    delta=custom(mat,code,inputs)
    transform=node(mat,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(delta,transform,'');L.connect_material_property(transform,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)

textures={}
for suffix in ('BaseColor','ORM','Normal'):
    name='T_StarTide_'+suffix;tex=existing(name)
    if not tex:
        task=u.AssetImportTask();task.filename=str(P/'Textures'/(name+'.png'));task.destination_path=D;task.destination_name=name
        task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(D+'/'+name)
    if not tex:raise RuntimeError('Texture import failed '+name)
    tex.set_editor_property('srgb',suffix=='BaseColor');tex.set_editor_property('max_texture_size',4096)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal' else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('never_stream',False)
    if suffix=='Normal':tex.set_editor_property('flip_green_channel',True)
    textures[suffix]=save(tex)

materials={};m=material('M_StarTide_Metal')
c=node(m,u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
orm=node(m,u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
n=node(m,u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
materials['M_StarTide_Metal']=surface(m,{'basecolor':c,'roughness':(orm,'G'),'metallic':(orm,'B'),'normal':n})

m=material('M_StarTide_Glass');m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
# Broad blue edge tint and a fine rim reveal the spherical glass boundary.
fresnel=node(m,u.MaterialExpressionFresnel,exponent=2.2,base_reflect_fraction=0.)
rim=node(m,u.MaterialExpressionFresnel,exponent=7.,base_reflect_fraction=0.)
opacity=binary(m,u.MaterialExpressionAdd,constant(m,.18),binary(m,u.MaterialExpressionMultiply,fresnel,constant(m,.72)))
edge_glow=binary(m,u.MaterialExpressionAdd,
    binary(m,u.MaterialExpressionMultiply,vector(m,(.006,.13,.42)),binary(m,u.MaterialExpressionMultiply,fresnel,constant(m,.55))),
    binary(m,u.MaterialExpressionMultiply,vector(m,(.14,.50,1.)),binary(m,u.MaterialExpressionMultiply,rim,constant(m,1.65))))
L.connect_material_property(constant(m,1.18),'',u.MaterialProperty.MP_REFRACTION)
materials['M_StarTide_Glass']=surface(m,{'basecolor':vector(m,(.006,.065,.21)),'roughness':constant(m,.10),'metallic':constant(m,0.),'specular':constant(m,.95),'opacity':opacity,'emissivecolor':edge_glow})

m=material('M_RuneboundManaOrb_StarTide_Gem');time,awake,impact=glow_parameters(m)
power=custom(m,'return float3(.003,.12,.55)*(1.+Awake*.9)*(.9+.1*sin(Age*1.9));',{'Age':time,'Awake':awake,'Impact':impact})
materials['M_StarTide_Gem']=surface(m,{'basecolor':vector(m,(.001,.022,.11)),'roughness':constant(m,.09),'metallic':constant(m,.32),'specular':constant(m,.8),'emissivecolor':power})

m=material('M_RuneboundManaOrb_StarTide_Rune');time,awake,impact=glow_parameters(m)
power=custom(m,'return float3(.008,.25,.95)*(1.15+Awake*1.15+Impact*.7)*(.94+.06*sin(Age*1.65));',{'Age':time,'Awake':awake,'Impact':impact})
materials['M_StarTide_Rune']=surface(m,{'basecolor':vector(m,(.002,.025,.10)),'roughness':constant(m,.27),'metallic':constant(m,.12),'emissivecolor':power})

m=material('M_RuneboundManaOrb_StarTide_Volume');m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
# Raymarching runs in the pixel shader. PreSkinnedPosition is vertex-only in
# this project's SM6 material compiler; use the component's local position.
time,awake,impact=glow_parameters(m)
pos=node(m,u.MaterialExpressionLocalPosition,local_origin=u.LocalPositionOrigin.PRIMITIVE,included_offsets=u.PositionIncludedOffsets.EXCLUDE_OFFSETS)
camera=node(m,u.MaterialExpressionCameraPositionWS)
camera_local=node(m,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
wire(camera,camera_local,'')
cloud=custom(m,(P/'nebula.ush').read_text('utf-8'),{'LocalPos':pos,'CameraLocal':camera_local,'Age':time,'Awake':awake,'Impact':impact},True)
rgb=node(m,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);wire(cloud,rgb,'')
alpha=node(m,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);wire(cloud,alpha,'')
materials['M_StarTide_Volume']=surface(m,{'basecolor':vector(m,(0,0,0)),'roughness':constant(m,1),'metallic':constant(m,0),'specular':constant(m,0),'emissivecolor':rgb,'opacity':alpha})

m=material('M_RuneboundManaOrb_StarTide_Core');time,awake,impact=glow_parameters(m);pos=node(m,u.MaterialExpressionPreSkinnedPosition)
animate_orbit(m,pos,time,core=True)
power=custom(m,'float pulse=.88+.12*sin(Age*2.4)+.035*sin(Age*5.3); return float3(.18,.55,1.)*pulse*(3.8+Awake*2.4+Impact*2.);',{'Age':time,'Awake':awake,'Impact':impact})
materials['M_StarTide_Core']=surface(m,{'basecolor':vector(m,(.02,.06,.15)),'roughness':constant(m,.3),'metallic':constant(m,0),'emissivecolor':power})

m=material('M_RuneboundManaOrb_StarTide_Filaments');time,awake,impact=glow_parameters(m);pos=node(m,u.MaterialExpressionPreSkinnedPosition);uv=node(m,u.MaterialExpressionTextureCoordinate)
animate_orbit(m,pos,time)
power=custom(m,'float packet=pow(.5+.5*sin(UV.x*37.6991-Age*3.2),12.); float endFade=smoothstep(0.,.06,UV.x)*smoothstep(0.,.06,1.-UV.x); return (float3(.002,.05,.22)+packet*float3(.12,.55,1.3))*(1.6+Awake+Impact*.7)*endFade;',{'UV':uv,'Age':time,'Awake':awake,'Impact':impact})
materials['M_StarTide_Filaments']=surface(m,{'basecolor':vector(m,(.001,.012,.03)),'roughness':constant(m,.6),'metallic':constant(m,0),'emissivecolor':power})

m=material('M_RuneboundManaOrb_StarTide_Particles');time,awake,impact=glow_parameters(m);pos=node(m,u.MaterialExpressionPreSkinnedPosition);seed=node(m,u.MaterialExpressionVertexColor)
animate_orbit(m,pos,time,seed)
power=custom(m,'float twinkle=pow(.5+.5*sin(Age*(1.3+Seed.x*2.)+Seed.x*31.4),3.); return float3(.07,.32,1.)*(.4+2.8*twinkle)*(1.+Awake*.8+Impact*.6);',{'Age':time,'Awake':awake,'Impact':impact,'Seed':seed})
materials['M_StarTide_Particles']=surface(m,{'basecolor':vector(m,(.001,.01,.03)),'roughness':constant(m,.6),'metallic':constant(m,0),'emissivecolor':power})

# Compile the actual current-RHI shader resources, not only the asset graph.
# This is production shader compilation; it starts no game or acceptance view.
receipt['gpu_compilation']={}
for key,value in materials.items():
    stats=L.get_statistics(value)
    receipt['gpu_compilation'][key]={'vertex_instructions':stats.num_vertex_shader_instructions,'pixel_instructions':stats.num_pixel_shader_instructions}
    record()
    if stats.num_pixel_shader_instructions<=0:
        raise RuntimeError('No compiled pixel shader for '+key+'; use the rendering-enabled SM6 author host')

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
receipt.update(mesh=mesh.get_path_name(),materials=bindings,effect='server active awakening +0.5 seconds per damaging target contact; uncapped',internal_vfx='24-step blue nebula, 4 double-helix currents, 48 contained stars, pulsing core; RuneAwake response; no additional actor tick')
record()
# Icon is a separate production stage so material import does not depend on image generation.
icon='ue_runebound_warhammer_pommel_star_tide_core'
if (P/(icon+'.png')).exists():
    tex=existing(icon)
    if not tex:
        task=u.AssetImportTask();task.filename=str(P/(icon+'.png'));task.destination_path=D;task.destination_name=icon;task.automated=True;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(D+'/'+icon)
    if not tex:raise RuntimeError('Cannot import framed pommel icon')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
    receipt['icon']=tex.get_path_name()
receipt['complete']=True;record();print('STAR_TIDE_ASSETS_SAVED')
