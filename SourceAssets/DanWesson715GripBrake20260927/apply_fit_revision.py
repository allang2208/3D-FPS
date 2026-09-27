"""Reimport only the two corrected grip meshes; preserve their existing UE materials."""
import json, shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;D='/Game/Weapons/DanWesson715/GripBrake20260927'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
report={}
for key in ['dw715_rubber_grip','dw715_target_wood_grip']:
    before=O/'FitInspection'/(key+'_before.json')
    if not before.exists():shutil.copyfile(O/'FitInspection'/(key+'.json'),before)
    name='SM_'+key;path=D+'/Meshes/'+name
    mesh=u.load_asset(path);bindings={str(s.material_slot_name):s.material_interface for s in mesh.static_materials}
    task=u.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=D+'/Meshes';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(path)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'FitRevision','20260927: preserve full contact floor; enlarged wood rear heel only, sampled against current V7 hands')
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    report[key]=mesh.get_path_name()
(O/'fit_revision_installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('DW715_GRIP_FIT_REVISION_SAVED '+str(len(report)))
