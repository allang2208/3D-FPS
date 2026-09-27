"""Import and save the new SVD attachment and its catalog textures only."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).parent
ROOT='/Game/Weapons/SVDDragunov20260922/ExtendedMagazine20260927'
ICON_ROOT='/Game/ColdSteelData/AttachmentIcons20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
records=json.loads((O/'icons.json').read_text())
targets={ROOT+'/SM_SVD_ext_mag'}|{ICON_ROOT+'/'+k for k in records}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
resume_path=O/'import_resume.json'
owned_pending=set(json.loads(resume_path.read_text()).get('pending',[])) if resume_path.exists() else set()
if (dirty&targets)-owned_pending:raise RuntimeError('Unsaved SVD attachment target; preserve current edits: '+str(sorted((dirty&targets)-owned_pending)))
receipt={'meshes':{},'icons':{},'game_tested':False}
def record(): (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    # Only this task's new packages are saved. Package saving also works while
    # the user plays; no level, factory asset or gameplay instance is modified.
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Cannot save '+asset.get_path_name())

host=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
source_slots={str(s.material_slot_name):s.material_interface for s in host.materials}
material=source_slots['SM_SVD_Magazine_001']
flag='Interchange.FeatureFlags.Import.FBX'
old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
    options.set_editor_property('reset_to_fbx_on_material_conflict',True)
    options.override_full_name=True
    data=options.static_mesh_import_data;data.combine_meshes=False;data.auto_generate_collision=False;data.import_mesh_lods=True
    data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=str(O/'Exports/SM_SVD_ext_mag.fbx');task.destination_path=ROOT
    task.destination_name='SM_SVD_ext_mag';task.options=options;task.factory=u.FbxFactory()
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    existing=u.load_asset(ROOT+'/SM_SVD_ext_mag')
    if existing:
        # FbxFactory atomic reimport reads the asset's stored flags rather than
        # the new task's flags when completing the earlier partial import.
        prior_data=existing.get_editor_property('asset_import_data')
        prior_data.set_editor_property('import_mesh_lods',True)
        prior_data.set_editor_property('combine_meshes',False)
    resume_path.write_text(json.dumps({'pending':[ROOT+'/SM_SVD_ext_mag']}))
    A.import_asset_tasks([task])
    mesh=u.load_asset(ROOT+'/SM_SVD_ext_mag')
    if not mesh or not task.imported_object_paths:raise RuntimeError('SVD extended magazine import failed')
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        # Factory external shell, internal rim and floorplate use the SAME
        # dedicated magazine atlas at runtime. Do not bind generic steel here.
        slot.material_interface=material;slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    # LODs are already baked in the FBX; no editing of the live scene or PIE
    # state is needed to produce them. Complete all levels in the import batch.
    lod_result=mesh.get_num_lods()
    if lod_result!=3:raise RuntimeError('FBX did not import all three authored LOD levels: '+str(lod_result))
    E.set_metadata_tag(mesh,'SourceAttribution','SVD (Dragunov sniper rifle) by LeroyCake / CC BY 4.0; local factory-surface extension 20260927')
    E.set_metadata_tag(mesh,'SVDMagazineFrame','Original SVD skeletal mesh space; WPN_SOCKET_Magazine bind-chain inverse, no additional seat offset')
    E.set_metadata_tag(mesh,'SVDMagazineSource',str(O/'SVD_ExtendedMagazine_Editable.blend'))
    save(mesh)
    receipt['meshes']['ext_mag']={'asset':mesh.get_path_name(),'saved':True,'lods':lod_result,
        'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},
        'wet_materials':'Reuses the existing SVD magazine material and its registered wet counterpart'}
    record();print('SVD_EXTMAG_MESH_SAVED '+mesh.get_path_name(),flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))

for key,info in records.items():
    task=u.AssetImportTask();task.filename=info['output'];task.destination_path=ICON_ROOT;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.save=False
    resume_path.write_text(json.dumps({'pending':[ICON_ROOT+'/'+key]}))
    A.import_asset_tasks([task]);tex=u.load_asset(ICON_ROOT+'/'+key)
    if not tex or not task.imported_object_paths:raise RuntimeError('SVD icon import failed '+key)
    tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    save(tex);receipt['icons'][key]={'asset':tex.get_path_name(),'saved':True};record()
receipt['status']='imported_and_saved';record()
resume_path.write_text(json.dumps({'pending':[]}))
catalog_script=O/'update_catalog.py'
exec(compile(catalog_script.read_text(encoding='utf-8'),str(catalog_script),'exec'),{'__file__':str(catalog_script),'__name__':'__main__'})
receipt['catalog_published']=True;record()
print('SVD_EXTMAG_IMPORT_COMPLETE',flush=True)
