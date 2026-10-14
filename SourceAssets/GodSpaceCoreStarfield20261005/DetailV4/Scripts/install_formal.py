"""Install the accepted starfield core at its existing UE identity; never save maps."""
from pathlib import Path
import unreal as u,json,hashlib,runpy,datetime
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[2]
DEST='/Game/Props/GodSpaceCoreStarfield20261005/DetailV4'
PATH='/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceCore'
FBX=PROJECT/'SourceAssets/GodSpaceLayout20260927/Integration/Exported/SM_GodSpaceCore.fbx'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert not (editor and editor.get_game_world()),'Stop PIE before installing assets'
assert FBX.is_file(),FBX
accepted=ROOT/'Authored/SM_GodSpaceCore_Starfield_V4.fbx'
signature=hashlib.sha256(accepted.read_bytes()).hexdigest()
assert hashlib.sha256(FBX.read_bytes()).hexdigest()==signature,'Legacy import source must match accepted core'
dependencies=runpy.run_path(str(ROOT/'Scripts/import_candidate.py'))
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saved':list(dependencies['receipt']['saved']),'source_file':str(FBX),'source_sha256':signature,'formal_path':PATH,'map_saved':False,'shared_materials_modified':False}
mesh=u.load_asset(PATH);assert mesh,'Expected the existing formal core identity'
body=mesh.get_editor_property('body_setup');assert body
collision={name:body.get_editor_property(name) for name in ['agg_geom','collision_trace_flag','double_sided_geometry']}
nanite=mesh.get_editor_property('nanite_settings')
contract=json.loads((ROOT.parent/'formal_contract.json').read_text(encoding='utf-8'))
material_map={name:u.load_asset(DEST+'/Materials/MI_'+name+'_V4') for name in ['Core_Starfield','Core_EngravedGold','Core_Sapphire']}
assert all(material_map.values())
count_api=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
receipt['collision_before']={'simple_count':count_api.get_simple_collision_count(mesh),'trace':str(collision['collision_trace_flag']),'double_sided':collision['double_sided_geometry']}
if E.get_metadata_tag(mesh,'CoreStarfieldInstalledSource')!=signature or E.get_metadata_tag(mesh,'CoreStarfieldRevision')!='20261005-V4-EngineParity':
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
    d=options.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.reorder_material_to_fbx_order=True;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(FBX);task.destination_path=PATH.rsplit('/',1)[0];task.destination_name=PATH.rsplit('/',1)[1];task.factory=u.FbxFactory();task.options=options;task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if E.get_metadata_tag(mesh,'CoreStarfieldPendingSource')!=signature:
        A.import_asset_tasks([task]);mesh=u.load_asset(PATH);assert mesh
        E.set_metadata_tag(mesh,'CoreStarfieldPendingSource',signature)
    # Atomic FBX reimport retains unused old slots. Capture section names first,
    # then install the accepted three slots and remap each actual render section.
    old_slots=list(mesh.get_editor_property('static_materials'))
    sections=[str(old_slots[count_api.get_lod_material_slot(mesh,0,i)].material_slot_name) for i in range(mesh.get_num_sections(0))]
    assert sorted(sections)==sorted(material_map),sections
    candidate=u.load_asset(DEST+'/Meshes/SM_GodSpaceCore_Starfield_V4')
    accepted_slots=list(candidate.get_editor_property('static_materials'));slot_indices={str(x.material_slot_name):i for i,x in enumerate(accepted_slots)}
    mesh.set_editor_property('static_materials',accepted_slots)
    for section,name in enumerate(sections):count_api.set_lod_material_slot(mesh,slot_indices[name],0,section)
    assert len(mesh.get_editor_property('static_materials'))==3
    body=mesh.get_editor_property('body_setup')
    for name,value in collision.items():body.set_editor_property(name,value)
    mesh.set_editor_property('nanite_settings',nanite)
    candidate=u.load_asset(DEST+'/Meshes/SM_GodSpaceCore_Starfield_V4')
    for name in ['negative_bounds_extension','positive_bounds_extension']:mesh.set_editor_property(name,candidate.get_editor_property(name))
    E.set_metadata_tag(mesh,'CoreStarfieldInstalledSource',signature)
    E.remove_metadata_tag(mesh,'CoreStarfieldPendingSource')
    E.set_metadata_tag(mesh,'CoreStarfieldAuthoring','SourceAssets/GodSpaceCoreStarfield20261005/DetailV4/Authored/GodSpaceCore_Starfield_V4_Editable.blend')
    E.set_metadata_tag(mesh,'CoreStarfieldRevision','20261005-V4-EngineParity')
    mesh.modify();assert E.save_loaded_asset(mesh,False),PATH;receipt['saved'].append(mesh.get_path_name())
receipt['collision_after']={'simple_count':count_api.get_simple_collision_count(mesh),'trace':str(body.get_editor_property('collision_trace_flag')),'double_sided':body.get_editor_property('double_sided_geometry')}
assert receipt['collision_after']==receipt['collision_before'],receipt
assert not mesh.get_editor_property('nanite_settings').enabled
b=mesh.get_bounds();assert (b.origin-u.Vector(*contract['origin_cm'])).length()<.01 and (b.box_extent-u.Vector(*contract['half_extent_cm'])).length()<.01
receipt.update(materials=[{'slot':str(x.material_slot_name),'path':x.material_interface.get_path_name()} for x in mesh.get_editor_property('static_materials')],bounds={'origin_cm':[b.origin.x,b.origin.y,b.origin.z],'half_extent_cm':[b.box_extent.x,b.box_extent.y,b.box_extent.z],'culling_sphere_radius_cm':b.sphere_radius,'previous_culling_sphere_radius_cm':contract['culling_sphere_radius_cm']},nanite=False,complete=True)
(ROOT/'Receipts/formal_install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))
