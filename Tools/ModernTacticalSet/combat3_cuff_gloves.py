"""Fit only floating wrist webbing onto each current glove's own surface."""
import sys,copy,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import P,R,C,read,write,unit,cuff_weights
from shirt_geometry import smooth_transport
DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3';rows=[]
def native_wrist_weights(d,g,ids):
    byname={b['name']:b['index'] for b in d['bones']}
    for i in ids:
        support={name:value for name,value in g['weights'][int(i)].items() if name.startswith(('lowerarm','hand_'))};total=sum(support.values())
        if total<=1e-6:raise RuntimeError('Wrist strap has no native forearm/hand support')
        d['weights'][int(i)]=[[byname[name],value/total] for name,value in support.items()]
sources=[r for r in read(C/'captured.json')['rows'] if r['role']=='glove']
# The M4 comparison input existed before the extended glove plan.
if not any(r['rig']=='M4' for r in sources):sources.append(next(r for r in read(C/'captured.json')['rows'] if r['key']=='Glove_M4'))
sources.sort(key=lambda r:(0 if r['rig'] in ['Jason','Kaitlin'] else 1,r['rig']))
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if args:sources=[row for row in sources if row['rig'] in args[0].split(',')]
manifest=C/('gloves-batch-'+args[1]+'.json' if args else 'gloves-authored.json')
for row in sources:
    file=C/'Authored'/('gloves_'+row['rig']+'.json');entry=dict(source=row['path'],rig=row['rig'],kind='gloves',file=str(file),asset=DEST+'/Wear/'+row['rig']+'/SK_TS01_'+row['rig']+'_CuffFitGloves',original_sha256=row['sha256'])
    if file.exists() and read(file).get('wrist_strap_fit',{}).get('native_sha256')==row['sha256']:
        cached=read(file)
        if cached['wrist_strap_fit'].get('binding')!='native_forearm_hand_renormalized_v1':
            original=read(row['file']);ids=[i for i,(a,b) in enumerate(zip(original['positions'],cached['positions'])) if a!=b];native_wrist_weights(cached,original,ids);cached['wrist_strap_fit']['binding']='native_forearm_hand_renormalized_v1';write(file,cached)
        rows.append(entry);write(manifest,dict(completed=False,rows=rows));continue
    g=read(row['file']);d=copy.deepcopy(g);d['bones']=[dict(name=name,**b) for name,b in g['bones'].items()];byname={b['name']:b['index'] for b in d['bones']};d['weights']=[[[byname[name],w] for name,w in ws.items()] for ws in g['weights']];d['rig']=row['rig'];p=np.array(g['positions']);f=np.array(g['triangles']);m=np.array(g['triangle_materials']);webbing={i for i,name in enumerate(g['material_slots']) if 'Webbing' in name};base={i for i,name in enumerate(g['material_slots']) if any(k in name for k in ['RangerNylon','CharcoalLeather','CharcoalStretch','RangerRipstop'])};faces=f[np.isin(m,list(webbing))];ids=np.unique(faces);_,weld=np.unique(np.round(p,5),axis=0,return_inverse=True);parent={int(weld[i]):int(weld[i]) for i in ids}
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for face in faces:
        a,b,c=[int(weld[i]) for i in face];parent[root(b)]=root(a);parent[root(c)]=root(a)
    components={}
    for i in ids:components.setdefault(root(int(weld[i])),[]).append(int(i))
    normal=np.zeros((int(weld.max())+1,3));corner=np.array(g['normals'])
    for j in range(3):np.add.at(normal,weld[f[:,j]],corner[:,j])
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12);tree=BVHTree.FromPolygons(p.tolist(),f[np.isin(m,list(base))].tolist(),all_triangles=True);new=p.copy();selected=[];component_records=[]
    for group in components.values():
        side=max(['l','r'],key=lambda side:sum(sum(w for name,w in g['weights'][i].items() if name.endswith('_'+side)) for i in group));w=np.array(g['bones']['hand_'+side]['position']);axis=unit(w-np.array(g['bones']['lowerarm_'+side]['position']));dist=-(p[group]-w)@axis
        if dist.max()<=0 or np.median(dist)<-.5:continue
        hits=0;edge_fits=0
        for i,along in zip(group,dist):
            center=w-axis*along;direction=unit(p[i]-center);hit=tree.ray_cast(Vector(center+direction*12),Vector(-direction),12.)
            if hit[0] is None:
                hit=tree.find_nearest(Vector(p[i]));edge_fits+=1;normal_direction=unit(np.array(hit[1]));direction=normal_direction if np.dot(normal_direction,direction)>=0 else -normal_direction
            # Keep a closed 0.08 cm strap section after fitting its centre sheet.
            height=.14 if np.dot(normal[weld[i]],direction)>=0 else .06;new[i]=np.array(hit[0])+direction*height;hits+=1
        native_wrist_weights(d,g,group);selected.extend(group);component_records.append(dict(side=side,vertices=len(group),longitudinal_range_cm=[float(dist.min()),float(dist.max())],surface_hits=hits,hem_edge_fits=edge_fits))
    if not selected:raise RuntimeError('No native wrist webbing '+row['rig'])
    delta=np.linalg.norm(new-p,axis=1);d['positions']=new.tolist();smooth_transport(d,p);d['wrist_strap_fit']=dict(method='Own current glove surface; 0.08 cm webbing thickness; native forearm and hand support',binding='native_forearm_hand_renormalized_v1',native_sha256=row['sha256'],changed_vertices=int(np.count_nonzero(delta>1e-5)),max_move_cm=float(delta.max()),components=component_records);write(file,d);rows.append(entry);write(manifest,dict(completed=False,rows=rows));print('NATIVE_GLOVE_WRIST_WEBBING_FITTED',row['rig'],d['wrist_strap_fit'],flush=True)
write(manifest,dict(completed=True,rows=rows))
