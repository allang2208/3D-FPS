from pathlib import Path
import sys
O=Path(__file__).parent
exec((O/'fit_elbow_helpers.py').read_text().split("frames=D['clips']")[0])
def thumb_data(side):
    bones=np.array([under(j,ix['thumb_01_'+side]) for j in range(len(names))]);fs=faces[weights[faces][:,:,bones].sum(2).mean(1)>.25]
    ids=np.unique(fs);reverse=np.full(len(verts),-1);reverse[ids]=np.arange(len(ids));fs=reverse[fs];wp=weights[ids];active=np.where(wp.max(0)>0)[0];wp=wp[:,active];wf=wp[fs].mean(1)
    vv=verts[ids];nn=np.cross(vv[fs[:,1]]-vv[fs[:,0]],vv[fs[:,2]]-vv[fs[:,0]]);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-12)
    return ids,fs,active,wp,wf,nn
tag=sys.argv[1] if len(sys.argv)>1 else 'before'
datasets={s:thumb_data(s) for s in ['l','r']};graph=json.loads((O/f'graph_{tag}.json').read_text());report=[]
for row in graph['cases']:
    if row['case']=='post_off':continue
    result={'food':row['food'],'case':row['case'],'sides':{}}
    for side in ['l','r'] if row['food']=='roasted_large_lamb' else ['l']:
        counts=[]
        for sample in row['samples']:
            if sample['weight']<.01:continue
            metrics=skin_metrics(mat(np.array(sample['world'])),side);counts.append((sample['time'],metrics[0]))
        worst=max(counts,key=lambda a:a[1]);result['sides'][side]={'worst':worst,'samples':counts}
    report.append(result);print(row['food'],row['case'],{s:v['worst'] for s,v in result['sides'].items()},flush=True)
(O/f'thumb_skin_{tag}.json').write_text(json.dumps(report,indent=2))
