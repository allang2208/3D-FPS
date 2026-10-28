"""Save only the new Canine mesh, PBR, rune adapters and menu icon."""
import json, sys
from pathlib import Path
import unreal as u

P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriCanineBlade20261027')
ROOT='/Game/Weapons/Kukri20261020/CanineBlade20261027'
SOURCE='/Game/Weapons/Kukri20261020/BladeVariants20261026'
RUNE_SOURCE='/Game/Weapons/Kukri20261020/ComponentVariants20261026/Runes'
sys.path.insert(0,str(P.parent/'KukriAssetRepair20261026'))
from kukri_mesh_import import import_mesh, require_authoring_context
require_authoring_context()
entry=json.loads((P/'canine.json').read_text(encoding='utf-8'))
runes=json.loads((P/'runes.json').read_text(encoding='utf-8'))['runes']
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
receipt={'complete':False,'saved_assets':[],'rune_surfaces':{},'runtime_tested':False}

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    (P/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return asset

def texture(filename,folder,channel,name=None):
    name=name or Path(filename).stem
    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=folder;task.destination_name=name
    task.factory=u.TextureFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not task.imported_object_paths or not asset:raise RuntimeError('Texture import failed: '+name)
    icon=channel=='Icon'
    asset.set_editor_properties({'srgb':channel in ('BaseColor','Icon'),
        'compression_settings':{'BaseColor':u.TextureCompressionSettings.TC_BC7,'ORM':u.TextureCompressionSettings.TC_MASKS,
            'Mask':u.TextureCompressionSettings.TC_MASKS,'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'Icon':u.TextureCompressionSettings.TC_EDITOR_ICON}[channel],
        'lod_group':{'BaseColor':u.TextureGroup.TEXTUREGROUP_WEAPON,'ORM':u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,
            'Mask':u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,'Normal':u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP,'Icon':u.TextureGroup.TEXTUREGROUP_UI}[channel],
        'never_stream':icon,'max_texture_size':1024 if icon else 2048,
        'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS if icon else u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP,
        'flip_green_channel':channel=='Normal'})
    return save(asset)

def duplicate(source,target):
    asset=u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.EditorAssetLibrary.duplicate_asset(source,target)
    if not asset:raise RuntimeError('Cannot create '+target+' from '+source)
    return asset

maps={kind:texture(filename,ROOT+'/Textures',kind) for kind,filename in entry['textures'].items()}
def replace_pbr(material):
    found=set()
    for expression in E.get_material_expressions(material):
        if not isinstance(expression,u.MaterialExpressionTextureSample) or isinstance(expression,u.MaterialExpressionTextureSampleParameter2D):continue
        sampler=expression.get_editor_property('sampler_type')
        channel={u.MaterialSamplerType.SAMPLERTYPE_COLOR:'BaseColor',u.MaterialSamplerType.SAMPLERTYPE_MASKS:'ORM',
                 u.MaterialSamplerType.SAMPLERTYPE_NORMAL:'Normal'}.get(sampler)
        if channel:expression.set_editor_property('texture',maps[channel]);found.add(channel)
    if found!={'BaseColor','ORM','Normal'}:raise RuntimeError('Source material missing a PBR channel: '+str(found))
    E.recompile_material(material)

material=duplicate(SOURCE+'/Materials/M_Kukri_FoldedBalanced',ROOT+'/Materials/M_Kukri_Canine')
replace_pbr(material);save(material)
mesh=import_mesh(entry['fbx'],ROOT+'/SM_Kukri_Blade_Canine',material)
source_mesh=u.load_asset(SOURCE+'/SM_Kukri_Blade_FoldedBalanced')
if not source_mesh:raise RuntimeError('Missing source blade mesh')
mesh.set_editor_property('nanite_settings',source_mesh.get_editor_property('nanite_settings'))
u.EditorAssetLibrary.set_metadata_tag(mesh,'Kukri.Source',entry['blend'])
u.EditorAssetLibrary.set_metadata_tag(mesh,'Kukri.BladeLength','Factory length; twelve serrations; grip interface fixed through 6.6 cm')
save(mesh)
receipt.update({'mesh':mesh.get_path_name(),'material':material.get_path_name(),'slot':'M_Kukri_Canine'})

masks={r['id']:texture(r['blade_masks']['Canine'],ROOT+'/Runes/Textures','Mask') for r in runes}
rune_material=duplicate(RUNE_SOURCE+'/Materials/M_KukriMark_FoldedBalanced',ROOT+'/Runes/Materials/M_KukriMark_Canine')
replace_pbr(rune_material)
for expression in E.get_material_expressions(rune_material):
    if isinstance(expression,(u.MaterialExpressionTextureSampleParameter2D,u.MaterialExpressionTextureObjectParameter)):
        if str(expression.get_editor_property('parameter_name'))=='RuneMask':
            expression.set_editor_property('texture',masks[runes[0]['id']])
E.recompile_material(rune_material);save(rune_material)
for rune in runes:
    instance=duplicate(RUNE_SOURCE+'/Natural20261027/Materials/MI_KukriMark_FoldedBalanced_'+rune['kind'],
        ROOT+'/Runes/Materials/MI_KukriMark_Canine_'+rune['kind'])
    E.set_material_instance_parent(instance,rune_material)
    E.set_material_instance_texture_parameter_value(instance,'RuneMask',masks[rune['id']])
    E.update_material_instance(instance);save(instance)
    receipt['rune_surfaces'][rune['id']]={'M_Kukri_Canine':instance.get_path_name()}

icon=texture(P/'Icons/ue_kukri_blade_1_canine_blade.png','/Game/ColdSteelData/AttachmentIcons20260913','Icon','ue_kukri_blade_1_canine_blade')
receipt['icon']=icon.get_path_name();receipt['complete']=True
(P/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('CANINE_ASSETS_SAVED '+str(len(receipt['saved_assets'])))
