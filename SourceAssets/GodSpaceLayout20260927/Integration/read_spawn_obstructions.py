import unreal as u,json
from pathlib import Path
e=u.get_editor_subsystem(u.UnrealEditorSubsystem);w=e.get_game_world() or e.get_editor_world()
def v(p):return [p.x,p.y,p.z]
data=[]
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    ctr,ext=a.get_actor_bounds(False)
    if abs(ctr.x+1100)>ext.x+100 or abs(ctr.y+5100)>ext.y+100:continue
    if ctr.z+ext.z<100 or ctr.z-ext.z>300:continue
    row={'name':a.get_name(),'label':a.get_actor_label(),'class':a.get_class().get_name(),'center':v(ctr),'extent':v(ext),'tags':[str(t) for t in a.tags],'meshes':[]}
    for c in a.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        if not m:continue
        d={'mesh':m.get_path_name(),'instances':[],'component':c.get_name()}
        if isinstance(c,u.InstancedStaticMeshComponent):
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);b=m.get_bounding_box();cc=t.transform_location((b.min+b.max)*.5);ex=(b.max-b.min)*.5*t.scale3d
                if abs(cc.x+1100)<abs(ex.x)+150 and abs(cc.y+5100)<abs(ex.y)+150:d['instances'].append({'index':i,'transform':str(t),'center':v(cc),'extent':v(ex)})
        row['meshes'].append(d)
    data.append(row)
Path(__file__).with_name('SpawnRepair').joinpath('obstructions.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data))
