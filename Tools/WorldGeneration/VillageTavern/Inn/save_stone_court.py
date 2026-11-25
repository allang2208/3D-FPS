"""Migrate the live R1 parts by site tag; retain unrelated actors and existing repair associations."""
from pathlib import Path
import json,sys,os
import unreal as u
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(ROOT/'Tools/WorldGeneration/AbandonedVillage'),str(ROOT/'Tools/WorldGeneration/VillageBlacksmith')]
from fit_inn import clear_inn_scatter
from stone_court import install,TAG
from layout_geometry import plot_geometry
from tavern_shell import room_frame,set_tavern_vision
def save():
    level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
    world=u.EditorLoadingAndSavingUtils.load_map(level)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    site,=[a for a in actors if 'VillageTavern.Site' in map(str,a.tags)]
    volume,=[a for a in actors if 'VillageTavern.Vision' in map(str,a.tags)]
    src=ROOT/'SourceAssets/TemperateHillsVillage'
    plan=json.loads((src/'layout.json').read_text(encoding='utf8'))
    house=next(h for h in plan['houses'] if h[0]=='02')
    shape=plot_geometry(house,json.loads((src/'house-pieces.json').read_text(encoding='utf8'))[house[2]],plan)
    new=room_frame(house,shape);old=site.get_actor_transform();moved=[]
    if TAG not in map(str,site.tags):
        if 'VillageTavern.ThreeStoreyInn' not in map(str,site.tags):raise RuntimeError('Expected three-storey tavern')
        for a in actors:
            if a==site:continue
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                m=c.static_mesh
                if not m or m.get_name() not in ('SM_TavernAleCask','SM_TavernTapCask','SM_TavernPitcher'):continue
                b=m.get_bounding_box()
                for i in range(c.get_instance_count()):
                    t=c.get_instance_transform(i,True)
                    p=u.MathLibrary.inverse_transform_location(old,u.MathLibrary.transform_location(t,(b.min+b.max)*.5))
                    if 165<p.x<385 and -655<p.y<-530:
                        a.modify();c.modify();t.translation=t.translation+new.translation-old.translation
                        if not c.update_instance_transform(i,t,True,True,True):raise RuntimeError('Cask move')
                        moved.append(m.get_name())
        if len(moved)!=3:raise RuntimeError('Expected the original cask station '+repr(moved))
        site.modify()
        site.set_actor_transform(new,False,True)
        install(site)
    cleared=clear_inn_scatter(actors,site)
    volume.modify();set_tavern_vision(volume,house,shape,plan)
    if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError(level)
    vec=lambda p:[round(v,2) for v in (p.x,p.y,p.z)]
    return dict(level=level,old=vec(old.translation),new=vec(new.translation),cask_station=moved,cleared=cleared)
if __name__=='__main__':
    Path(os.environ['TAVERN_INN_BATCH'],'level.json').write_text(json.dumps(save(),indent=2),encoding='utf8')
