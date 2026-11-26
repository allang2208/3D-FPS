"""Focused geometry review of the reported village wall support defects."""
import json
import numpy as np
from wall_support_geometry import ROOT,load_mesh,rotate_vertices,bottom_profile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

source=ROOT/'SourceAssets/TemperateHillsVillage'
batch=source/'WallSupport20261114'
old=json.loads((batch/'Before/SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
new=json.loads((source/'layout.json').read_text(encoding='utf-8'))
prior=[i for w in old['yard_walls'] for i in w['native_instances']]
current=[i for w in new['yard_walls'] for i in w['native_instances']]
meshes={}
metrics=[]
def measure(instance):
    name=instance['mesh'].split('.')[-1]
    if name not in meshes:meshes[name]=load_mesh(name)
    v,f=meshes[name]
    # Support along the actual wall axis; yaw only turns that axis in the flat XY pad.
    q=rotate_vertices(v*np.array(instance['scale']),[instance['rot'][0],0,instance['rot'][2]])
    q[:,2]+=instance['pos'][2]
    xs,b=bottom_profile(q,f,step=1.6)
    b=b[np.isfinite(b)]
    unsupported=run=0
    for gap in b>0:
        run=run+1 if gap else 0;unsupported=max(unsupported,run)
    return dict(min_z_cm=round(float(q[:,2].min()),3),height_cm=round(float(q[:,2].max()),3),
        contact_fraction=round(float(np.mean(b<=0)),4),longest_unsupported_cm=round(unsupported*1.6,2)),q,f
for index,(a,b) in enumerate(zip(prior,current)):
    assert a['mesh']==b['mesh'] and a['pos'][:2]==b['pos'][:2] and a['scale']==b['scale']
    before,_,_=measure(a);after,_,_=measure(b)
    metrics.append(dict(index=index,mesh=b['mesh'].split('.')[-1],before=before,after=after))
worst=sorted(metrics,key=lambda m:m['before']['contact_fraction'])[:10]
fig,axes=plt.subplots(5,4,figsize=(17,16),layout='constrained')
for i,row in enumerate(worst):
    for j,group in enumerate((prior,current)):
        stat,q,f=measure(group[row['index']]);ax=axes[i//2,(i%2)*2+j]
        ax.add_collection(PolyCollection(q[f][:,:,[0,2]],facecolor='#626751',edgecolor='none'))
        ax.axhline(0,color='#9d5840');ax.axhspan(-85,0,color='#9d8768',alpha=.25)
        ax.set_xlim(q[:,0].min()-10,q[:,0].max()+10);ax.set_ylim(-85,180);ax.set_aspect('equal')
        ax.set_title(('%03d '%row['index'])+('BEFORE' if j==0 else 'AFTER')+' contact %.0f%%'%(100*stat['contact_fraction']))
fig.savefig(batch/'support-before-after.png',dpi=125)
report=dict(walls=len(metrics),xy_and_scale_preserved=True,
    before_fully_floating=sum(m['before']['min_z_cm']>1 for m in metrics),
    before_contact_below_90_percent=sum(m['before']['contact_fraction']<.9 for m in metrics),
    after_fully_floating=sum(m['after']['min_z_cm']>0 for m in metrics),
    after_min_contact_fraction=min(m['after']['contact_fraction'] for m in metrics),
    after_longest_unsupported_cm=max(m['after']['longest_unsupported_cm'] for m in metrics),
    after_height_range_cm=[min(m['after']['height_cm'] for m in metrics),max(m['after']['height_cm'] for m in metrics)],
    measurement='LOD0 triangle lower envelope sampled every 1.6 cm; geometry check, not physics simulation or gameplay acceptance',
    rows=metrics)
(batch/'support-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
assert report['walls']==154 and report['after_fully_floating']==0
assert report['after_min_contact_fraction']>=.9 and report['after_longest_unsupported_cm']<=16.1
