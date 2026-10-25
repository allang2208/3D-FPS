"""Native female jacket derivatives through the existing measured body correspondence."""
import copy,gc,sys
import numpy as np
from workwear_common import *
sys.path.insert(0,str(P/'Tools/KaitlinPlayer'))
from body_surface_fit import BodySurfaceFit
W=P/'SourceAssets/KaitlinPlayer20261023'
captured=read(W/'FitInputs/captured.json');body=read(W/'FitInputs/player_body.json');modular=read(W/'FitInputs/modular_outfits.json')
source=read(W/'FitInputs'/captured[modular['profiles'][body['body_mesh']]['native_bare_skin']]['file']);target=read(W/'NativeGeometry/MHC_Kaitlin_Body.json')
fit=BodySurfaceFit(source,target,read(W/'body_correspondence.json')['target_to_source_vertices'])
manifest=read(R/'authored.json');inputs=read(R/'inputs.json');records=[]
for row in manifest['records']:
    if row['rig']!='Jason':continue
    d=read(row['file']);names=sorted(d['bones'],key=lambda n:d['bones'][n]['index']);indices={n:i for i,n in enumerate(names)}
    converted=dict(d,source=d['binding_source'],materials=[],bones=[dict(d['bones'][n],name=n,index=indices[n]) for n in names],weights=[[[indices[n],w] for n,w in ws.items()] for ws in d['weights']])
    result=fit.garment(converted);out=copy.deepcopy(d);out['positions']=result['positions'];out['weights']=[{target['bones'][i]['name']:w for i,w in ws} for ws in result['weights']];out['bones']={b['name']:{k:v for k,v in b.items() if k!='name'} for b in target['bones']}
    out['binding_source']=inputs['kaitlin_recipe']['owner_body_meshes']['Kaitlin'] if row.get('owner') else inputs['kaitlin_recipe']['rig_meshes']['Kaitlin']
    # Rebuild smooth corner normals from the deformed native surface, preserving UV splits.
    pp=np.array(out['positions']);ff=np.array(out['triangles']);cross=-np.cross(pp[ff[:,1]]-pp[ff[:,0]],pp[ff[:,2]]-pp[ff[:,0]]);vn=np.zeros_like(pp)
    for j in range(3):np.add.at(vn,ff[:,j],cross)
    _,inverse=np.unique(np.round(pp,5),axis=0,return_inverse=True);acc=np.zeros((inverse.max()+1,3));np.add.at(acc,inverse,vn);vn=acc[inverse];vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12);out['normals']=vn[ff].tolist()
    out['profile']=row['profile'].replace('Jason','Kaitlin');out['contract']+='; Kaitlin native bind frames and body surface correspondence; own native material hiding'
    path=R/'Authored'/KEY/(out['profile']+'.json');compact(path,out);records.append(dict(row,profile=out['profile'],rig='Kaitlin',file=str(path)))
    write(R/'female-authored.json',dict(completed=False,records=records));print('WORK_JACKET_KAITLIN_AUTHORED',out['profile'],flush=True);del d,out,converted,result;gc.collect()
write(R/'female-authored.json',dict(completed=True,records=records,runtime_tested=False))
