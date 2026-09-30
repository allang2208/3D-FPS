"""Conservative refinement of existing fitted vertices and surface fields.
No mesh replacement, overlays, new shells, or added geometry.
"""
from pathlib import Path
import json,numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.ndimage import gaussian_filter
from PIL import Image
O=Path(__file__).parent;(O/'Textures').mkdir(exist_ok=True)
records=json.loads((O/'source.json').read_text());report=[]
targets={'Receiver':.00055,'TopCover':.00045,'Handguard':.00032,'TopRail':.00020,'FrontSight_Fitted':.00022,'RearSight':.00022,'FrontSightBase_Fitted':.00022,'Stock':.00028,'CarryHandle':.00018}
for item in records:
 name=item['object'];d=np.load(O/'Work'/(name+'.npz'));base=d['vertices'];v=base.copy();f=d['faces'];loops=d['loops'];old=d['normals'];nf=len(f);nv=len(v)
 def fn(p):
  q=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]);area=np.linalg.norm(q,axis=1);return q/np.maximum(area[:,None],1e-15),area
 if name not in targets:continue
 cap=targets[name];n0,ar=fn(v);c=v[f].mean(1)
 edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);ef=np.tile(np.arange(nf),3)
 ee,inv,counts=np.unique(edges,axis=0,return_inverse=True,return_counts=True);order=np.argsort(inv,kind='stable');starts=np.r_[0,np.cumsum(counts)[:-1]]
 man=counts==2;fa=ef[order[starts[man]]];fb=ef[order[starts[man]+1]];pair=ee[man]
 dot=np.sum(n0[fa]*n0[fb],axis=1);mat=d['material_ids'];feature=(dot<np.cos(np.radians(32)))|(mat[fa]!=mat[fb])
 pin=np.zeros(nv,bool);pin[np.unique(ee[~man])]=True;pin[np.unique(pair[feature])]=True
 # Cut faces, mating planes and endpoints stay exactly where the accepted rig expects.
 surface=np.array(['Surface' in item['materials'][i] for i in mat]);pin[np.unique(f[~surface])]=True
 adj=coo_matrix((np.ones(len(ee)*2),(np.r_[ee[:,0],ee[:,1]],np.r_[ee[:,1],ee[:,0]])),shape=(nv,nv)).tocsr();deg=np.maximum(np.asarray(adj.sum(1)).ravel(),1)
 influence=(~pin).astype(float)
 for _ in range(2):influence=np.minimum(influence,adj@influence/deg)
 influence[pin]=0
 allowed=(~feature)&surface[fa]&surface[fb];a=fa[allowed];b=fb[allowed]
 spatial=np.exp(-np.sum((c[a]-c[b])**2,axis=1)/(2*.003**2));filtered=n0.copy()
 for _ in range(10):
  w=spatial*np.exp(-(1-np.clip(np.sum(filtered[a]*filtered[b],axis=1),-1,1))/.0075)
  acc=filtered.copy();den=np.ones(nf);np.add.at(acc,a,filtered[b]*w[:,None]);np.add.at(acc,b,filtered[a]*w[:,None]);np.add.at(den,a,w);np.add.at(den,b,w)
  filtered=acc/den[:,None];filtered/=np.maximum(np.linalg.norm(filtered,axis=1,keepdims=True),1e-15)
 weights=np.clip(np.sqrt(ar/max(np.median(ar),1e-15)),.25,2)
 den=np.bincount(f.ravel(),weights=np.repeat(weights,3),minlength=nv)
 for _ in range(35):
  centers=v[f].mean(1);off=np.sum((centers[:,None]-v[f])*filtered[:,None],axis=2);delta=np.zeros_like(v)
  np.add.at(delta,f.ravel(),(off[:,:,None]*filtered[:,None]*weights[:,None,None]).reshape(-1,3))
  change=v+delta/np.maximum(den[:,None],1e-15)*influence[:,None]*.65-base
  change*=np.minimum(1,cap/np.maximum(np.linalg.norm(change,axis=1),1e-15))[:,None];v=base+change
 # Flatten only coherent, nearly planar patches in the existing large panels.
 # Recess walls and embossed ridges cannot join these connected surface islands.
 planar=[]
 if name in ['Receiver','TopCover','Stock','TopRail']:
  axes=[0] if name in ['Receiver','Stock'] else [0,2]
  for axis in axes:
   for sign in [-1,1]:
    use=surface&(filtered[:,axis]*sign>.992)
    conn=allowed&use[fa]&use[fb];x=fa[conn];y=fb[conn]
    graph=coo_matrix((np.ones(len(x)*2),(np.r_[x,y],np.r_[y,x])),shape=(nf,nf)).tocsr();_,label=connected_components(graph)
    for li in np.unique(label[use]):
     ids=np.flatnonzero(use&(label==li))
     if len(ids)<70 or ar[ids].sum()<.00012:continue
     vi=np.unique(f[ids]);p=base[vi];center=np.median(p,axis=0);_,_,vt=np.linalg.svd(p-center,full_matrices=False);normal=vt[-1]
     if abs(normal[axis])<.99:continue
     delta=(v[vi]-center)@normal
     if np.quantile(np.abs(delta),.9)>.0010:continue
     support=np.zeros(nv);np.add.at(support,f[ids].ravel(),1)
     allcount=np.bincount(f.ravel(),minlength=nv);strength=(support>=allcount)*influence
     for _ in range(2):strength=np.minimum(strength,adj@strength/deg)
     v[vi]-=normal[None]*np.clip(delta,-cap,cap)[:,None]*strength[vi,None]*.75
     planar.append({'axis':axis,'faces':len(ids)})
 # Final displacement remains bounded, including the planar pass.
 change=v-base;change*=np.minimum(1,cap/np.maximum(np.linalg.norm(change,axis=1),1e-15))[:,None];v=base+change
 # Transport original corner normals by the face deformation. Only compatible
 # smooth fans on modified surfaces receive a small area-weighted correction.
 n1,ar1=fn(v);cross=np.cross(n0,n1);cos=np.sum(n0*n1,axis=1);src=old[loops]
 rotated=src+np.cross(cross[:,None],src)+np.cross(cross[:,None],np.cross(cross[:,None],src))/np.maximum(1+cos[:,None,None],1e-8)
 vn=np.zeros_like(v);np.add.at(vn,f.ravel(),np.repeat(n1*np.sqrt(ar1[:,None]),3,axis=0));vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
 compatible=np.sum(vn[f]*rotated,axis=2)>.985
 amount=.40*influence[f]*compatible;result=rotated*(1-amount[:,:,None])+vn[f]*amount[:,:,None];result/=np.maximum(np.linalg.norm(result,axis=2,keepdims=True),1e-12)
 normals=old.copy();normals[loops.ravel()]=result.reshape(-1,3)
 np.savez_compressed(O/'Work'/(name+'_edited.npz'),vertices=v,normals=normals)
 report.append({'part':name,'changed_vertices':int((np.linalg.norm(change,axis=1)>1e-9).sum()),'max_displacement_mm':float(np.linalg.norm(change,axis=1).max()*1000),'planar_patches':planar,'topology_unchanged':True})
 print('REFINED',name,report[-1]['changed_vertices'],flush=True)

