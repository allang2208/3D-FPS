"""Scoped main-plaza instancing, shared by the original builder and this integration batch."""
from collections import defaultdict
import hashlib, math
import unreal as u

CELL_CM=1600.0
TAG='ColdSteel.MainPlaza.Generated'
ROLES={'ColdSteel.MainPlaza.Colonnade','ColdSteel.MainPlaza.Entablature',
       'ColdSteel.MainPlaza.Balustrade','ColdSteel.MainPlaza.Precinct'}

def apply():
    api=u.get_editor_subsystem(u.EditorActorSubsystem)
    groups=defaultdict(list)
    rejected=[]
    for actor in api.get_all_level_actors():
        tags={str(t) for t in actor.tags}
        if TAG not in tags or not tags.intersection(ROLES) or not isinstance(actor,u.StaticMeshActor):continue
        policy=u.PlazaInstanceTools.cluster_policy(actor)
        if not policy:
            c=actor.static_mesh_component;m=c.static_mesh
            rejected.append({'actor':actor.get_actor_label(),'mesh':m.get_path_name() if m else None,
                'nanite_enabled':bool(m.get_editor_property('nanite_settings').enabled) if m else False,
                'nanite_triangles':m.get_num_nanite_triangles() if m else 0,
                'mobility':str(c.get_editor_property('mobility')),
                'overlaps':c.get_editor_property('generate_overlap_events'),
                'attached_to':str(actor.get_attach_parent_actor())})
            continue
        p=actor.get_actor_location()
        key=(math.floor(p.x/CELL_CM),math.floor(p.y/CELL_CM),math.floor(p.z/600),hashlib.sha256(policy.encode()).hexdigest()[:16])
        groups[key].append(actor)
    rows=[]
    for key,sources in sorted(groups.items()):
        if len(sources)<2:continue
        originals=[{'label':s.get_actor_label(),'object':s.get_path_name(),
            'transform':str(s.get_actor_transform()),'mesh':s.static_mesh_component.static_mesh.get_path_name()} for s in sources]
        label='PlazaInstances_%d_%d_%d_%s'%key
        result=u.PlazaInstanceTools.create_plaza_cluster(sources,label)
        if not result:raise RuntimeError('Cluster policy changed while applying '+label)
        for source in sources:
            if not api.destroy_actor(source):raise RuntimeError('Cannot retire source after creating '+label+'; preserve unsaved state')
        rows.append({'cluster':result.get_path_name(),'sources':originals,'instances':len(originals)})
    return {'cell_cm':CELL_CM,'clusters':rows,'components_removed':sum(r['instances']-1 for r in rows),
            'eligible_groups':len(groups),'eligible_actors':sum(len(v) for v in groups.values()),'retained_actors':rejected}
