"""Check only the reported shoulder opening and the preserved bolt support."""
from pathlib import Path
import copy
exec(compile((Path(__file__).parent/'shoulder.py').read_text().split("if __name__=='__main__'")[0],'current shoulder models','exec'))
changes=json.load(gzip.open(O/'shoulder_tracks.json.gz','rt'))

report={}
for family,records in changes.items():
    cams=get_cameras(family);report[family]={}
    for role,tracks in records.items():
        old=entry(family,role);clip=copy.deepcopy(old);replace={tr['bone']:tr for tr in tracks}
        clip['tracks']=[replace.get(tr['bone'],tr) for tr in old['tracks']]
        start,end=window(role,clip)
        modes=[(blend_camera(cams['hip'],cams['scope'],alpha),75.-alpha*20.,alpha) for alpha in (0.,.25,.5,.75,1.)] if role in ('aim','fire') else [(cams['hip'],75.,0.)]
        results={'before_cm':1000.,'after_cm':1000.,'elbow_mm':0.,'palm_mm':0.,'upper_length_mm':0.}
        for t in np.linspace(start,end,round((end-start)*60)+1):
            prior,_=compose(old,float(t));row,_=compose(clip,float(t))
            before=skin_rim(prior);after=skin_rim(row)
            for camera,fov,alpha in modes:
                cm0,_=clearance(before,camera,fov);cm1,count=clearance(after,camera,fov)
                results['before_cm']=min(results['before_cm'],cm0)
                if cm1<results['after_cm']:results.update(after_cm=cm1,time=float(t),view_alpha=alpha,in_view=count)
            for n,key in [('lowerarm_l','elbow_mm'),('hand_l','palm_mm')]:
                results[key]=max(results[key],(row[n].translation-prior[n].translation).length*1000)
            def length(r):return (r['upperarm_l'].translation-r['lowerarm_l'].translation).length
            results['upper_length_mm']=max(results['upper_length_mm'],1000*abs(length(row)-length(prior)))
        report[family][role]=results
    print('BOLT_ROOT_MARGIN',family,[(role,round(v['before_cm'],3),round(v['after_cm'],3),round(v['palm_mm'],4)) for role,v in report[family].items()],flush=True)
(O/'camera_clearance.json').write_text(json.dumps(report,indent=2))
