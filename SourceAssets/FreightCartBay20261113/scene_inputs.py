from pathlib import Path
import unreal as u,json
def apply(world,row):
    d={}
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        label=a.get_actor_label()
        if not (('Floor' in label or 'Station_' in label or 'Workshop' in label or label.startswith('Cart_')) and a.get_component_by_class(u.StaticMeshComponent)): continue
        c=a.get_component_by_class(u.StaticMeshComponent)
        if not c.static_mesh:continue
        p,e=a.get_actor_bounds(False)
        if abs(p.x-8500)>e.x+80 or abs(p.y+340)>e.y+140:continue
        d[label]=dict(center=p.to_tuple(),ext=e.to_tuple(),mesh=c.static_mesh.get_name(),mats=[str(m.get_path_name()) if m else '' for m in c.get_materials()])
    Path(__file__).with_name('inputs.json').write_text(json.dumps(d,indent=2),'utf8')
