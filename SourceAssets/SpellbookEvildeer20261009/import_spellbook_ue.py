"""Save the prepared book assets in an isolated UE content folder."""
import json
from datetime import datetime, timezone
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpellbookEvildeer20261009')
OUT=ROOT/'Export'
DEST='/Game/Weapons/SpellbookEvildeer20261009'
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
A=u.AssetToolsHelpers.get_asset_tools()
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
receipt={'destination':DEST,'started_at':datetime.now(timezone.utc).isoformat(),'saved_assets':[],
         'source':manifest['source_uid'],'selected_cover':manifest['selected_cover'],
         'complete':False,'runtime_integration':False,'tested':False,'rendered':False}
# Reuse completed texture/material work when resuming an interrupted import.
previous_receipt=ROOT/'ue-import-receipt.json'
previous_saved=set(json.loads(previous_receipt.read_text(encoding='utf-8')).get('saved_assets',[])) if previous_receipt.exists() else set()

def record():
    (ROOT/'ue-import-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

def save(asset):
    if not E.save_loaded_asset(asset,only_if_is_dirty=False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    path=asset.get_path_name()
    if path not in receipt['saved_assets']:receipt['saved_assets'].append(path)
    record()

def imp(file,name,destination,options=None):
    task=u.AssetImportTask()
    task.filename=str(file);task.destination_name=name;task.destination_path=destination
    task.automated=True;task.replace_existing=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task])
    asset=u.load_asset(destination+'/'+name)
    if not asset:raise RuntimeError('Import did not create '+destination+'/'+name)
    return asset

record()
materials={}
for name,spec in manifest['materials'].items():
    path=DEST+'/Materials/'+name
    mat=E.load_asset(path) if E.does_asset_exist(path) else None
    if mat and mat.get_path_name() in previous_saved:
        materials[name]=mat
        receipt['saved_assets'] += sorted(p for p in previous_saved if p==mat.get_path_name() or ('/Textures/T_'+name[2:]+'_') in p)
        record()
        continue
    if not mat:mat=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    for expression in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expression)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('used_with_skeletal_mesh',True)
    properties={'BaseColor':u.MaterialProperty.MP_BASE_COLOR,'Roughness':u.MaterialProperty.MP_ROUGHNESS,
                'Metallic':u.MaterialProperty.MP_METALLIC,'Normal':u.MaterialProperty.MP_NORMAL}
    for channel,rel in spec['maps'].items():
        source=OUT/rel
        texture=imp(source,source.stem,DEST+'/Textures')
        texture.set_editor_property('srgb',channel=='BaseColor')
        if channel=='Normal':
            texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('flip_green_channel',spec['normal_convention']=='OpenGL')
            sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL
        elif channel=='BaseColor':sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR
        else:
            texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
            sampler=u.MaterialSamplerType.SAMPLERTYPE_MASKS
        save(texture)
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSample)
        node.texture=texture;node.set_editor_property('sampler_type',sampler)
        L.connect_material_property(node,'RGB' if channel in ('BaseColor','Normal') else 'R',properties[channel])
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material compile failed: '+name+' '+str(errors))
    E.set_metadata_tag(mat,'SourceAuthor','evildeer')
    E.set_metadata_tag(mat,'SourceLicense','CC BY 4.0')
    save(mat);materials[name]=mat

def options(kind):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.import_mesh=kind!='animation';opt.import_animations=kind=='animation';opt.import_as_skeletal=kind=='skeletal'
    opt.mesh_type_to_import={'static':u.FBXImportType.FBXIT_STATIC_MESH,'skeletal':u.FBXImportType.FBXIT_SKELETAL_MESH,'animation':u.FBXImportType.FBXIT_ANIMATION}[kind]
    if kind!='animation':
        data=opt.skeletal_mesh_import_data if kind=='skeletal' else opt.static_mesh_import_data
        data.convert_scene=True;data.convert_scene_unit=False;data.import_uniform_scale=1.
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        if kind=='static':
            data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    return opt

def material_for_slot(slot):
    name=str(slot.material_slot_name)
    # FBX/UE preserve authored material slot names; do not silently replace with a default.
    if name not in materials:raise RuntimeError('No authored material for slot '+name)
    return materials[name]

flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for filename in manifest['static_meshes']:
        mesh=imp(OUT/filename,Path(filename).stem,DEST+'/Meshes',options('static'))
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,material_for_slot(slot))
        nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite)
        save(mesh)
    name=Path(manifest['skeletal_mesh']).stem
    skin=imp(OUT/manifest['skeletal_mesh'],name,DEST+'/Meshes',options('skeletal'))
    slots=list(skin.get_editor_property('materials'))
    for slot in slots:slot.set_editor_property('material_interface',material_for_slot(slot))
    skin.set_editor_property('materials',slots)
    save(skin)
    skeleton=skin.get_editor_property('skeleton');save(skeleton)
    receipt['skeleton']=skeleton.get_path_name()
    receipt['animations']={}
    for key,spec in manifest['animations'].items():
        opt=options('animation');opt.skeleton=skeleton
        opt.anim_sequence_import_data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
        anim=imp(OUT/spec['file'],Path(spec['file']).stem,DEST+'/Animations',opt)
        save(anim);receipt['animations'][key]=anim.get_path_name()
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

receipt['complete']=True;receipt['finished_at']=datetime.now(timezone.utc).isoformat();record()
print('SPELLBOOK_ASSETS_SAVED '+json.dumps({'assets':len(receipt['saved_assets']),'destination':DEST,'tested':False,'runtime_integration':False}))
