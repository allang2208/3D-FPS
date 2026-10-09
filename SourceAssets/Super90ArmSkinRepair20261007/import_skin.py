"""Save corrected native surfaces and the Super90 equipment derivatives only."""
import json,re,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];S=P/'SourceAssets/BenelliM4Super9020261006'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
auth=json.loads((O/'authoring_receipt.json').read_text())
ROOT='/Game/Weapons/Super90/Cransh20261006'
OUTFIT='/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90'
receipt={'meshes_saved':[],'equipment':[],'animation_tracks_changed':False,'runtime_tested':False}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
def clean(n):return re.sub(r'[._]\d{3}$','',str(n)).removeprefix('Manny_S90_')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Cannot save '+asset.get_path_name())
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for name,folder in [('SK_Super90_V7',ROOT),('SK_Super90_BareArmsV7',OUTFIT)]:
        mesh=u.load_asset(folder+'/'+name)
        if not mesh:raise RuntimeError('Missing native mesh '+name)
        old={clean(m.material_slot_name):(str(m.material_slot_name),m.material_interface) for m in mesh.materials}
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True
        options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
        options.create_physics_asset=False;options.skeleton=mesh.skeleton
        options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
        options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS if name=='SK_Super90_V7' else u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        file=Path(auth['exports'][name]);task=u.AssetImportTask();task.filename=str(file)
        task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True
        task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        A.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('No imported mesh returned for '+name)
        mesh=u.load_asset(folder+'/'+name);slots=list(mesh.materials)
        for i,slot in enumerate(slots):
            key=clean(slot.material_slot_name)
            if key not in old:raise RuntimeError('Unmapped material '+key)
            slot.material_slot_name=old[key][0];slot.material_interface=old[key][1];slots[i]=slot
        mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
        if name=='SK_Super90_V7':
            editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
            settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
            settings.recompute_normals=False;settings.recompute_tangents=False;editor.set_lod_build_settings(mesh,0,settings)
        E.set_metadata_tag(mesh,'Super90SourceSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
        E.set_metadata_tag(mesh,'Super90ArmSkinRepair','20261007: segment warp and proximal forearm skin station')
        save(mesh);receipt['meshes_saved'].append(mesh.get_path_name());record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

script=S/'import_equipment_family.py'
code=script.read_text(encoding='utf-8-sig').split('# Merge at the end')[0]
code=code.replace("(O/'equipment_manifest.json')","Path(r'"+str(O/'equipment_manifest.json')+"')")
scope={'__file__':str(script)};exec(compile(code,str(script),'exec'),scope)
for entry in json.loads((O/'equipment_manifest.json').read_text()):
    saved=json.loads((S/'EquipmentSaved'/(entry['profile']+'_'+entry['item']+'.json')).read_text())
    receipt['equipment'].append(saved['mesh'])

# Preserve current recipes, updating only this viewmodel's material coverage.
cp=P/'Content/ColdSteelData/modular_outfits.json';config=json.loads(cp.read_text(encoding='utf-8-sig'))
mesh=u.load_asset(ROOT+'/SK_Super90_V7');bare=u.load_asset(OUTFIT+'/SK_Super90_BareArmsV7')
profile=config['profiles'][mesh.get_path_name()]
profile['hide_source_materials']=[i for i,m in enumerate(mesh.materials) if str(m.material_slot_name).startswith('Manny_S90_')]
profile['glove_covers']=[i for i,m in enumerate(bare.materials) if 'hand' in str(m.material_slot_name).lower()]
profile['shirt_covers']=[i for i,m in enumerate(bare.materials) if i not in profile['glove_covers']]
cp.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt['completed']=True;record()
print('SUPER90_ARM_SKIN_SAVED',len(receipt['meshes_saved']),len(receipt['equipment']))
