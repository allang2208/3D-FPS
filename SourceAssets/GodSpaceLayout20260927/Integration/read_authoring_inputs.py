"""Read the saved hub's authoring inputs; no gameplay, asset writes or rendering."""
import json
from pathlib import Path
import unreal as u

root = Path(__file__).parent
world = u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting')
if not world:
    raise RuntimeError('Hub package could not be loaded')
def xyz(v): return [v.x, v.y, v.z]
def transform(t):
    r=t.rotation.rotator()
    return dict(location=xyz(t.translation),rotation=[r.pitch,r.yaw,r.roll],scale=xyz(t.scale3d))
rows=[]
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    row=dict(label=a.get_actor_label(),name=a.get_name(),cls=a.get_class().get_path_name(),tags=[str(t) for t in a.tags],transform=transform(a.get_actor_transform()),components=[])
    for c in a.get_components_by_class(u.ActorComponent):
        if not isinstance(c,(u.StaticMeshComponent,u.SkyAtmosphereComponent,u.VolumetricCloudComponent,u.ExponentialHeightFogComponent)): continue
        d=dict(name=c.get_name(),cls=c.get_class().get_name(),transform=transform(c.get_world_transform()))
        if isinstance(c,u.StaticMeshComponent):
            m=c.static_mesh
            d.update(mesh=m.get_path_name() if m else None,materials=[x.get_path_name() if x else None for x in c.get_materials()],visible=c.is_visible(),hidden=c.get_editor_property('hidden_in_game'))
            if m: d['bounds']=[xyz(m.get_bounding_box().min),xyz(m.get_bounding_box().max)]
            if isinstance(c,u.InstancedStaticMeshComponent):d['instances']=[transform(c.get_instance_transform(i,world_space=True)) for i in range(c.get_instance_count())]
        else:
            props=['layer_bottom_altitude','layer_height','material','planet_radius','trace_max_distance','view_sample_count_scale'] if isinstance(c,u.VolumetricCloudComponent) else ['transform_mode','bottom_radius'] if isinstance(c,u.SkyAtmosphereComponent) else ['fog_density','fog_height_falloff','start_distance']
            for p in props:
                try:
                    v=c.get_editor_property(p)
                    d[p]=v.get_path_name() if isinstance(v,u.Object) else str(v)
                except Exception: pass
        row['components'].append(d)
    rows.append(row)
(root/'saved_hub_inputs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('AUTHORING_INPUTS_WRITTEN actors='+str(len(rows)))
