"""Publish only the surveyed tavern, its exposure volume and three apron barrel pieces."""
from pathlib import Path
import json
import os
import sys
import unreal as u

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(ROOT/'Tools/WorldGeneration/AbandonedVillage'),str(ROOT/'Tools/WorldGeneration/VillageBlacksmith')]
from fit_inn import TAG,upgrade,clear_inn_scatter
from layout_geometry import plot_geometry
from tavern_shell import room_frame,set_tavern_vision

out=Path(os.environ['TAVERN_INN_BATCH'])
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
content=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir()))
file=content/(level[6:]+'.umap')
stamp=file.stat().st_mtime_ns
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Pending level edits')
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError(level)
all_actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
site,=[a for a in all_actors if 'VillageTavern.Site' in map(str,a.tags)]
vis,=[a for a in all_actors if a.get_actor_label().startswith('Village_InteriorVision_02_')]
src=ROOT/'SourceAssets/TemperateHillsVillage'
plan=json.loads((src/'layout.json').read_text(encoding='utf8'))
house=next(h for h in plan['houses'] if h[0]=='02')
pieces=json.loads((src/'house-pieces.json').read_text(encoding='utf8'))[house[2]]
shape=plot_geometry(house,pieces,plan)
frame=room_frame(house,shape)
report={}
if TAG not in map(str,site.tags):
    old=site.get_actor_transform()
    delta=frame.translation-old.translation
    if abs(delta.length()-65)>1:raise RuntimeError('House 02 moved since survey')
    moved=[]
    for a in all_actors:
        if a==site:continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            m=c.static_mesh
            if not m or m.get_name() not in ('SM_TavernAleCask','SM_TavernTapCask','SM_TavernPitcher'):continue
            box=m.get_bounding_box()
            mid=(box.min+box.max)*.5
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True)
                p=u.MathLibrary.inverse_transform_location(old,u.MathLibrary.transform_location(t,mid))
                if 170<p.x<380 and -640<p.y<-540:
                    a.modify();c.modify();t.translation=t.translation+delta
                    if not c.update_instance_transform(i,t,True,True,True):raise RuntimeError('Cask station move failed')
                    moved.append(m.get_name())
    if len(moved)!=3:raise RuntimeError('Unexpected street-side cask count '+str(moved))
    site.modify();site.set_actor_transform(frame,False,True)
    if (site.get_actor_location()-frame.translation).length()>.1:raise RuntimeError('Tavern setback failed')
    report=upgrade(site,plan)
    report['cleared_scatter']=clear_inn_scatter(all_actors,site)
    report.update(moved_apron=moved,anchor_cm=[frame.translation.x,frame.translation.y,frame.translation.z])
vis.modify()
set_tavern_vision(vis,house,shape,plan)
if file.stat().st_mtime_ns!=stamp:raise RuntimeError('Concurrent village edit')
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Failed saving '+level)
(out/'level.json').write_text(json.dumps(dict(level=level,**report),indent=2),encoding='utf8')

