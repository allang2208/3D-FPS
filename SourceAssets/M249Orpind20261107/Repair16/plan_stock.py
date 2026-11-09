import json,pickle,numpy as np
from pathlib import Path
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
r=Path(__file__).resolve().parent
d=pickle.load(open(r.parent/'Repair13/native.pkl','rb'))
v=np.array(d['vertices']);f=np.array(d['faces']);s=np.array(d['sections'])
ff=f[s==d['slots'].index('M249_Factory_Stock')];ids=np.unique(ff)
w,rm=np.unique(np.round(v[ids],4),axis=0,return_inverse=True)
look=np.zeros(len(v),int);look[ids]=rm;ff=look[ff]
edges=np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]])
_,lab=connected_components(coo_matrix((np.ones(len(edges)),edges.T),shape=(len(w),)*2),directed=False)
tube=next(w[lab==k] for k in set(lab) if len(w[lab==k])>20 and w[lab==k,1].min()<-5 and w[lab==k,2].min()>-3.6)
rim=tube[tube[:,1]<-3];center=rim.mean(0)
rim=rim[np.argsort(np.arctan2(rim[:,2]-center[2],rim[:,0]-center[0]))]
old=np.array(json.loads((r.parent/'Repair13/parts_recipe.json').read_text())['interfaces_component_cm']['stock'])
extension=2.2
plan=dict(original_lower_anchor_cm=old.tolist(),factory_upper_port_cm=center.tolist(),
          upper_port_ring_cm=rim.tolist(),new_stock_anchor_cm=(center+[0,extension,0]).tolist(),
          extension_cm=extension,body_translation_cm=(center+[0,extension,0]-old).tolist(),
          source='SK_M249_V7 M249_Factory_Stock upper tube front ring',runtime_tested=False)
(r/'stock_plan.json').write_text(json.dumps(plan,indent=2))
print('STOCK_INTERFACE_PLAN',plan['factory_upper_port_cm'],plan['body_translation_cm'])
