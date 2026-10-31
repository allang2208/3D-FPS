"""Read the reported missing foliage and the PCG authoring API; no level writes."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
out={'actors':[],'api':{}}
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=a.get_actor_label()
    if not label.startswith('NB28_'):continue
    row={'label':label,'location':str(a.get_actor_location()),'root_mobility':str(a.root_component.mobility),'components':[]}
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=c.static_mesh
        row['components'].append({'name':c.get_name(),'count':c.get_instance_count(),'mesh':mesh.get_path_name() if mesh else None,'visible':c.get_editor_property('visible'),'hidden_in_game':c.get_editor_property('hidden_in_game'),'component_transform':str(c.get_world_transform()),'first_instance_world':str(c.get_instance_transform(0,True)) if c.get_instance_count() else None,'materials':[x.get_path_name() if x else None for x in c.get_materials()],'bounds':str(c.get_local_bounds())})
    out['actors'].append(row)
for n in ('PCGToolset','PCGSpatialToolset','Object','PCGComponent','PCGSubsystem','PCGGraphInstance'):
    cls=getattr(u,n,None)
    out['api'][n]=[x for x in dir(cls or []) if any(k in x for k in ('graph','param','generat','execute','call_method','tick','python','serialize'))]
    if cls and n=='Object':out['api']['call_method_doc']=str(cls.call_method.__doc__)
(R/'saved_scene_read.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('NEAR_BANK_READ_SAVED',len(out['actors']),sum(c['count'] for a in out['actors'] for c in a['components']),out['api'],flush=True)
