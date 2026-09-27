"""Reimport V5 geometry into the currently referenced meshes in the live editor.

Keep published object paths stable: the native sword catalog caches paths for
the editor process. Back up the existing packages before replacing geometry.
The editor must be out of PIE. No gameplay, screenshot or acceptance test.
"""
from datetime import datetime
from pathlib import Path
import json
import shutil
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
DATA=ROOT/'Content/ColdSteelData'
spec=json.loads((P/'author_receipt.json').read_text(encoding='utf-8'))
catalog=json.loads((DATA/'highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
items=json.loads((DATA/'items.json').read_text(encoding='utf-8-sig'))
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End current play before reimporting the sword junction.')
world=editor.get_editor_world() if editor else None
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
before=P/'Before'/stamp;before.mkdir(parents=True,exist_ok=True)
receipt={'revision':'JunctionV5','time':stamp,'assets':[],'stable_runtime_paths':True,'complete':False,'tested':False}


def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')


def target_for(row):
    name=row['source_mesh']
    if row['kind']=='world':return items['ue_highland_claymore']['world_mesh']
    if row['kind']=='blade':
        option='highland_broadblade' if name.endswith('Broadblade_ThickV2') else name.removeprefix('SM_Highland_Blade_')
        return catalog['slots']['blade_1'][option]['mesh']
    option='highland_cloven_guard' if name.endswith('_Cloven') else name.removeprefix('SM_Highland_Guard_')
    return catalog['slots']['guard'][option]['mesh']


for row in spec['assets']:
    target=target_for(row)
    if not target.startswith('/Game/Weapons/HighlandClaymore20260922/'):
        raise RuntimeError('Unexpected active Highland mesh: '+target)
    asset=u.load_asset(target)
    if asset is None:raise RuntimeError('Active mesh missing: '+target)
    package=target.split('.')[0]
    destination,name=package.rsplit('/',1)
    disk=ROOT/'Content'/Path(package.removeprefix('/Game/')+'.uasset')
    for suffix in ['.uasset','.uexp','.ubulk']:
        old_file=disk.with_suffix(suffix)
        if old_file.exists():shutil.copy2(old_file,before/old_file.name)
    materials={str(slot.material_slot_name):slot.material_interface for slot in asset.static_materials}
    old_settings=static.get_lod_build_settings(asset,0)
    nanite=asset.get_editor_property('nanite_settings')
    lod_group=asset.get_editor_property('lod_group')
    lods=[]
    lod_count=static.get_lod_count(asset)
    if lod_count>1:
        sizes=static.get_lod_screen_sizes(asset)
        for index in range(lod_count):
            reduction=static.get_lod_reduction_settings(asset,index)
            entry=u.EditorScriptingMeshReductionSettings()
            entry.percent_triangles=reduction.percent_triangles;entry.screen_size=sizes[index];lods.append(entry)
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True
    options.import_materials=False;options.import_textures=False;options.import_animations=False
    cfg=options.static_mesh_import_data
    cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
    cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    cfg.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    cfg.import_uniform_scale=1.;cfg.convert_scene=True;cfg.convert_scene_unit=True;cfg.force_front_x_axis=False
    task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=destination;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True
    task.options=options;task.factory=u.FbxFactory();task.save=False
    A.import_asset_tasks([task])
    asset=u.load_asset(target)
    if asset is None or not task.imported_object_paths:raise RuntimeError('Reimport failed: '+target)
    slots=list(asset.static_materials)
    for slot in slots:
        key=str(slot.material_slot_name)
        material=materials.get(key) or materials.get(key.split('.')[0])
        if material is None and len(materials)==1:material=next(iter(materials.values()))
        if material is None:raise RuntimeError('Unmapped Highland material: '+key)
        slot.material_interface=material
    asset.static_materials=slots
    old_settings.recompute_normals=False;old_settings.recompute_tangents=True
    old_settings.use_mikk_t_space=True;old_settings.use_high_precision_tangent_basis=True
    old_settings.use_full_precision_u_vs=True
    static.set_lod_build_settings(asset,0,old_settings)
    asset.set_editor_property('nanite_settings',nanite);asset.set_editor_property('lod_group',lod_group)
    if lods:
        reductions=u.EditorScriptingMeshReductionOptions()
        reductions.auto_compute_lod_screen_size=False;reductions.reduction_settings=lods
        static.set_lods(asset,reductions)
    L.set_metadata_tag(asset,'HighlandJunctionRevision','JunctionV5_20260927')
    L.set_metadata_tag(asset,'HighlandSource',row['fbx'])
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+target)
    receipt['assets'].append({'asset':asset.get_path_name(),'source':row['fbx'],'saved':True,'backup':str(before/name)+'.uasset'})
    record();print('JUNCTION_V5_SAVED '+target)
receipt['complete']=True;record()
print('JUNCTION_V5_IMPORT_COMPLETE '+str(len(receipt['assets'])))
