"""Install the repaired 20 options and three materials in one editor-owned batch.
No PIE, captures, audits, player profiles, or unrelated packages are touched.
"""
import unreal as u
import json
from pathlib import Path
ROOT=Path(r'D:/FPS3D/FPSGAME/SourceAssets/ApprenticeStaff20260927')
DEST='/Game/Weapons/ApprenticeStaff20260927'
RECEIPT=ROOT/'RepairV2/import-receipt.json'
editor=u.get_editor_subsystem(u.LevelEditorSubsystem) if '-run=' not in u.SystemLibrary.get_command_line().lower() else None
if editor and editor.is_in_play_in_editor():
    raise RuntimeError('PIE must end before this asset-writing batch can start.')
entries=[e for e in json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8'))
         if e['name'] not in ('SM_Staff_Base','SM_Staff_Body','SM_Staff_head_crystal_false','SM_Staff_grip_lining_false')]
new_names=('M_Staff_PineV2','M_Staff_SandalV2','M_Staff_RuneV2')
targets={DEST+'/Meshes/'+e['name'] for e in entries}|{DEST+'/Materials/'+n for n in new_names}
# Ownership precondition, not an asset acceptance run: do not overwrite manual unsaved work.
# Explicit ownership of the interrupted writes: first material (PIE rejected
# save), then first reimport (read-only slot metadata rejected assignment).
resume_created={DEST+'/Materials/M_Staff_PineV2',DEST+'/Meshes/SM_Staff_head_crystal_frozen_crystal'}
conflicts=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets and p.get_name() not in resume_created]
if conflicts:raise RuntimeError('Unsaved edits in staff target assets: '+', '.join(conflicts))
tools=u.AssetToolsHelpers.get_asset_tools()
saved=json.loads(RECEIPT.read_text(encoding='utf-8')).get('saved_assets',[]) if RECEIPT.exists() else []
def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Asset was not saved: '+asset.get_path_name())
    if asset.get_path_name() not in saved:saved.append(asset.get_path_name())
    RECEIPT.write_text(json.dumps({'revision':2,'complete':False,'saved_assets':saved,'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
def scalar(m,value,prop):
    n=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionConstant)
    n.set_editor_property('r',value);u.MaterialEditingLibrary.connect_material_property(n,'',prop)
def color(m,value):
    n=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionConstant3Vector)
    n.set_editor_property('constant',u.LinearColor(*value,1));return n
for name in new_names:
    path=DEST+'/Materials/'+name
    m=u.load_asset(path)
    if m:
        if path in resume_created and m.get_path_name() not in saved:save(m)
        continue
    m=tools.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    if name=='M_Staff_RuneV2':
        base=color(m,(.68,.34,.08));u.MaterialEditingLibrary.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR)
        emission=color(m,(.102,.051,.012));u.MaterialEditingLibrary.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        scalar(m,.7,u.MaterialProperty.MP_METALLIC);scalar(m,.4,u.MaterialProperty.MP_ROUGHNESS)
    else:
        tex=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionTextureSample)
        tex.set_editor_property('texture',u.load_asset(DEST+'/Textures/T_Staff_base_color'))
        tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        tint=color(m,(.83,.62,.38) if name=='M_Staff_PineV2' else (.44,.17,.10))
        multiply=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionMultiply)
        u.MaterialEditingLibrary.connect_material_expressions(tex,'RGB',multiply,'A')
        u.MaterialEditingLibrary.connect_material_expressions(tint,'',multiply,'B')
        u.MaterialEditingLibrary.connect_material_property(multiply,'',u.MaterialProperty.MP_BASE_COLOR)
        normal=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionTextureSample)
        normal.set_editor_property('texture',u.load_asset(DEST+'/Textures/T_Staff_normal'))
        normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        u.MaterialEditingLibrary.connect_material_property(normal,'RGB',u.MaterialProperty.MP_NORMAL)
        scalar(m,.58,u.MaterialProperty.MP_ROUGHNESS);scalar(m,0,u.MaterialProperty.MP_METALLIC)
    u.MaterialEditingLibrary.recompile_material(m);save(m)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.set_editor_property('import_mesh',True);options.set_editor_property('import_as_skeletal',False)
options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
options.set_editor_property('import_materials',False);options.set_editor_property('import_textures',False)
data=options.get_editor_property('static_mesh_import_data');data.set_editor_property('combine_meshes',True)
data.set_editor_property('auto_generate_collision',False);data.set_editor_property('import_uniform_scale',1)
data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
data.set_editor_property('reorder_material_to_fbx_order',True)
for entry in entries:
    task=u.AssetImportTask();task.set_editor_property('filename',entry['fbx'])
    task.set_editor_property('destination_path',DEST+'/Meshes');task.set_editor_property('destination_name',entry['name'])
    task.set_editor_property('automated',True);task.set_editor_property('replace_existing',True)
    task.set_editor_property('replace_existing_settings',True);task.set_editor_property('save',False);task.set_editor_property('options',options)
    tools.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/Meshes/'+entry['name'])
    if not asset:raise RuntimeError('Import did not return mesh: '+entry['name'])
    # Preserve importer-owned section indices and read-only imported slot names.
    # Reimports can retain unused old slots; binding by source name is safe even
    # when those slots are present. Do not truncate and shift section indices.
    for i,slot in enumerate(asset.get_editor_property('static_materials')):
        imported=str(slot.get_editor_property('imported_material_slot_name'))
        named=str(slot.get_editor_property('material_slot_name'))
        name=imported if imported in entry['materials'] else named if named in entry['materials'] else entry['materials'][min(i,len(entry['materials'])-1)]
        material=u.load_asset(DEST+'/Materials/'+name)
        if not material:raise RuntimeError('Missing authored material: '+name)
        asset.set_material(i,material)
    save(asset)
RECEIPT.write_text(json.dumps({'revision':2,'complete':True,'reimported_options':len(entries),'saved_assets':saved,
    'factory_assets_reimported':False,'tested':False,'rendered':False,'editor_restarted':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('STAFF_REPAIR_V2_SAVED options='+str(len(entries))+' saved='+str(len(saved)))
