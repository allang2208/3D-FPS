"""Read only: saved bow instances and their actual mesh assets. No game world."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir())
OUT=ROOT/'Saved/BowModelRepair20260926'
OUT.mkdir(parents=True,exist_ok=True)
catalog=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8'))['bow_dark']
report={'catalog':catalog,'slots':[],'assets':{},'save_files_written':False}
paths={catalog['bow_part_riser_mesh']}
for suffix in ('A','B'):
    slot='ColdSteelPlayer_'+suffix
    file=ROOT/'Saved/SaveGames'/f'{slot}.sav'
    digest=hashlib.sha1(file.read_bytes()).hexdigest().upper()
    stored=file.with_suffix('.sha1').read_text(encoding='utf-8-sig').strip()
    # Profile is a protected native property. Read its serialized item JSON
    # without creating a profile subsystem or touching the player's save.
    row={'slot':slot,'checksum_matches':digest==stored,'bows':[]}
    buf=file.read_bytes()
    for encoding in ('utf-16-le','utf-8'):
        needle='{'.encode(encoding);start=0
        while True:
            start=buf.find(needle,start)
            if start<0:break
            try:
                data,_=json.JSONDecoder().raw_decode(buf[start:].decode(encoding,errors='ignore'))
                if isinstance(data,dict) and data.get('id')=='bow_dark':
                    row['bows'].append({'data':data})
                    paths.add(data.get('bow_part_riser_mesh',data.get('bow_mesh','')))
            except (ValueError,UnicodeError):pass
            start+=len(needle)
    report['slots'].append(row)
for path in sorted(paths):
    mesh=u.load_asset(path) if path else None
    entry={'loaded':mesh is not None}
    if mesh:
        b=mesh.get_bounds()
        entry.update({'class':mesh.get_class().get_name(),'resolved_path':mesh.get_path_name(),
            'triangles':mesh.get_num_triangles(0),
            'size_cm':[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2],
            'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials]})
    report['assets'][path]=entry
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['running_world']=world.get_path_name() if world else None
report['live_components']=[]
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        if 'FPS' not in actor.get_class().get_name():continue
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            name=comp.get_name()
            if 'riser' not in name.lower() and 'bow' not in name.lower():continue
            mesh=comp.static_mesh
            report['live_components'].append({'actor':actor.get_path_name(),'name':name,
                'mesh':mesh.get_path_name() if mesh else None,
                'visible':comp.is_visible(),
                'materials':[m.get_path_name() if m else None for m in comp.get_materials()]})
(OUT/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('DARKBOW_MODEL_DIAGNOSIS',json.dumps({'slots':[{**s,'bows':[{
    'revision':b['data'].get('bow_presentation_revision'),'mesh':b['data'].get('bow_part_riser_mesh'),
    'material':b['data'].get('bow_part_riser_material'),'legacy_mesh':b['data'].get('bow_mesh')} for b in s['bows']]} for s in report['slots']],
    'assets':report['assets'],'running_world':report['running_world'],'live_components':report['live_components']},ensure_ascii=False))
