"""Read the live production recipe and fixed entry actors; never generate or save."""
from pathlib import Path
import unreal as u,json
ROOT=Path(__file__).resolve().parent
(ROOT/'Sources').mkdir(parents=True,exist_ok=True)
# Read a World asset without switching the user's current map or ending PIE.
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
g=next(a for a in actors if isinstance(a,u.AuthoredDungeonGenerator))
(ROOT/'Sources/production-catalog.json').write_text(g.get_editor_property('module_catalog_json'),encoding='utf8')
rows=[]
for a in actors:
 if a.actor_has_tag('DungeonRouteGenerated'):continue
 p=a.get_actor_location()
 rows.append(dict(label=a.get_actor_label(),class_name=a.get_class().get_name(),tags=[str(x) for x in a.tags],position=[p.x,p.y,p.z],rotation=str(a.get_actor_rotation()),meshes=[c.static_mesh.get_path_name() for c in a.get_components_by_class(u.StaticMeshComponent) if c.static_mesh]))
(ROOT/'Sources/fixed-actors.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('PRODUCTION_RECIPE_READ',len(rows))
