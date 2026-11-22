"""Replace the old common sign and the ground-floor crate in the existing village level."""
import json,sys
from pathlib import Path
import unreal as u
from author_shop import require,standing
from TradeSign.layout import placements,OLD_SIGN,OLD_CRATE,SIGN

def apply(project):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'AbandonedVillage'))
    from shop_pendants import component,remove_components
    data=json.loads((project/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
    house=next(h for h in data['houses'] if h[0]==data['blacksmith']['house'])
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    by_label={a.get_actor_label():a for a in actors.get_all_level_actors()}
    common=by_label['Village_Blacksmith_Common']
    repaired=by_label['Village_Blacksmith_Repaired']
    frames=placements(house)
    def find(actor,path):
        return [c for c in actor.get_components_by_class(u.StaticMeshComponent)
                if c.static_mesh and c.static_mesh.get_path_name().split('.')[0]==path]
    old=find(common,OLD_SIGN)
    current=find(common,SIGN)
    suspended=any('VillageShop.SmithBracket' in map(str,c.component_tags) for c in common.get_components_by_class(u.StaticMeshComponent))
    if len(old)+len(current)+int(suspended)!=1:raise RuntimeError('Cannot identify the existing blacksmith sign')
    if old and isinstance(old[0],u.InstancedStaticMeshComponent) and old[0].get_instance_count()!=1:
        raise RuntimeError('Unexpected number of original sign instances')
    anchor=standing(house,OLD_CRATE,300,-300,0,0,.58).translation
    crates=[(c,i) for c in find(repaired,OLD_CRATE) for i in range(c.get_instance_count())
            if (c.get_instance_transform(i,True).translation-anchor).length()<1.]
    if len(crates)!=(1 if old else 0):raise RuntimeError('Ground-floor crate bay changed')
    common.modify();repaired.modify()
    if old:remove_components(common,old)
    for c,i in crates:
        c.modify()
        if not c.remove_instance(i):raise RuntimeError('Could not free ground-floor crate bay')
    report=[]
    for state,path,t,profile in frames:
        if suspended and path==SIGN:continue
        host=common if state=='Common' else repaired
        parts=find(host,path)
        if len(parts)>1:raise RuntimeError('Duplicate smith prop '+path)
        if parts:remove_components(host,parts)
        c=component(host,u.HierarchicalInstancedStaticMeshComponent)
        c.set_mobility(u.ComponentMobility.STATIC)
        c.set_static_mesh(require(path))
        c.set_collision_profile_name(profile)
        c.set_editor_property('generate_overlap_events',False)
        c.set_editor_property('receives_decals',False)
        c.component_tags=(['VillageShop.Repaired'] if state=='Repaired' else [])+(['VillageShop.NoCollision'] if profile=='NoCollision' else [])
        if state=='Repaired':
            c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.add_instances([t],False,True,False)
        report.append(dict(mesh=path,state=state,world_cm=[t.translation.x,t.translation.y,t.translation.z],
                           yaw=t.rotation.rotator().yaw))
    return report
