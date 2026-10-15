from pathlib import Path
import json,hashlib,unreal as u
ROOT=Path(__file__).resolve().parent
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
actors=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(actors)!=1:raise RuntimeError('Expected the saved production generator')
raw=actors[0].get_editor_property('module_catalog_json');catalog=json.loads(raw)
modules=[m for m in catalog['modules'] if m['id'] in ('AbandonedIncineratorHall','AbandonedFlueGasStation')]
if len(modules)!=2:raise RuntimeError('Missing production rooms')
bp=u.load_asset('/Game/Monsters/IncineratorBossM66/BP_M66RigPreview');cdo=u.get_default_object(bp.generated_class())
cap=cdo.get_editor_property('capsule_component');mesh=cdo.get_editor_property('mesh')
report=dict(source='/Game/GameMaps/L_Dungeon_Randomized',catalog_sha256=hashlib.sha256(raw.encode()).hexdigest(),modules=modules,
 monster=dict(radius=cap.get_unscaled_capsule_radius(),half_height=cap.get_unscaled_capsule_half_height(),mesh=cdo.get_editor_property('visual_mesh').get_path_name(),
 land=cdo.get_editor_property('land_clip').get_path_name(),get_up=cdo.get_editor_property('get_up_clip').get_path_name()))
(ROOT/'Records/production_rooms.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('M66_STAIR_SOURCE '+json.dumps(dict(monster=report['monster'],parts={m['id']:len(m['parts']) for m in modules})))
