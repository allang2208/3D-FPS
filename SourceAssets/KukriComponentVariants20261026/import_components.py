"""Import/save only this batch's meshes, baked materials, and shared menu icons."""
import json,sys
from pathlib import Path
import unreal as u

P=Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\KukriComponentVariants20261026\import_components.py').resolve().parent
data=json.loads((P/'components.json').read_text(encoding='utf-8'))
sys.path.insert(0,str(P.parent/'KukriAssetRepair20261026'))
from kukri_mesh_import import import_mesh,require_authoring_context
require_authoring_context()
A=u.AssetToolsHelpers.get_asset_tools()
E=u.MaterialEditingLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
ROOT='/Game/Weapons/Kukri20261020/ComponentVariants20261026'
ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
receipt={'complete':False,'saved_assets':[],'runtime_tested':False,'stats_authored':False}

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return asset

def import_asset(filename,folder,name,options=None):
    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed '+folder+'/'+name)
    return asset

def node(mat,cls,**properties):
    n=E.create_material_expression(mat,cls)
    for key,value in properties.items():n.set_editor_property(key,value)
    return n

for entry in data['variants']:
    factory_name={'grip':'Grip','pommel':'Pommel','lanyard':'Lanyard'}[entry['slot']]
    template=u.load_asset('/Game/Weapons/Kukri20261020/Modules20261026/SM_Kukri_'+factory_name+'_Factory')
    if not template:raise RuntimeError('Factory component template missing')
    maps={}
    for suffix,filename in entry['textures'].items():
        tex=import_asset(filename,ROOT+'/Textures',Path(filename).stem)
        tex.set_editor_property('srgb',suffix=='BaseColor')
        tex.set_editor_property('compression_settings',{'BaseColor':u.TextureCompressionSettings.TC_BC7,
            'ORM':u.TextureCompressionSettings.TC_MASKS,'Normal':u.TextureCompressionSettings.TC_NORMALMAP}[suffix])
        tex.set_editor_property('lod_group',{'BaseColor':u.TextureGroup.TEXTUREGROUP_WEAPON,
            'ORM':u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,'Normal':u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP}[suffix])
        tex.set_editor_property('never_stream',False)
        tex.set_editor_property('max_texture_size',2048)
        # Blender tangent normal bake is +Y; Unreal expects DirectX -Y.
        if suffix=='Normal':tex.set_editor_property('flip_green_channel',True)
        maps[suffix]=save(tex)
    name='M_Kukri_'+entry['kind']
    mat=u.load_asset(ROOT+'/Materials/'+name) or A.create_asset(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    E.delete_all_material_expressions(mat)
    mat.set_editor_property('use_material_attributes',False)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('two_sided',False)
    base=node(mat,u.MaterialExpressionTextureSample,texture=maps['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm=node(mat,u.MaterialExpressionTextureSample,texture=maps['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    normal=node(mat,u.MaterialExpressionTextureSample,texture=maps['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    slab=node(mat,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for source,pin,prop,target in [(base,'RGB',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),
            (normal,'RGB',u.MaterialProperty.MP_NORMAL,'Normal'),(orm,'G',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),
            (orm,'B',u.MaterialProperty.MP_METALLIC,'Metallic'),(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION,None)]:
        if target and not E.connect_material_expressions(source,pin,slab,target):raise RuntimeError('Material pin '+target)
        if not E.connect_material_property(source,pin,prop):raise RuntimeError('Material output '+str(prop))
    if not E.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('FrontMaterial connection')
    E.layout_material_expressions(mat);E.recompile_material(mat)
    u.EditorAssetLibrary.set_metadata_tag(mat,'Kukri.CosmeticVariant',entry['id']);save(mat)
    mesh=import_mesh(entry['fbx'],ROOT+'/'+entry['object'],mat)
    u.EditorAssetLibrary.set_metadata_tag(mesh,'Kukri.CosmeticVariant',entry['id'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'Kukri.Source',str(P/'Kukri_Blade_Variants_Editable.blend'))
    save(mesh)
    icon=import_asset(entry['icon'],ICONS,entry['icon_key'])
    icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True)
    icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    icon.set_editor_property('max_texture_size',1024);save(icon)
    u.log('KUKRI_VARIANT_SAVED '+entry['id'])
import runpy
rune_result=runpy.run_path(str(P/'import_runes.py'),run_name='__main__')
receipt['saved_assets']+=rune_result['receipt']['saved_assets']
receipt['root_materials']=rune_result['receipt']['root_materials']
receipt['rune_surfaces']=rune_result['receipt']['rune_surfaces']
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('KUKRI_VARIANTS_IMPORT_COMPLETE '+str(len(receipt['saved_assets'])))
