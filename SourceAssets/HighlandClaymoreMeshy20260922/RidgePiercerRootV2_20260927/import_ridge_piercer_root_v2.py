"""Reimport only the active ridge-piercer mesh and its menu icon, in-place.

Preserve runtime paths, material bindings, LOD policy, catalogs and gameplay.
Use the current editor bridge when UE is open; otherwise use a commandlet.
"""
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
DATA=ROOT/'Content/ColdSteelData'
spec=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
catalog=json.loads((DATA/'highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
target=catalog['slots']['blade_1']['highland_ridge_piercer']['mesh']
package=target.split('.')[0]
if package!='/Game/Weapons/HighlandClaymore20260922/RidgePiercer20260927/SM_Highland_Blade_RidgePiercer_V1':
    raise RuntimeError('Ridge-piercer asset identity changed; preserve the current catalog: '+target)
icon_file=DATA/'AttachmentIcons20260913'/spec['icon']
icon_package='/Game/ColdSteelData/AttachmentIcons20260913/'+icon_file.stem
L=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End active play before replacing the ridge-piercer geometry.')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection({package,icon_package}):
    raise RuntimeError('Preserved unsaved edits in target assets: '+str(dirty.intersection({package,icon_package})))
world=editor.get_editor_world() if editor else None
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
mesh=u.load_asset(target)
if mesh is None:raise RuntimeError('Active ridge-piercer asset missing: '+target)
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
before=P/'Before'/stamp
before.mkdir(parents=True,exist_ok=True)
receipt={'revision':spec['revision'],'time':stamp,'editor_pid':os.getpid(),
         'complete':False,'assets':[],'stable_runtime_paths':True,
         'gameplay_catalog_changed':False,'module_catalog_changed':False,
         'native_build_required':False,'tested':False}

def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')

def backup(package_name):
    disk=ROOT/'Content'/Path(package_name.removeprefix('/Game/')+'.uasset')
    for suffix in ['.uasset','.uexp','.ubulk']:
        file=disk.with_suffix(suffix)
        if file.exists():shutil.copy2(file,before/file.name)

def save(asset,source):
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
    receipt['assets'].append({'asset':asset.get_path_name(),'source':str(source),'saved':True})
    record()

backup(package)
backup(icon_package)
if icon_file.exists():shutil.copy2(icon_file,before/icon_file.name)
record()
materials={str(slot.material_slot_name):slot.material_interface for slot in mesh.static_materials}
settings=static.get_lod_build_settings(mesh,0)
nanite=mesh.get_editor_property('nanite_settings')
lod_group=mesh.get_editor_property('lod_group')
lods=[]
if static.get_lod_count(mesh)>1:
    sizes=static.get_lod_screen_sizes(mesh)
    for index in range(static.get_lod_count(mesh)):
        row=u.EditorScriptingMeshReductionSettings()
        row.percent_triangles=static.get_lod_reduction_settings(mesh,index).percent_triangles
        row.screen_size=sizes[index]
        lods.append(row)
options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal=False
options.import_mesh=True
options.import_materials=False
options.import_textures=False
options.import_animations=False
cfg=options.static_mesh_import_data
cfg.combine_meshes=True
cfg.auto_generate_collision=False
cfg.generate_lightmap_u_vs=False
cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
cfg.vertex_color_import_option=u.VertexColorImportOption.REPLACE
cfg.import_uniform_scale=1.
cfg.convert_scene=True
cfg.convert_scene_unit=True
cfg.force_front_x_axis=False
destination,name=package.rsplit('/',1)
task=u.AssetImportTask()
task.filename=spec['fbx']
task.destination_path=destination
task.destination_name=name
task.options=options
task.factory=u.FbxFactory()
task.automated=True
task.replace_existing=True
task.replace_existing_settings=True
task.save=False
A.import_asset_tasks([task])
mesh=u.load_asset(target)
if mesh is None or not task.imported_object_paths:raise RuntimeError('Root V2 FBX import failed')
slots=list(mesh.static_materials)
for slot in slots:
    key=str(slot.material_slot_name)
    mat=materials.get(key) or materials.get(key.split('.')[0])
    if mat is None and len(materials)==1:mat=next(iter(materials.values()))
    if mat is None:raise RuntimeError('Unmapped material slot: '+key)
    slot.material_interface=mat
mesh.static_materials=slots
settings.recompute_normals=False
settings.recompute_tangents=True
settings.use_mikk_t_space=True
settings.use_high_precision_tangent_basis=True
settings.use_full_precision_u_vs=True
static.set_lod_build_settings(mesh,0,settings)
mesh.set_editor_property('nanite_settings',nanite)
mesh.set_editor_property('lod_group',lod_group)
if lods:
    reductions=u.EditorScriptingMeshReductionOptions()
    reductions.auto_compute_lod_screen_size=False
    reductions.reduction_settings=lods
    static.set_lods(mesh,reductions)
L.set_metadata_tag(mesh,'HighlandBladeRevision',spec['revision'])
L.set_metadata_tag(mesh,'HighlandJunctionRevision','JunctionV5_20260927')
L.set_metadata_tag(mesh,'HighlandSource',spec['fbx'])
save(mesh,spec['fbx'])
shutil.copy2(P/'Icons'/spec['icon'],icon_file)
it=u.AssetImportTask()
it.filename=str(icon_file)
it.destination_path='/Game/ColdSteelData/AttachmentIcons20260913'
it.destination_name=icon_file.stem
it.factory=u.TextureFactory()
it.automated=True
it.replace_existing=True
it.save=False
A.import_asset_tasks([it])
icon=u.load_asset(icon_package)
if icon is None or not it.imported_object_paths:raise RuntimeError('Root V2 icon import failed')
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property('srgb',True)
save(icon,icon_file)
receipt['complete']=True
record()
print('HIGHLAND_RIDGE_PIERCER_ROOT_V2_INSTALLED '+target)
