"""Save head-specific rune masks and PBR-preserving material derivatives."""
from pathlib import Path
import json,runpy,shutil
import unreal as u
P=Path(__file__).resolve().parent;PROJECT=P.parents[2]
ROOT='/Game/Weapons/TacticalHatchet20261101/CommonRunes20261104'
CARRIER='/Game/Weapons/TacticalHatchet20261101/ModulesV1/SM_TacticalHatchet_Head_Factory_RuneCarrier'
E=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary
source=json.loads((P/'sources.json').read_text('utf-8'))
heads=[json.loads((P/(h['kind']+'.json')).read_text('utf-8')) for h in source['heads']]
owned={CARRIER}
for head in heads:
    owned.add(ROOT+'/Materials/M_HatchetMark_'+head['kind'])
    for plan in head['placements']:
        owned.add(ROOT+'/Textures/'+Path(plan['mask']).stem)
        owned.add(ROOT+'/Materials/MI_HatchetMark_'+head['kind']+'_'+plan['kind'])
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&owned:raise RuntimeError('Unsaved rune targets preserved: '+str(dirty&owned))
for package in owned:
    rel=Path(package.removeprefix('/Game/')+'.uasset')
    old=PROJECT/'Content'/rel;backup=P/'Before/Assets'/rel
    if old.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,backup)
receipt={'complete':False,'saved_assets':[],'rune_surfaces':{r['id']:{} for r in source['runes']},'heads':[],
    'runtime_tested':False,'geometry_modified':False,'pbr_preserved':True}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    if asset.get_path_name() not in receipt['saved_assets']:receipt['saved_assets'].append(asset.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def connect(a,pin,b,target):
    if not E.connect_material_expressions(a,pin,b,target):raise RuntimeError('Cannot connect '+target)
flow=runpy.run_path(str(PROJECT/'SourceAssets/AllWeaponRuneFlow20261102/knife_material.py'))['add_knife_flow']
for head in heads:
    masks={}
    for plan in head['placements']:
        name=Path(plan['mask']).stem
        task=u.AssetImportTask();task.filename=plan['mask'];task.destination_path=ROOT+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
        texture=u.load_asset(ROOT+'/Textures/'+name)
        if not texture or not task.imported_object_paths:raise RuntimeError('Mask import failed: '+name)
        texture.set_editor_properties({'srgb':False,'never_stream':False,'compression_settings':u.TextureCompressionSettings.TC_MASKS,
            'lod_group':u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,'max_texture_size':2048,
            'address_x':u.TextureAddress.TA_CLAMP,'address_y':u.TextureAddress.TA_CLAMP})
        save(texture);masks[plan['id']]=texture
    path=ROOT+'/Materials/M_HatchetMark_'+head['kind']
    mat=u.load_asset(path) if L.does_asset_exist(path) else L.duplicate_asset(head['material'].split('.')[0],path)
    if not mat:raise RuntimeError('Cannot preserve head PBR: '+head['kind'])
    if L.get_metadata_tag(mat,'HatchetRuneSurface')!='isometric-head-uv0-v1':
        front=E.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)
        if not isinstance(front,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Unexpected head surface graph')
        def node(cls,**props):
            result=E.create_material_expression(mat,cls);result.set_editor_properties(props);return result
        ink=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='RuneMask',
            texture=next(iter(masks.values())),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        tint=node(u.MaterialExpressionVectorParameter,parameter_name='RuneTint',default_value=u.LinearColor(.4,.4,.4,1))
        # Retain the actual source graph and UVs, including its normal and existing finish.
        for prop,pin,replacement in [(u.MaterialProperty.MP_BASE_COLOR,'BaseColor',tint),
                                      (u.MaterialProperty.MP_ROUGHNESS,'Roughness',.28),
                                      (u.MaterialProperty.MP_METALLIC,'Metallic',.87)]:
            original=E.get_material_property_input_node(mat,prop)
            output=E.get_material_property_input_node_output_name(mat,prop)
            if not original:raise RuntimeError('Missing authored PBR input '+pin)
            blend=node(u.MaterialExpressionLinearInterpolate)
            connect(original,output,blend,'A');connect(ink,'R',blend,'Alpha')
            if isinstance(replacement,float):blend.set_editor_property('const_b',replacement)
            else:connect(replacement,'RGB',blend,'B')
            connect(blend,'',front,pin)
            if not E.connect_material_property(blend,'',prop):raise RuntimeError('Cannot preserve legacy '+pin)
        z0=min(p['center_m'][1]-p['height_m']*.5 for p in head['placements'])*100
        z1=max(p['center_m'][1]+p['height_m']*.5 for p in head['placements'])*100
        flow(mat,z0,z1-z0)
        L.set_metadata_tag(mat,'HatchetRuneSurface','isometric-head-uv0-v1')
        L.set_metadata_tag(mat,'OriginalPBR',head['material'])
        E.layout_material_expressions(mat);E.recompile_material(mat)
    save(mat)
    for rune in source['runes']:
        name='MI_HatchetMark_'+head['kind']+'_'+rune['kind']
        instance=u.load_asset(ROOT+'/Materials/'+name) if L.does_asset_exist(ROOT+'/Materials/'+name) else A.create_asset(name,ROOT+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        E.set_material_instance_parent(instance,mat)
        E.set_material_instance_texture_parameter_value(instance,'RuneMask',masks[rune['id']])
        E.set_material_instance_vector_parameter_value(instance,'RuneTint',u.LinearColor(*rune['tint']))
        E.update_material_instance(instance);save(instance)
        receipt['rune_surfaces'][rune['id']][head['target_slot']]=instance.get_path_name()
    receipt['heads'].append({'id':head['id'],'slot':head['target_slot'],'source_mesh':head['mesh']})
# The factory head shares its old slot label with the grip and pommel.
# A geometry-identical carrier gives only the head a unique runtime material identity.
factory=next(h for h in heads if h['id']=='factory')
mesh=u.load_asset(CARRIER) if L.does_asset_exist(CARRIER) else L.duplicate_asset(factory['mesh'].split('.')[0],CARRIER)
if not mesh:raise RuntimeError('Cannot create factory head carrier')
slots=mesh.get_editor_property('static_materials')
if len(slots)!=1:raise RuntimeError('Unexpected factory head material layout')
slot=slots[0]
slot.set_editor_property('material_slot_name',u.Name(factory['target_slot']))
# Array indexing returns a struct value; write it back before assigning the array.
slots[0]=slot
# ImportedMaterialSlotName is read-only import provenance; runtime uses MaterialSlotName.
mesh.set_editor_property('static_materials',slots)
if str(mesh.get_editor_property('static_materials')[0].get_editor_property('material_slot_name'))!=factory['target_slot']:
    raise RuntimeError('Factory rune carrier slot assignment failed')
mesh.set_material(0,u.load_asset(factory['material']))
L.set_metadata_tag(mesh,'RuneCarrier','Head-only material identity; original geometry UV0 and PBR retained')
save(mesh)
receipt['factory_carrier']={'mesh':mesh.get_path_name(),'material_slot_names':[factory['target_slot']],
    'materials':{factory['target_slot']:factory['material']},'rune_carrier_source_mesh':factory['mesh']}
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
u.log('HATCHET_COMMON_RUNES_SAVED heads=5 runes=3 assets='+str(len(receipt['saved_assets'])))
