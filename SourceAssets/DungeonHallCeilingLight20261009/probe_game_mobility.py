"""Reproduce the rejected rotation in an initialized PIE world, with invisible temporary lights."""
from pathlib import Path
import json, math
import unreal as u
ROOT=Path(__file__).resolve().parent
worlds=list(u.EditorLevelLibrary.get_pie_worlds(False))
world=next((w for w in worlds if 'L_Dungeon_Randomized' in w.get_path_name()),None)
if not world:world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world or 'UEDPIE_' not in world.get_path_name():raise RuntimeError('Needs an actual initialized PIE world, not a blank editor world')
catalog=json.loads((ROOT.parents[1]/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json').read_text('utf8'))
api=u.get_default_object(u.GameplayStatics)
def vec(v):return [v.x,v.y,v.z]
rows=[]
print('HALL_MOBILITY_PROBE_BEGIN',world.get_path_name())
for module in catalog['modules']:
    for index,l in enumerate(module['lights']):
        cls={'spot':u.SpotLight,'rect':u.RectLight,'point':u.PointLight}[l['type']]
        local=u.Rotator(pitch=l.get('pitch',-90 if l['type']!='point' else 0),yaw=l.get('yaw',0),roll=l.get('roll',0))
        for yaw in (0,90,180,270):
            rotation=u.MathLibrary.compose_rotators(local,u.Rotator(pitch=0,yaw=yaw,roll=0))
            expected=vec(u.MathLibrary.get_forward_vector(rotation))
            position=u.Vector(0,0,-100000)
            pose=u.Transform(location=position,rotation=rotation,scale=u.Vector(1,1,1))
            actor=api.call_method('BeginDeferredActorSpawnFromClass',(world,cls.static_class(),pose,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            try:
                component=actor.get_component_by_class(u.LocalLightComponent)
                component.set_visibility(False);component.set_intensity(0.)
                api.call_method('FinishSpawningActor',(actor,pose,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
                spawned=vec(component.get_forward_vector())
                # This is the previous fix's order: the game rejects this move.
                actor.set_actor_location_and_rotation(position,rotation,False,True)
                rejected=vec(component.get_forward_vector())
                component.set_mobility(u.ComponentMobility.MOVABLE)
                actor.set_actor_location_and_rotation(position,rotation,False,True)
                corrected=vec(component.get_forward_vector())
                if math.dist(corrected,expected)>.001:raise RuntimeError('Still wrong in PIE: '+module['id']+'/'+str(index))
                rows.append(dict(module=module['id'],index=index,id=l.get('id'),type=l['type'],room_yaw=yaw,
                    spawned=spawned,before_movable=rejected,after_movable=corrected,expected=expected,
                    previous_fix_failed=math.dist(rejected,expected)>.001))
            finally:
                actor.destroy_actor()
wrong={(r['module'],r['index']) for r in rows if r['previous_fix_failed']}
report=dict(stage='initialized_game_world_direction_checked',world=world.get_path_name(),rows=rows,
    light_count=sum(len(m['lights']) for m in catalog['modules']),cases=len(rows),previous_fix_failed_lights=len(wrong),
    saved=False,lights_invisible=True,temporary_lights_destroyed=True)
(ROOT/'Receipts/game-mobility-directions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HALL_MOBILITY_PROBE_END',len(rows),'cases;',len(wrong),'previously rejected lights; corrected game-world directions passed')
