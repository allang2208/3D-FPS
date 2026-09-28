"""Read the reported handrail mesh and its placed collision configuration."""
import unreal as u,json
from pathlib import Path
R=Path(__file__).parent/'RailRepair';R.mkdir(exist_ok=True)
e=u.get_editor_subsystem(u.UnrealEditorSubsystem);w=e.get_game_world() or e.get_editor_world()
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
def v(p):return [p.x,p.y,p.z]
out={'world':str(w),'assets':{},'components':[]}
for name in ['SM_RomanRail_200','SM_RomanBaluster_Small']:
    m=u.load_asset('/Game/Props/RomanColumn20260915/'+name)
    bs=m.get_editor_property('body_setup');b=m.get_bounding_box();ag=bs.get_editor_property('agg_geom')
    data={'bounds':[v(b.min),v(b.max)],'trace':str(bs.get_editor_property('collision_trace_flag')),'simple_count':S.get_simple_collision_count(m),'boxes':[],'convex_count':len(ag.get_editor_property('convex_elems')),'sphere_count':len(ag.get_editor_property('sphere_elems')),'capsule_count':len(ag.get_editor_property('sphyl_elems'))}
    for box in ag.get_editor_property('box_elems'):
        data['boxes'].append({k:str(box.get_editor_property(k)) for k in ['center','rotation','x','y','z']})
    out['assets'][name]=data
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    for c in a.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        if not m or m.get_name() not in out['assets']:continue
        out['components'].append({'actor':a.get_name(),'label':a.get_actor_label(),'component':c.get_name(),'mesh':m.get_name(),'tags':[str(t) for t in a.tags],'transform':str(c.get_world_transform()),'enabled':str(c.get_collision_enabled()),'profile':str(c.get_collision_profile_name()),'pawn':str(c.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)),'visibility':str(c.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY)),'instances':c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1})
(R/'collision-before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'world':out['world'],'assets':out['assets'],'components':len(out['components']),'profiles':list({str((x['mesh'],x['enabled'],x['profile'],x['pawn'],x['visibility'])) for x in out['components']}),'pieces':sum(x['instances'] for x in out['components'])}))
