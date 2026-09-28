import unreal as u, json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/GodSpaceLayout20260927')
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=e.get_game_world() or e.get_editor_world()
a=u.GameplayStatics.get_all_actors_of_class(w,u.Actor)
def v(x): return [round(x.x,3),round(x.y,3),round(x.z,3)]
def t(x): return dict(location=v(x.translation),rotation=[x.rotation.rotator().pitch,x.rotation.rotator().yaw,x.rotation.rotator().roll],scale=v(x.scale3d))
rows=[]
for x in a:
    cs=[]
    for c in x.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        if not m: continue
        b=m.get_bounding_box()
        rec=dict(name=c.get_name(),mesh=m.get_path_name(),bounds=[v(b.min),v(b.max)],materials=[z.get_path_name() if z else None for z in c.get_materials()],visible=c.is_visible(),transform=t(c.get_world_transform()))
        if isinstance(c,u.InstancedStaticMeshComponent): rec['instances']=[t(c.get_instance_transform(i,world_space=True)) for i in range(c.get_instance_count())]
        cs.append(rec)
    rows.append(dict(label=x.get_actor_label(),path=x.get_path_name(),cls=x.get_class().get_name(),transform=t(x.get_actor_transform()),tags=[str(z) for z in x.tags],folder=str(x.get_folder_path()),meshes=cs))
r=dict(world=w.get_path_name(),pie=bool(e.get_game_world()),dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],dirty_content=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],actors=rows)
(root/'current_scene.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:r[k] for k in ['world','pie','dirty_maps','dirty_content']},ensure_ascii=False))
print('actors',len(rows))
print('\n'.join(x['label']+' | '+x['cls']+' | '+str(x['transform']['location']) for x in rows if not x['label'].startswith(('PlazaInstances','MainPlaza_','Plaza_'))))
