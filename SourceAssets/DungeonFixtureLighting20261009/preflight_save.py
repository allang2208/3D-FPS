from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
def path(x):return x.get_path_name() if x else None
def v(x):return [x.x,x.y,x.z]
out=dict(editor_world=path(ed.get_editor_world()),game_world=path(ed.get_game_world()),dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],maps={})
for target in ['/Game/GameMaps/L_Dungeon_Randomized','/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject']:
    world=u.load_asset(target)
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    rows=[]
    for a in actors:
        for c in a.get_components_by_class(u.LocalLightComponent):
            if target.endswith('L_Dungeon_Randomized') and a.actor_has_tag('DungeonRouteGenerated'):continue
            rows.append(dict(label=a.get_actor_label(),type=c.get_class().get_name(),position=v(c.get_world_location()),forward=v(c.get_forward_vector()),intensity=c.intensity))
    out['maps'][target]=rows
    for g in u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator):
        if target.endswith('L_Dungeon_Randomized'):(ROOT/'Receipts/live-catalog-before.json').write_text(g.get_editor_property('module_catalog_json'),encoding='utf8')
(ROOT/'Receipts/save-preflight.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('LIGHT_SAVE_PREFLIGHT',json.dumps({k:v for k,v in out.items() if k!='maps'}),[(k,len(v)) for k,v in out['maps'].items()])
