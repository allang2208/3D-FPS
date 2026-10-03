"""Save native-715 RSH meshes and mechanical-only profiles, without running PIE."""
import unreal as u,json,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('PIE active; defer saving')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
root='/Game/Weapons/RSH12/Native71520261003'
receipt=dict(revision='native-715-contact-v2',complete=False,saved=[],families={},runtime_tested=False)
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    receipt['saved'].append(a.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
metal=u.load_asset('/Game/Weapons/RSH12/Materials/MI_RSH12_SourcePBR')
bare=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareNative_Default')
config=P/'Content/ColdSteelData/modular_outfits.json'
original=config.read_text(encoding='utf-8-sig');outfits=json.loads(original)
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for side in ('single','r','l'):
        src=O/('Single' if side=='single' else 'Dual/'+side)
        meta=json.loads((src/'authoring.json').read_text(encoding='utf8'))
        name=Path(meta['mesh']).stem;dest=root+'/'+side
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
        opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_animations=False
        opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False
        opts.skeleton=u.load_asset(meta['skeleton'])
        opts.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
        opts.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
        opts.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(src/meta['mesh']);task.destination_path=dest;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True
        task.save=False;task.options=opts;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=u.load_asset(dest+'/'+name)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
        slots=list(mesh.materials);arm_slots=[]
        for i,slot in enumerate(slots):
            arm='Manny' in str(slot.material_slot_name)
            slot.material_interface=bare if arm else metal
            if arm:arm_slots.append(i)
            slots[i]=slot
        mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
        E.set_metadata_tag(mesh,'AuthoringSource','RSH12Native71520261003; native V7 grasp; real RSH yoke hinge; hand-relative cartridge pickup and shared insertion contact')
        save(mesh)
        oldpath='/Game/Weapons/RSH12/'+('SK_RSH12_Manny.SK_RSH12_Manny' if side=='single' else 'Dual/'+side+'/SK_Dual_RSH12_'+side+'.SK_Dual_RSH12_'+side)
        entry=copy.deepcopy(outfits['profiles'][oldpath]);entry['hide_source_materials']=arm_slots
        outfits['profiles'][mesh.get_path_name()]=entry
        name='DA_RSH12_'+('' if side=='single' else side+'_')+'base'
        profile=u.load_asset(root+'/Profiles/'+name)
        if not profile:
            f=u.DataAssetFactory();f.set_editor_property('data_asset_class',u.WeaponGripProfile)
            profile=A.create_asset(name,root+'/Profiles',u.WeaponGripProfile,f)
        content=(src/'profile.json').read_text(encoding='utf8')
        if not profile.set_shared_clips_from_json(content):raise RuntimeError('Profile import failed '+side)
        save(profile)
        receipt['families'][side]=dict(mesh=mesh.get_path_name(),profile=profile.get_path_name(),shared_clips=len(json.loads(content)['clips']),new_animation_sequences=0)
        print('RSH12_CONTACT_REPAIR_SAVED',side,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
if config.read_text(encoding='utf-8-sig')!=original:raise RuntimeError('Outfit config changed during import')
backup=O/'BeforeCatalog/modular_outfits.json';backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():backup.write_text(original,encoding='utf8')
config.write_text(json.dumps(outfits,ensure_ascii=False,indent=2),encoding='utf8')
receipt['complete']=True
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH12_CONTACT_REPAIR_IMPORT_COMPLETE',flush=True)
