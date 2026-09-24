"""Bind concrete only to dungeon mineral slots and publish saved wall variants to the live catalog."""
import json,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized';E=u.EditorAssetLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active')
if list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):raise RuntimeError('Preserve unsaved map before switching')
if json.loads((ROOT/'Receipts/meshes.json').read_text())['stage']!='meshes_saved':raise RuntimeError('Finish mesh imports first')
materials=json.loads((ROOT/'Config/material-remap.json').read_text());variants=json.loads((ROOT/'Config/mesh-variants.json').read_text())
variant_paths={p for values in variants.values() for p in values}
loaded={p:u.load_asset(p) for p in materials.values()}
if not all(loaded.values()) or not all(E.does_asset_exist(p) for p in variant_paths):
    raise RuntimeError('A saved wall dependency is missing')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith('/Game/Dungeons/') for p in dirty):raise RuntimeError('Preserve unsaved dungeon packages')
receipt_path=ROOT/'Receipts/install.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(stage='binding',material_slots={},preview_skins=[],runtime_tested=False)
def record():receipt_path.write_text(json.dumps(receipt,indent=2))
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
def bind_mesh_materials(path):
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.StaticMesh):return
    changes=[]
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        old=slot.material_interface.get_path_name().split('.')[0] if slot.material_interface else ''
        if old in materials:
            mesh.set_material(i,loaded[materials[old]]);changes.append(dict(slot=i,before=old,after=materials[old]))
    if changes:receipt['material_slots'][path]=changes;save(mesh);record()

# Do not retain 77 new surfaces while loading every legacy dungeon mesh. Keep
# each binding's UObject references local, then release completed batches before
# loading the map; distance-field jobs otherwise overlap with map serialization.
mesh_paths=[p for p in E.list_assets('/Game/Dungeons',recursive=True,include_folder=False)
    if p.rsplit('/',1)[-1].startswith('SM_') and p.split('.')[0] not in variant_paths]
for index,path in enumerate(mesh_paths):
    bind_mesh_materials(path)
    if (index+1)%8==0:u.collect_garbage()
u.collect_garbage()
loaded.update({p:u.load_asset(p) for p in variant_paths})
if not all(loaded.values()):raise RuntimeError('Cannot load a saved surface variant')
backup=ROOT/'Sources/L_Dungeon_Randomized-before-wall-damage.umap'
if not backup.exists():shutil.copy2(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap',backup)
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Cannot load dungeon')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one authored dungeon generator')
g=generators[0];previous=g.get_editor_property('module_catalog_json')
backup_catalog=ROOT/'Sources/catalog-before-wall-damage.json'
if not backup_catalog.exists():backup_catalog.write_text(previous,encoding='utf-8')
catalog=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend'](json.loads(previous))
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
retired_refs=set(variants)|set(materials)
refs={a.get_path_name():a for a in g.get_editor_property('module_assets') if a and a.get_path_name().split('.')[0] not in retired_refs}
refs.update({a.get_path_name():a for a in loaded.values()});g.set_editor_property('module_assets',list(refs.values()))
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.get_editor_property('static_mesh');old=mesh.get_path_name().split('.')[0] if mesh else ''
        if old in variants:
            component.modify();component.set_static_mesh(loaded[variants[old][0]])
            # New tile meshes retain the same canonical material-slot list as their source.
            if old.startswith('/Game/Dungeons/AtmosphereV2/TileFracture/'):
                component.set_editor_property('override_materials',[])
            receipt['preview_skins'].append(dict(actor=actor.get_actor_label(),before=old,after=variants[old][0]))
        for i,mat in enumerate(component.get_editor_property('override_materials')):
            key=mat.get_path_name().split('.')[0] if mat else ''
            if key in materials:component.modify();component.set_material(i,loaded[materials[key]])
save(world)
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
receipt.update(stage='map_saved',map=TARGET,material_families=len(materials),variant_meshes=sum(len(v) for v in variants.values()),
    fixed_start_skins=8,random_surface_families=sum(len(v)>1 for v in variants.values()))
record();print('DUNGEON_WALL_DAMAGE_INSTALLED',len(receipt['material_slots']),receipt['variant_meshes'],flush=True)
