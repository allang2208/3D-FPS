"""Run inside UE Python after coordination with the active editor owner."""
import json
from pathlib import Path
import unreal

SOURCE=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
DEST='/Game/Weapons/AKMReplacement'
contract=json.loads((SOURCE/'akm_replacement_export_report.json').read_text())
assets=unreal.AssetToolsHelpers.get_asset_tools()

def import_file(path,options):
    task=unreal.AssetImportTask();task.filename=str(path);task.destination_path=DEST
    task.automated=True;task.replace_existing=True;task.save=True;task.options=options
    assets.import_asset_tasks([task])
    return list(task.imported_object_paths)

options=unreal.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
options.import_materials=True;options.import_textures=True;options.create_physics_asset=False
mesh_paths=import_file(SOURCE/'SK_AKM_Replacement.fbx',options)
mesh=unreal.load_asset(DEST+'/SK_AKM_Replacement')
if not mesh:
    mesh=next((unreal.load_asset(p)for p in mesh_paths if isinstance(unreal.load_asset(p),unreal.SkeletalMesh)),None)
if not mesh:raise RuntimeError('AKM replacement mesh failed: '+str(mesh_paths))
skeleton=mesh.get_editor_property('skeleton')
animation_paths={}
durations={}
for clip in contract['clips']:
    options=unreal.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal=False;options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
    data=options.anim_sequence_import_data
    data.set_editor_property('use_default_sample_rate',False)
    data.set_editor_property('custom_sample_rate',clip['fps'])
    paths=import_file(SOURCE/('A_AKM_'+clip['clip']+'.fbx'),options)
    animation_paths[clip['clip']]=paths
    anim=unreal.load_asset(DEST+'/A_AKM_'+clip['clip'])
    if not anim:raise RuntimeError('Missing animation '+clip['clip'])
    durations[clip['clip']]=anim.get_play_length()
    if abs(durations[clip['clip']]-clip['duration'])>.011:
        raise RuntimeError('Animation duration changed: '+clip['clip']+' '+str(durations[clip['clip']]))

# FBX does not reliably preserve Blender metal/roughness inputs. Set PBR explicitly.
material_report=[];material_overrides={}
for item in contract['materials']:
    # Interchange creates MaterialInstanceConstant assets for imported FBX slots.
    # Author our editable material under a separate name, then bind each mesh slot.
    name=item['name']+'_PBR';path=DEST+'/'+name;mat=unreal.load_asset(path)
    if not mat:mat=assets.create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(mat)
    col=unreal.MaterialEditingLibrary.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-400,0)
    col.set_editor_property('constant',unreal.LinearColor(*item['color'],1))
    unreal.MaterialEditingLibrary.connect_material_property(col,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for prop,key,y in [(unreal.MaterialProperty.MP_METALLIC,'metallic',140),(unreal.MaterialProperty.MP_ROUGHNESS,'roughness',260)]:
        val=unreal.MaterialEditingLibrary.create_material_expression(mat,unreal.MaterialExpressionConstant,-400,y)
        val.set_editor_property('r',item[key]);unreal.MaterialEditingLibrary.connect_material_property(val,'',prop)
    unreal.MaterialEditingLibrary.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    assert unreal.MaterialEditingLibrary.has_material_usage(mat,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH),path
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False),path
    material_report.append(path)
    material_overrides[item['name']]=mat

slots=mesh.get_editor_property('materials')
for index,slot in enumerate(slots):
    names=[str(slot.get_editor_property('material_slot_name')),str(slot.get_editor_property('imported_material_slot_name'))]
    current=slot.get_editor_property('material_interface')
    if current:names.append(current.get_name())
    for name in names:
        if name in material_overrides:
            slot.set_editor_property('material_interface',material_overrides[name]);slots[index]=slot;break
mesh.set_editor_property('materials',slots)
unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)

unreal.EditorAssetLibrary.save_directory(DEST,only_if_is_dirty=False,recursive=True)
report={'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),'mesh_paths':mesh_paths,
        'animations':animation_paths,'durations':durations,'materials':material_report,
        'arms_replacement_meshes':contract['arms_replacement_meshes'],
        'missing_source_textures':contract['missing_texture_count'],'destination':DEST}
(SOURCE/'akm_replacement_unreal_import_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('AKM_REPLACEMENT_IMPORT_OK '+json.dumps(report))
