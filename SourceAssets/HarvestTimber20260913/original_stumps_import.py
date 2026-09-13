"""Import eight original-tree derivatives; only save this revision's assets."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent/'OriginalStumps';DEST='/Game/Items/HarvestTimber'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
bark=u.load_asset('/Game/WorldGeneration/TemperateHills/MI_BlackPoplarPCG_Bark')
foliage=u.load_asset('/Game/WorldGeneration/TemperateHills/MI_BlackPoplarPCG_Foliage')
cap=u.load_asset(DEST+'/M_PoplarEnd')
report={}
for name,info in json.loads((ROOT/'authoring.json').read_text()).items():
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
    task=u.AssetImportTask();task.filename=str(ROOT/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.options=opt;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if mesh is None:raise RuntimeError('Failed to import '+name)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        label=str(slot.material_slot_name)
        slot.material_interface=cap if 'EndGrain' in label else foliage if 'Foliage' in label else bark
        slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+name)
    report[name]={'path':mesh.get_path_name(),'bounds':str(mesh.get_bounds()),'slots':[str(s.material_slot_name) for s in slots]}
(ROOT/'import.json').write_text(json.dumps(report,indent=2))
u.log('ORIGINAL_STUMPS_IMPORTED count='+str(len(report)))
