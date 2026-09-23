"""Import only eight PKM grip meshes, preserving the current dry/wet finish."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2]
D='/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
spec=json.loads((O/'authoring.json').read_text());report={};before={}
table=u.load_asset('/Game/Weapons/PKMLowpoly20260922/Finish20/DA_PKM_WetMaterials')
wet={str(k):v.get_path_name() for k,v in table.get_editor_property('wet_materials').items() if v}
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,info in spec.items():
        path=D+'/'+info['name'];mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Current grip missing: '+path)
        bindings={str(s.material_slot_name):s.material_interface for s in mesh.static_materials}
        if any(m is None for m in bindings.values()):raise RuntimeError('Unbound current material: '+path)
        before[key]={'asset':path,'size_cm':list((mesh.get_bounds().box_extent*2).to_tuple()),
                     'materials':{n:m.get_path_name() for n,m in bindings.items()},
                     'source':mesh.get_editor_property('asset_import_data').get_first_filename()}
        (O/'assets_before.json').write_text(json.dumps(before,indent=2))
        disk=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'BeforeImport'/disk.name
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():shutil.copy2(disk,backup)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
        data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=str(O/'Exports'/(info['name']+'.fbx'))
        task.destination_path=D;task.destination_name=info['name'];task.options=opt;task.factory=u.FbxFactory()
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not task.imported_object_paths:raise RuntimeError('Import failed: '+key)
        slots=mesh.static_materials
        for i,slot in enumerate(slots):
            name=str(slot.material_slot_name)
            if name not in bindings:raise RuntimeError('Unexpected material slot: '+key+' / '+name)
            slot.material_interface=bindings[name];slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        E.set_metadata_tag(mesh,'PKMContactRevision','GripMount25; factory grasp-axis seat and fitted mount surfaces')
        size=list((mesh.get_bounds().box_extent*2).to_tuple())
        if not 2<size[0]<11 or not 3<size[1]<16 or not 4<size[2]<17:
            raise RuntimeError('Grip import unit mismatch: '+str(size))
        if not E.save_asset(path,False):raise RuntimeError('Save failed: '+key)
        report[key]={'asset':mesh.get_path_name(),'saved':True,'size_cm':size,
            'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name(),
                      'wet':wet.get(s.material_interface.get_path_name())} for s in mesh.static_materials],
            'source_fbx':task.filename,'backup':str(backup),'sha256':hashlib.sha256(disk.read_bytes()).hexdigest()}
        (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
        print('PKM25_GRIP_SAVED',key,json.dumps(size),flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('PKM25_ALL_GRIPS_SAVED',flush=True)
