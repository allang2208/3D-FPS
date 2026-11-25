"""Apply the inn refit to the current village without respawning neighbouring houses."""
from pathlib import Path
import math,json,sys,os
import unreal as u
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(ROOT/'Tools/WorldGeneration/AbandonedVillage')]
from hall_refit import TAG,install

def clear_verge(actors,spec):
    count=0
    def inside(p):
        x,y=p.x*.01,p.y*.01
        if not (-18<x<-7 and -.5<y<26.5):return False
        for a,b in zip(spec['stations'],spec['stations'][1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
            if math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)<a[2]+t*(b[2]-a[2])-.22:return True
        return False
    for a in actors:
        if not a.get_actor_label().startswith('Village_'):continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            m=c.static_mesh
            if not m or not m.get_name().lower().startswith(('sm_grass','flower_','sm_planttype','sm_stone_','sm_softwildgrass','sm_foresttwig')):continue
            box=m.get_bounding_box();mid=(box.min+box.max)*.5
            for i in reversed(range(c.get_instance_count())):
                p=u.MathLibrary.transform_location(c.get_instance_transform(i,True),mid)
                if p.z<110 and inside(p):
                    a.modify();c.modify()
                    if not c.remove_instance(i):raise RuntimeError('Verge '+m.get_name())
                    count+=1
    return count

def retire(actors,targets):
    hits={}
    for a in actors:
        if not a.get_actor_label().startswith('Village_'):continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            m=c.static_mesh
            if not m or 'StoneWall_00A_Piece' not in m.get_name():continue
            possible=[(k,q['pos']) for k,q in enumerate(targets) if q['mesh']==m.get_path_name()]
            if not possible:continue
            for i in range(c.get_instance_count()):
                p=c.get_instance_transform(i,True).translation
                for k,pos in possible:
                    if math.dist((p.x,p.y,p.z),pos)<2:
                        if k in hits:raise RuntimeError('Ambiguous wall '+str(k))
                        hits[k]=(a,c,i)
    if len(hits)!=len(targets):raise RuntimeError('Missing wall instances '+str(set(range(len(targets)))-set(hits)))
    for a,c,i in sorted(hits.values(),key=lambda v:-v[2]):
        a.modify();c.modify()
        if not c.remove_instance(i):raise RuntimeError('Stone wall removal')
    return len(hits)

def save():
    level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
    world=u.EditorLoadingAndSavingUtils.load_map(level);actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    site,=[a for a in actors if 'VillageTavern.Site' in map(str,a.tags)]
    spec=json.loads((ROOT/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf8'))['tavern']['inn']['hall_road']
    n=retire(actors,spec['retired_walls']) if TAG not in map(str,site.tags) else 0
    result=install(site);result.update(removed_wall_instances=n,cleared_verge_instances=clear_verge(actors,spec),level=level)
    if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError(level)
    return result
if __name__=='__main__':
    Path(os.environ['TAVERN_INN_BATCH'],'level.json').write_text(json.dumps(save(),indent=2),encoding='utf8')
