"""Install the connector repair and bind Fab finishes only to dungeon-owned meshes/maps."""
import json
import re
import shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if editor and editor.get_game_world():raise RuntimeError('PIE active; preserve the running game')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
dirty+=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
unfinished='/Game/Dungeons/SeamMetal20260923/Materials/M_FabIndustrialMetal'
if any((p.get_name().startswith('/Game/Dungeons/') or TARGET in p.get_name()) and p.get_name()!=unfinished for p in dirty):
    raise RuntimeError('Preserve unsaved dungeon packages before installation')
if list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):
    raise RuntimeError('Preserve unsaved map before switching to dungeon')
materials=json.loads((ROOT/'Receipts/materials.json').read_text(encoding='utf-8'))
if materials['stage']!='materials_saved':raise RuntimeError('Materials must be saved first')
mapping=materials['materials'];loaded={}
for old,new in mapping.items():
    obj=u.load_asset(new)
    if not obj:raise RuntimeError('New material missing '+new)
    loaded[old]=obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
def mapped(path):
    key=path.split('.')[0]
    return mapping.get(key,path)
receipt_file=ROOT/'Receipts/install.json'
receipt=dict(stage='connector_import',meshes=[],material_slots={},runtime_tested=False)
def record():receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record()
manifest=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
base='/Game/Dungeons/Treasure20260922/Meshes'
for item in manifest['objects']:
    path=base+'/'+item['name']
    old=u.load_asset(path)
    if not old:raise RuntimeError('Original connector missing '+path)
    backup=ROOT/'Sources'/('Before_'+item['name']+'.uasset')
    if not backup.exists():shutil.copy2(PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset'),backup)
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=base;task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    mesh=u.load_asset(path)
    if not mesh or not task.get_objects():raise RuntimeError('Connector import failed '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));source=item['materials'][key]
        mat=u.load_asset(mapped(source))
        if not mat:raise RuntimeError('Connector material missing '+source)
        mesh.set_material(index,mat)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True;settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.0;settings.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',settings);save(mesh)
    receipt['meshes'].append(path);record()
receipt['stage']='material_binding';record()
# Keep original vendor packages and shared weapons/UI untouched. Store exact slot
# bindings for a scoped material-only reversal, without duplicating every mesh.
for path in E.list_assets('/Game/Dungeons',recursive=True,include_folder=False):
    if not path.rsplit('/',1)[-1].startswith('SM_'):continue
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.StaticMesh):continue
    changes=[]
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        source=slot.material_interface.get_path_name() if slot.material_interface else ''
        key=source.split('.')[0]
        if key in loaded:
            changes.append(dict(slot=index,before=source,after=loaded[key].get_path_name()))
    if not changes:continue
    receipt['material_slots'][path]=changes;record()
    for row in changes:mesh.set_material(row['slot'],loaded[row['before'].split('.')[0]])
    save(mesh)
receipt['stage']='catalog';record()
backup=ROOT/'Sources/L_Dungeon_Randomized-before-seam-metal.umap'
if not backup.exists():shutil.copy2(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap',backup)
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Cannot load dungeon map for catalog update')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one generator')
g=generators[0];previous=g.get_editor_property('module_catalog_json')
backup=ROOT/'Sources/catalog-before-seam-metal.json'
if not backup.exists():backup.write_text(previous,encoding='utf-8')
def replace(value):
    if isinstance(value,str):return mapped(value)
    if isinstance(value,list):return [replace(x) for x in value]
    if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
    return value
catalog=replace(json.loads(previous))
link=next(m for m in catalog['modules'] if m['id']=='TreasureLink')
link['min']=[-180,-200,-22];link['max']=[180,0,302]
link['cells']=[dict(min=link['min'],max=link['max'])]
link['portal_geometry']=dict(owner='adjoining_room',frame_depth_cm=29,skin_setback_cm=15,reveal_recess_cm=4)
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
assets={x.get_path_name():x for x in g.get_editor_property('module_assets') if x}
assets.update({x.get_path_name():x for x in loaded.values()})
g.set_editor_property('module_assets',list(assets.values()))
# Existing editor-preview overrides must not mask the new mesh slots. Runtime
# layout and actors are still rebuilt only on the user's next dungeon entry.
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        for index,mat in enumerate(component.get_editor_property('override_materials')):
            key=mat.get_path_name().split('.')[0] if mat else ''
            if key in loaded:component.modify();component.set_material(index,loaded[key])
save(world)
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
receipt.update(stage='map_saved',map=TARGET,material_families=len(mapping),changed_meshes=len(receipt['material_slots']),
    geometry_contract='room owns reveal; connector recessed 4cm; tiles trimmed 15cm at both ends')
record();print('DUNGEON_SEAM_METAL_INSTALLED',receipt['changed_meshes'],receipt['material_families'],flush=True)
