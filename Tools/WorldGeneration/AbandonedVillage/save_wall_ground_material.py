"""Bind the reviewed root blend to the 154 saved boundary walls only."""
import hashlib,json,sys
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source=root/'SourceAssets/TemperateHillsVillage'
out=source/'WallReview20261114'
relative=Path('Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before_sha=digest(out/'MaterialBefore'/relative)
if digest(root/relative)!=before_sha:raise RuntimeError('Village changed since this material backup; preserve concurrent work')
sys.path.insert(0,str(root/'Tools/WorldGeneration/AbandonedVillage'))
from wall_ground_material import dress_wall
plan=json.loads((source/'layout.json').read_text(encoding='utf-8'))
wanted=[i for w in plan['yard_walls'] for i in w['native_instances']]
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError('Village load failed')
rows=[]
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        if not comp.static_mesh or 'StoneWall' not in comp.static_mesh.get_name():continue
        for index in range(comp.get_instance_count()):
            rows.append((actor,comp,index,comp.get_instance_transform(index,True)))
selected=[]
for inst in wanted:
    matches=[r for r in rows if r[1].static_mesh.get_path_name()==inst['mesh']
             and (r[3].translation-u.Vector(*inst['pos'])).length()<.05
             and (r[3].scale3d-u.Vector(*inst['scale'])).length()<.001]
    if len(matches)!=1:raise RuntimeError('Boundary wall match is not unique')
    selected.append(matches[0])
components={row[1] for row in selected}
if len(selected)!=154 or sum(c.get_instance_count() for c in components)!=154:
    raise RuntimeError('Material component would include unowned masonry')
cache={};changes=[]
for comp in components:
    before=[comp.get_material(i).get_path_name() for i in range(comp.get_num_materials())]
    comp.get_owner().modify();comp.modify();dress_wall(comp,cache)
    after=[comp.get_material(i).get_path_name() for i in range(comp.get_num_materials())]
    changes.append(dict(actor=comp.get_owner().get_actor_label(),instances=comp.get_instance_count(),before=before,after=after))
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Village material bindings not saved')
report=dict(saved=True,boundary_walls=154,house_masonry_preserved=len(rows)-154,
    before_map_sha256=before_sha,after_map_sha256=digest(root/relative),
    created_assets=sorted({v.get_path_name() for v in cache.values()}),components=sorted(changes,key=lambda x:x['actor']),
    max_colour_roughness_blend=.42,max_normal_blend=.105,transition_top_cm=[4.4,7.6],transforms_edited=False)
(out/'wall-material-saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WALL_ROOT_MATERIAL_SAVED',len(components),len(report['created_assets']))
