"""Persistent, non-emissive cosmetic rune surfaces for all four Kukri blades."""
import json
from pathlib import Path
import unreal as u
P=Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\KukriComponentVariants20261026\import_runes.py').resolve().parent
ROOT='/Game/Weapons/Kukri20261020/ComponentVariants20261026/Runes/Natural20261027'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
entries=json.loads((P/'runes.json').read_text(encoding='utf-8'))['runes']
receipt={'complete':False,'saved_assets':[],'root_materials':{},'rune_surfaces':{},'runtime_tested':False}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name());return asset
def import_texture(filename,dest,name,icon=False):
    task=u.AssetImportTask();task.filename=filename;task.destination_path=dest;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    asset=u.load_asset(dest+'/'+name)
    if not asset:raise RuntimeError('Texture import '+name)
    asset.set_editor_property('srgb',icon);asset.set_editor_property('never_stream',icon)
    asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_MASKS)
    asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI if icon else u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR)
    asset.set_editor_property('max_texture_size',1024 if icon else 2048)
    if icon:asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    return save(asset)
def node(mat,cls,**kw):
    n=E.create_material_expression(mat,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def connect(a,pin,b,target):
    if not E.connect_material_expressions(a,pin,b,target):raise RuntimeError('Connect '+target)
masks={}
for entry in entries:
    masks[entry['id']]={kind:import_texture(filename,ROOT+'/Textures',Path(filename).stem)
        for kind,filename in entry.get('blade_masks',{'Factory':entry['mask']}).items()}
    import_texture(entry['icon'],'/Game/ColdSteelData/AttachmentIcons20260913',entry['icon_key'],True)
    receipt['rune_surfaces'][entry['id']]={}

blades=[{'id':'factory','kind':'Factory','mesh':'/Game/Weapons/Kukri20261020/Modules20261026/SM_Kukri_Blade_Factory',
 'texture_root':'/Game/Weapons/Kukri20261020/Textures/T_Kukri_'}]
for source in json.loads((P.parent/'KukriBladeVariants20261026/variants.json').read_text(encoding='utf-8'))['variants']:
    blades.append({'id':source['id'],'kind':source['kind'],'mesh':source['mesh'],
        'texture_root':'/Game/Weapons/Kukri20261020/BladeVariants20261026/Textures/T_Kukri_'+source['kind']+'_'})
colors={'knife_mark_wing':(.42,.27,.09,1),'knife_mark_knot':(.60,.62,.64,1),'knife_mark_peaks':(.035,.04,.045,1)}
for blade in blades:
    mesh=u.load_asset(blade['mesh'])
    if not mesh:raise RuntimeError('Blade mesh missing '+blade['mesh'])
    slots=mesh.get_editor_property('static_materials')
    slot=str(slots[0].get_editor_property('material_slot_name'))
    base_material=mesh.get_material(0)
    receipt['root_materials'][blade['id']]={'material_slot_names':[slot],'materials':{slot:base_material.get_path_name()}}
    name='M_KukriMark_'+blade['kind']
    mat=u.load_asset(ROOT+'/Materials/'+name) or A.create_asset(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    E.delete_all_material_expressions(mat);mat.set_editor_property('use_material_attributes',False)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);mat.set_editor_property('two_sided',False)
    base=node(mat,u.MaterialExpressionTextureSample,texture=u.load_asset(blade['texture_root']+'BaseColor'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm=node(mat,u.MaterialExpressionTextureSample,texture=u.load_asset(blade['texture_root']+'ORM'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    normal=node(mat,u.MaterialExpressionTextureSample,texture=u.load_asset(blade['texture_root']+'Normal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    ink=node(mat,u.MaterialExpressionTextureSampleParameter2D,parameter_name='RuneMask',texture=next(iter(masks.values()))['Factory'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    tint=node(mat,u.MaterialExpressionVectorParameter,parameter_name='RuneTint',default_value=u.LinearColor(.4,.4,.4,1))
    color=node(mat,u.MaterialExpressionLinearInterpolate)
    connect(base,'RGB',color,'A');connect(tint,'RGB',color,'B');connect(ink,'R',color,'Alpha')
    rough=node(mat,u.MaterialExpressionLinearInterpolate,const_b=.28);connect(orm,'G',rough,'A');connect(ink,'R',rough,'Alpha')
    metal=node(mat,u.MaterialExpressionLinearInterpolate,const_b=.87);connect(orm,'B',metal,'A');connect(ink,'R',metal,'Alpha')
    slab=node(mat,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for src,pin,prop,target in [(color,'',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(rough,'',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),
          (metal,'',u.MaterialProperty.MP_METALLIC,'Metallic'),(normal,'RGB',u.MaterialProperty.MP_NORMAL,'Normal'),(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION,None)]:
        if target:connect(src,pin,slab,target)
        if not E.connect_material_property(src,pin,prop):raise RuntimeError('Material output '+str(prop))
    if not E.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('FrontMaterial output')
    E.layout_material_expressions(mat);E.recompile_material(mat);save(mat)
    for entry in entries:
        name='MI_KukriMark_'+blade['kind']+'_'+entry['kind']
        instance=u.load_asset(ROOT+'/Materials/'+name) or A.create_asset(name,ROOT+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        E.set_material_instance_parent(instance,mat)
        E.set_material_instance_texture_parameter_value(instance,'RuneMask',masks[entry['id']].get(blade['kind'],masks[entry['id']]['Factory']))
        E.set_material_instance_vector_parameter_value(instance,'RuneTint',u.LinearColor(*colors[entry['id']]))
        E.update_material_instance(instance);save(instance)
        receipt['rune_surfaces'][entry['id']][slot]=instance.get_path_name()
receipt['complete']=True
(P/'rune_import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('KUKRI_STATIC_RUNES_SAVED '+str(len(receipt['saved_assets'])))
