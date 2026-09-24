"""Read only the reported dungeon material and connector state from the owning editor."""
import json,os
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
for name in ('Sources','Receipts','Config','Authored'):(ROOT/name).mkdir(parents=True,exist_ok=True)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=(ue.get_game_world() or ue.get_editor_world()) if ue else None
out=dict(world=world.get_path_name() if world else 'asset commandlet',pie=bool(ue and ue.get_game_world()),meshes={},materials={},dirty=[])
catalog=json.loads((PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').read_text())
for generator in (u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator) if world else []):
    text=generator.get_editor_property('module_catalog_json')
    (ROOT/'Sources/loaded-catalog.json').write_text(text,encoding='utf-8')
    (ROOT/'Sources/loaded-layout.json').write_text(generator.get_editor_property('layout_manifest_json'),encoding='utf-8')
    catalog=json.loads(text);break
paths=set()
for module in catalog['modules']:
    if module['id'] in ('Transit','Threshold','RouteElbow','Distribution'):
        paths.update(p['mesh'] for p in module.get('parts',[]))
for path in sorted(paths):
    mesh=u.load_asset(path)
    if not mesh:out['meshes'][path]={'missing':True};continue
    settings=mesh.get_editor_property('nanite_settings')
    row={'triangles':mesh.get_num_triangles(0),'nanite':{},'materials':[]}
    for key in ('enabled','explicit_tangents','keep_percent_triangles','trim_relative_error','fallback_percent_triangles','fallback_relative_error'):
        row['nanite'][key]=str(settings.get_editor_property(key))
    for slot in mesh.get_editor_property('static_materials'):
        material=slot.material_interface
        row['materials'].append({'slot':str(slot.material_slot_name),'path':material.get_path_name() if material else None})
        if not material:continue
        base=material.get_base_material();key=base.get_path_name()
        if key not in out['materials']:
            out['materials'][key]={p:bool(base.get_editor_property(p)) for p in ('used_with_instanced_static_meshes','used_with_nanite','automatically_set_usage_in_editor')}
    out['meshes'][path]=row
out['dirty']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith('/Game/Dungeons/')]
snapshot=os.environ.get('DUNGEON_SURFACE_SNAPSHOT','inputs')
(ROOT/'Receipts'/(snapshot+'.json')).write_text(json.dumps(out,indent=2),encoding='utf-8')
missing={p:row for p,row in out['materials'].items() if not row['used_with_instanced_static_meshes'] or not row['used_with_nanite']}
print('DUNGEON_SURFACE_INPUTS',json.dumps(dict(world=out['world'],pie=out['pie'],meshes=len(out['meshes']),missing_usage=missing,dirty=out['dirty'])),flush=True)