# Atlas keeps its layout and structural normal map. Rework coating response;
# do not erase the normal texture to disguise geometric irregularities.
src=O.parent/'Refine29/Textures'
base=np.array(Image.open(src/'T_201_R29_Surface_BaseColor.png').convert('RGB'),dtype=np.float32)/255
orm=np.array(Image.open(src/'T_201_R29_Surface_ORM.png').convert('RGB'),dtype=np.float32)/255
metal=np.clip(orm[:,:,2]/.78,0,1);valid=orm[:,:,0]>.1
lum=np.mean(base,axis=2);detail=lum-gaussian_filter(lum,2.0)
# A small local contrast increase makes existing engraved/stamped details read.
base=np.clip(base+np.clip(detail,-.025,.025)[:,:,None]*.22,0,1)
rough_coat=.60+np.clip((orm[:,:,1]-.35)/.065,0,1)*.055
rough_poly=.68+np.clip((orm[:,:,1]-.61)/.11,0,1)*.055
orm[:,:,1]=np.where(metal>.5,rough_coat,rough_poly)+np.clip(-detail*1.2,-.015,.018)
orm[:,:,2]=np.where(metal>.5,orm[:,:,2]*.42,orm[:,:,2]);orm=np.clip(orm,0,1)
for name,a in [('BaseColor',base),('ORM',orm)]:Image.fromarray(np.rint(a*255).astype('uint8'),'RGB').save(O/'Textures'/('T_LMG201_S32_'+name+'.png'))
report={'method':'original fitted vertices, bounded bilateral fairing and coherent planar-patch fitting','parts':report,'material':{'coated_roughness': [.60,.655],'polymer_roughness':[.68,.735],'coated_metallic_factor':.42,'structural_normal':'R29 UV0 map retained unchanged','extra_noise':False},'components_added':0,'rendered':False,'tested':False}
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('SURFACE32_SOURCE_AUTHORED',flush=True)
