"""Import independent modules and the unchanged arm animation carrier."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/FrostCrystalSword20260915/Modules20260915'
rows=json.loads((P/'exports.json').read_text());A=u.AssetToolsHelpers.get_asset_tools()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
donor=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/SK_FrostCrystalSword_Manny')
finish=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze')
receipt=[]
def import_asset(name,skeletal=False):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.create_physics_asset=False
    data=opt.skeletal_mesh_import_data if skeletal else opt.static_mesh_import_data
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    if skeletal:opt.skeleton=donor.skeleton;data.set_editor_property('update_skeleton_reference_pose',False)
    else:data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=D;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
    asset=u.load_asset(D+'/'+name)
    if not asset or not task.imported_object_paths:raise RuntimeError('Import failed '+name)
    if skeletal:
        bindings={str(s.material_slot_name):s.material_interface for s in donor.get_editor_property('materials')}
        slots=asset.get_editor_property('materials')
        for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
        asset.set_editor_property('materials',slots)
        asset.set_editor_property('positive_bounds_extension',u.Vector(120,120,120));asset.set_editor_property('negative_bounds_extension',u.Vector(120,120,120))
    else:
        for i,s in enumerate(asset.static_materials):asset.set_material(i,finish)
    u.EditorAssetLibrary.save_loaded_asset(asset,False);receipt.append({'source':task.filename,'asset':asset.get_path_name()});return asset
arms=import_asset(rows['arms'],True)
catalog={'version':1,'weapon':'ue_frost_crystal_sword','interface':'frost_hilt_v1','arms_mesh':arms.get_path_name(),'drive_bone':'WPN_root','slots':{}}
for row in rows['parts']:
    asset=import_asset(row['mesh'])
    spec={'mesh':asset.get_path_name(),'location_cm':row['location_cm'],'interface':'frost_hilt_v1'}
    if row['slot']=='blade_1':spec['rune_dimensions_cm']=[12,10,63]
    catalog['slots'].setdefault(row['slot'],{})[row['id']]=spec
# The compiler derives the mount from matching original source vertices, so
# FBX axis conversion and 100x bone scale are resolved once during authoring.
(P/'catalog_base.json').write_text(json.dumps(catalog,indent=2))
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
u.log('FROST_SWORD_MODULES_IMPORTED')
