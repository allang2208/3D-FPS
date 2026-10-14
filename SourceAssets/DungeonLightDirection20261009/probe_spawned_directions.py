"""Instantiate every catalog light through native deferred spawning, not editor factories."""
from pathlib import Path
import json,math,collections
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Use an isolated commandlet; never replace a live editor scene')
catalog=json.loads((PROJECT/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json').read_text('utf8'))
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
statics=u.get_default_object(u.GameplayStatics)
def vec(v):return [v.x,v.y,v.z]
def direction(rotation):return vec(u.MathLibrary.get_forward_vector(rotation))
def error(a,b):return math.dist(a,b)
def spawn(cls,rotation):
    t=u.Transform(location=u.Vector(0,0,600),rotation=rotation,scale=u.Vector(1,1,1))
    a=statics.call_method('BeginDeferredActorSpawnFromClass',(world,cls.static_class(),t,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    if not a:raise RuntimeError('Native spawning failed')
    statics.call_method('FinishSpawningActor',(a,t,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    return a
rows=[];legacy_bad=[]
for m in catalog['modules']:
    for i,l in enumerate(m['lights']):
        kind=l['type'];cls={'spot':u.SpotLight,'rect':u.RectLight,'point':u.PointLight}[kind]
        local=u.Rotator(pitch=l.get('pitch',-90 if kind!='point' else 0),yaw=l.get('yaw',0),roll=l.get('roll',0))
        for room_yaw in (0,90,180,270):
            q=u.MathLibrary.compose_rotators(local,u.Rotator(pitch=0,yaw=room_yaw,roll=0))
            # Reproduce the exact old spot branch: a -90 spawn pose composed
            # with ASpotLight's own -90 root default, ignoring room orientation.
            requested=u.Rotator(pitch=-90,yaw=0,roll=0) if kind=='spot' else q
            a=spawn(cls,requested);c=a.get_component_by_class(u.LocalLightComponent)
            before=vec(c.get_forward_vector());expected=direction(q)
            if error(before,expected)>.001:legacy_bad.append(dict(module=m['id'],index=i,room_yaw=room_yaw,actual=before,expected=expected))
            a.set_actor_location_and_rotation(u.Vector(0,0,600),q,False,True)
            after=vec(c.get_forward_vector())
            if error(after,expected)>.001:raise RuntimeError('Spawned component still points incorrectly: '+m['id']+'/'+str(i))
            rows.append(dict(module=m['id'],index=i,id=l.get('id'),type=kind,room_yaw=room_yaw,
                expected=expected,before=before,after=after,angle_error_before_deg=math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(before,expected)))))),
                ceiling_center_is_in_cone_after=(after[2]>math.cos(math.radians(l.get('outer_cone_degrees',65)))) if kind=='spot' else None))
            a.destroy_actor()
# Independently cover authored tilted spot directions and all axes. The old
# yaw-only setter discarded pitch; the final world pose must retain it.
orientation_cases=[]
for p,y,r in [(-60,37,0),(-90,125,43),(-30,-82,17),(0,180,0)]:
    q=u.Rotator(pitch=p,yaw=y,roll=r);a=spawn(u.SpotLight,q);a.set_actor_rotation(q,True)
    actual=vec(a.get_component_by_class(u.LocalLightComponent).get_forward_vector())
    if error(actual,direction(q))>.001:raise RuntimeError('Tilted fixture failed')
    orientation_cases.append(dict(rotation=[p,y,r],actual=actual));a.destroy_actor()
result=dict(stage='native_spawn_component_directions_checked',engine_version=u.SystemLibrary.get_engine_version(),
    light_count=sum(len(m['lights']) for m in catalog['modules']),rows=rows,legacy_bad=legacy_bad,
    actual_legacy_bad_lights=len({(r['module'],r['index']) for r in legacy_bad}),orientation_cases=orientation_cases,
    map_saved=False,game_run=False,rendered=False)
(ROOT/'Receipts/native-spawn-directions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('NATIVE_LIGHT_DIRECTIONS',result['light_count'],'lights;',len(rows),'created component cases;',result['actual_legacy_bad_lights'],'legacy wrong-direction lights;',len(orientation_cases),'tilted spot cases; corrected cases passed')
