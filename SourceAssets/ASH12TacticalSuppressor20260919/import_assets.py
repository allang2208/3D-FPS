"""Install the ASH-only suppressor, its PBR regions, wet variants and icon."""
import json
import shutil
from pathlib import Path
import unreal as u

O=Path(__file__).resolve().parent
ROOT=O.parents[1]
D='/Game/Weapons/ASH12/TacticalSuppressor20260919'
A=u.AssetToolsHelpers.get_asset_tools()
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
receipt={'asset_directory':D,'materials':{},'tested':False}


def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Required asset missing: '+path)
    return asset


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):
        raise RuntimeError('Could not save '+asset.get_path_name())


def node(mat,cls,**props):
    result=L.create_material_expression(mat,cls)
    for key,value in props.items():result.set_editor_property(key,value)
    return result


def wire(source,target,pin):
    expression,output=source if isinstance(source,tuple) else (source,'')
    if not L.connect_material_expressions(expression,output,target,pin):
        raise RuntimeError('Material input connection failed: '+pin)


def output(source,prop):
    expression,pin=source if isinstance(source,tuple) else (source,'')
    if not L.connect_material_property(expression,pin,getattr(u.MaterialProperty,'MP_'+prop)):
        raise RuntimeError('Material output connection failed: '+prop)


def custom(mat,code,inputs,size,label):
    expression=node(mat,u.MaterialExpressionCustom,code=code,
        output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)),description=label)
    fields=[]
    for name in inputs:
        entry=u.CustomInput();entry.set_editor_property('input_name',name);fields.append(entry)
    expression.set_editor_property('inputs',fields)
    for name,source in inputs.items():wire(source,expression,name)
    return expression


def import_texture(filename,kind,folder=None):
    task=u.AssetImportTask();task.filename=str(filename);task.destination_name=Path(filename).stem
    task.destination_path=folder or D+'/Textures';task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);texture=load(task.destination_path+'/'+task.destination_name)
    texture.srgb=kind in ('color','icon')
    texture.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else u.TextureCompressionSettings.TC_MASKS if kind=='masks' else u.TextureCompressionSettings.TC_DEFAULT
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI if kind=='icon' else u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='normal':texture.set_editor_property('flip_green_channel',False)
    if kind=='icon':texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    save(texture)
    return texture


textures={}
for part,paths in auth['textures'].items():
    textures[part]={name:import_texture(path,'color' if name=='base_color' else 'normal' if name=='normal' else 'masks') for name,path in paths.items()}

bead_code=(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(encoding='utf-8')


def material(part,wet=False):
    name='M_ASH12_TacticalSuppressor_'+part+('_Wet' if wet else '')
    mat=u.load_asset(D+'/Materials/'+name)
    # This task owns independent names. Reuse completed saved graphs rather
    # than clearing a graph referenced by a mesh in the shared editor.
    if mat:return mat
    mat=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    if part=='Inner':
        output(node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.006,.007,.008,1)),'BASE_COLOR')
        output(node(mat,u.MaterialExpressionConstant,r=.90),'ROUGHNESS')
        output(node(mat,u.MaterialExpressionConstant,r=.05),'METALLIC')
    else:
        def sample(key,sampler):
            return node(mat,u.MaterialExpressionTextureSample,texture=textures[part][key],sampler_type=sampler)
        col=sample('base_color',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        orm=sample('orm',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        normal=sample('normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        color=(col,'RGB');rough=(orm,'G');norm=(normal,'RGB')
        if wet:
            wetness=node(mat,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
            beads=custom(mat,bead_code,{'UV':node(mat,u.MaterialExpressionTextureCoordinate),'Wet':wetness},4,'ASH water beads')
            color=custom(mat,'return Base*(1-Data.a*.055);',{'Base':color,'Data':beads},3,'Thin film color')
            rough=custom(mat,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':rough,'Data':beads},1,'Film and bead roughness')
            norm=custom(mat,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',{'Base':norm,'Data':beads},3,'Beads over surface normal')
        output(color,'BASE_COLOR');output(rough,'ROUGHNESS');output(norm,'NORMAL')
        output((orm,'R'),'AMBIENT_OCCLUSION');output((orm,'B'),'METALLIC')
        output(node(mat,u.MaterialExpressionConstant,r=.5),'SPECULAR')
    L.recompile_material(mat);save(mat)
    return mat


dry={part:material(part) for part in ('Shell','Band','Mount','Inner')}
wet={part:material(part,True) for part in ('Shell','Band','Mount')}
for part,m in dry.items():
    receipt['materials'][part]={'dry':m.get_path_name(),'wet':wet[part].get_path_name() if part in wet else None}

task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=D;task.destination_name=auth['mesh']
task.automated=True;task.replace_existing=True;task.save=False
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_materials=False;options.import_textures=False;options.import_animations=False
data=options.static_mesh_import_data
data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options=options;A.import_asset_tasks([task])
mesh=load(D+'/'+auth['mesh']);slots=mesh.static_materials
for i,slot in enumerate(slots):
    part=str(slot.material_slot_name).removeprefix('ASH12Tac_')
    slot.material_interface=dry[part];slots[i]=slot
mesh.set_editor_property('static_materials',slots)
save(mesh)
receipt['mesh']={'path':mesh.get_path_name(),
    'slots':{str(slot.material_slot_name):slot.material_interface.get_path_name() for slot in mesh.static_materials},
    'source':auth['fbx']}

# Add only this attachment's mappings to ASH's private weather library.
library=load('/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials')
mapping=dict(library.get_editor_property('wet_materials'))
for part,m in wet.items():mapping[dry[part].get_path_name()]=m
library.set_editor_property('wet_materials',mapping);save(library)
receipt['weather_library']=library.get_path_name()

icon_file=Path(auth['icon'])
icon_destination=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/icon_file.name
shutil.copy2(icon_file,icon_destination)
icon=import_texture(icon_file,'icon','/Game/ColdSteelData/AttachmentIcons20260913')
receipt['icon']={'png':str(icon_destination),'texture':icon.get_path_name()}
receipt['exclusive_weapon']='ue_ash12'
receipt['option_id']='ash12_tactical_suppressor'
(O/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ASH12_TACTICAL_SUPPRESSOR_IMPORT_COMPLETE '+json.dumps(receipt,ensure_ascii=False))
