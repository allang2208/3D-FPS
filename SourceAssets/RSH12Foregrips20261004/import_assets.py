"""Import and save only this RSH foregrip batch; no play, renders or tests."""
import unreal as u,json,runpy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/RSH12/Foregrips20261004'
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('PIE is active; assets were not modified')
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing source '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
models=json.loads((O/'models.json').read_text());receipt={'meshes':{},'profiles':{},'runtime_tested':False}
finish=runpy.run_path(str(O.parent/'RSH12MaterialFinish20261005/finish_materials.py'))
finished_materials=finish['make_foregrip_materials'](save)
finish['register_weather'](finished_materials.values(),save)
bindings=finish['FOREGRIP_BINDINGS']
for key,part in models['parts'].items():
    name='SM_RSH12_'+key
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'));task.destination_path=D+'/Meshes';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.options=options;A.import_asset_tasks([task])
    mesh=load(D+'/Meshes/'+name);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        label=str(slot.material_slot_name).split('.')[0]
        # FBX sanitizes material suffix periods into underscores.
        if label not in bindings:
            label=next((n for n in bindings if label.startswith(n)),label)
        slot.material_interface=load(bindings[label]);slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
    settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
    editor.set_lod_build_settings(mesh,0,settings)
    # Existing project helper builds the imported render resources before save.
    if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Mesh build failed '+key)
    E.set_metadata_tag(mesh,'RSHForegripSource','RSH12Foregrips20261004; common grip body, narrow rail insert')
    save(mesh);receipt['meshes'][key]=mesh.get_path_name()
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
for family in ('vertical','canted','prism','angled'):
    name='DA_RSH12_'+family;asset=u.load_asset(D+'/Profiles/'+name)
    if not asset:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
        asset=A.create_asset(name,D+'/Profiles',u.WeaponGripProfile,factory)
    if not asset.set_shared_clips_from_json((O/'Profiles'/(family+'.json')).read_text(encoding='utf8')):raise RuntimeError('Profile import failed '+family)
    E.set_metadata_tag(asset,'RSHForegripSource','RSH12UnifiedGrip20261004 plus left-arm rifle grasp; native reload and quickcombat middle')
    save(asset);receipt['profiles'][family]=asset.get_path_name()
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
print('RSH_FOREGRIPS_ASSETS_SAVED',flush=True)
