"""Remove only the captured parallel street-wall instances; preserve every house."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/VillageDefenses20261117'
targets=json.loads((OUT/'duplicate-wall-removal.json').read_text(encoding='utf-8'))
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
world=u.get_editor_subsystem(u.LevelEditorSubsystem)
if not world.load_level(level):raise RuntimeError('Cannot load owned village level')
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
removed=[]
for actor in actors:
    for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=c.get_editor_property('static_mesh')
        if not mesh:continue
        path=mesh.get_path_name()
        wanted=[t for t in targets if t['instance']['mesh']==path]
        if not wanted:continue
        matches=[]
        for i in range(c.get_instance_count()):
            tr=c.get_instance_transform(i,True);p=tr.translation
            for t in wanted:
                q=t['instance']['pos']
                if abs(p.x-q[0])<1.0 and abs(p.y-q[1])<1.0:
                    matches.append(i);removed.append({'actor':actor.get_actor_label(),'mesh':path,'xy':[p.x,p.y]});break
        if matches:
            c.modify();actor.modify()
            for i in sorted(matches,reverse=True):
                if not c.remove_instance(i):raise RuntimeError('Cannot remove '+str(i))
if len(removed) not in (0,len(targets)):
    raise RuntimeError('Partial match: refusing to save '+str(len(removed))+'/'+str(len(targets)))
if not world.save_current_level():raise RuntimeError('Village level save failed')
(OUT/('duplicate-wall-saved.json' if removed or not (OUT/'duplicate-wall-saved.json').exists() else 'duplicate-wall-reimport-check.json')).write_text(json.dumps({'level':level,'removed':removed,'already_absent':not removed,'expected':len(targets)},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('VILLAGE_DUPLICATE_WALL_REMOVED '+str(len(removed)))
