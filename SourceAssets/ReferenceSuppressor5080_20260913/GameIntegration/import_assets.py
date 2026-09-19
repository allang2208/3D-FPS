"""Import tactical suppressor meshes/materials at independent paths; no PIE or audits."""
import unreal as u
import json
from pathlib import Path

O=Path(__file__).resolve().parent
D='/Game/Weapons/TacticalSuppressor20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text())

def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Required source asset missing: '+path)
    return asset

def save(asset):
    if not E.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Unable to save '+asset.get_path_name())

def node(m,cls,**properties):
    result=L.create_material_expression(m,cls)
    for k,v in properties.items():result.set_editor_property(k,v)
    return result

def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection: '+pin)

def output(a,out,prop):
    if not L.connect_material_property(a,out,prop):raise RuntimeError('Material output: '+str(prop))

def texture(file,kind):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=D+'/Textures';task.destination_name=Path(file).stem
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    asset=load(task.destination_path+'/'+task.destination_name)
    asset.srgb=kind=='color'
    asset.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else u.TextureCompressionSettings.TC_DEFAULT if kind=='color' else u.TextureCompressionSettings.TC_MASKS
    asset.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='normal':asset.set_editor_property('flip_green_channel',True)
    else:
        asset.set_editor_property('address_x',u.TextureAddress.TA_MIRROR);asset.set_editor_property('address_y',u.TextureAddress.TA_MIRROR)
    save(asset);return asset

normal=texture(O/'Textures/T_TacticalSuppressor_Normal.png','normal')
maps={
    'M4':{k:load('/Game/Weapons/AttachmentFinish20260913/M4/Textures/T_M4_Receiver_'+k) for k in ['BaseColor','Roughness']},
    'AKM':{k:load('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_'+suffix) for k,suffix in [('BaseColor','Base_color'),('Metallic','Metallic'),('Roughness','Roughness')]},
    'M1911':{k:load('/Game/Weapons/M1911/Attachments20260913/Textures/T_M1911_Attachment_'+k) for k in ['BaseColor','ORM']},
    'QBZ191':{k:texture(O/'Textures'/('T_TacticalSuppressor_QBZ191_'+k+'.png'),'color' if k=='BaseColor' else 'masks') for k in ['BaseColor','ORM']}}
refs={
    'M4':'/Game/Weapons/M4InfimaV3/Body_001',
    'AKM':'/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR',
    'QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/Materials/M_QBZ191_Unified_M_QBZ191_Wear_Body_metal',
    'M1911':'M1911Hero20260913 accepted blued slide coating / M1911Attachments20260913'}

def make_material(family,part):
    name='M_TacticalSuppressor_'+part
    folder=D+'/'+family
    m=u.load_asset(folder+'/'+name)
    if m is None:m=A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    if part=='Recess':
        c=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.006,.007,.009,1));output(c,'',u.MaterialProperty.MP_BASE_COLOR)
        output(node(m,u.MaterialExpressionConstant,r=.82),'',u.MaterialProperty.MP_ROUGHNESS)
        output(node(m,u.MaterialExpressionConstant,r=.08),'',u.MaterialProperty.MP_METALLIC)
    else:
        uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
        samples={}
        for key,tex in maps[family].items():
            sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if family=='M4' or key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE if family=='AKM' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
            sample=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler);link(uv,'',sample,'UVs');samples[key]=sample
        if family=='M4':
            fn=node(m,u.MaterialExpressionMaterialFunctionCall,material_function=load('/InterchangeAssets/Functions/MF_PhongToMetalRoughness'))
            link(samples['BaseColor'],'RGB',fn,'DiffuseColor');link(samples['Roughness'],'R',fn,'Shininess')
            link(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.2,.2,.2,1)),'',fn,'SpecularColor')
            link(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,1)),'',fn,'AmbientColor')
            for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(u.MaterialProperty.MP_METALLIC,'Metallic'),(u.MaterialProperty.MP_SPECULAR,'Specular')]:output(fn,out,prop)
        else:
            output(samples['BaseColor'],'RGB',u.MaterialProperty.MP_BASE_COLOR)
            output(samples['Roughness'] if family=='AKM' else samples['ORM'],'R' if family=='AKM' else 'G',u.MaterialProperty.MP_ROUGHNESS)
            output(samples['Metallic'] if family=='AKM' else samples['ORM'],'R' if family=='AKM' else 'B',u.MaterialProperty.MP_METALLIC)
    if part!='Mount':
        uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
        sample=node(m,u.MaterialExpressionTextureSample,texture=normal,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        link(uv,'',sample,'UVs');output(sample,'RGB',u.MaterialProperty.MP_NORMAL)
    E.set_metadata_tag(m,'WeaponFinishReference',refs[family]);E.set_metadata_tag(m,'StructureNormalUV','0')
    L.recompile_material(m);save(m);return m

report={}
for family,info in auth.items():
    materials={part:make_material(family,part) for part in ['Shell','Recess','Mount']}
    folder=D+'/'+family
    task=u.AssetImportTask();task.filename=info['fbx'];task.destination_path=folder;task.destination_name='SM_TacticalSuppressor'
    task.automated=True;task.replace_existing=True;task.save=False
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;task.options=opt
    A.import_asset_tasks([task]);mesh=load(folder+'/SM_TacticalSuppressor')
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        label=str(slot.material_slot_name)
        part='Recess' if 'Recess' in label else 'Mount' if 'Mount' in label else 'Shell'
        slot.material_interface=materials[part];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'DisplayName','战术消音器')
    E.set_metadata_tag(mesh,'GunsmithOptionId','tactical_suppressor')
    E.set_metadata_tag(mesh,'SourceModel',str(O.parent/'KnurlRefinedV1/Suppressor_KnurlRefinedV1.blend'))
    E.set_metadata_tag(mesh,'WeaponFinishReference',refs[family]);save(mesh)
    report[family]={'mesh':mesh.get_path_name(),'materials':{k:v.get_path_name() for k,v in materials.items()},'source_fbx':info['fbx'],'normal_uv':0,'coating_uv':1}
    (O/'import_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.log('TACTICAL_SUPPRESSOR_IMPORTED '+family)
u.log('TACTICAL_SUPPRESSOR_IMPORT_COMPLETE')
