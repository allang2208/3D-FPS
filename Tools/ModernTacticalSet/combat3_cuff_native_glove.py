"""Fit the confirmed legacy Body/Super90 glove cuff mismatch to native skin."""
import sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import C,read,write,unit,smooth
from shirt_geometry import smooth_transport
def fit(rig):
    file=C/'Authored'/f'gloves_{rig}.json';d=read(file)
    if d.get('native_cuff_fit',{}).get('method')=='current_native_skin_v2':return
    records=read(C/'captured.json')['rows'];row=next(r for r in records if r['key']=='Native_'+rig);native=read(row['file']);original=read(next(r['file'] for r in records if r['key']=='Glove_'+rig));shirt=read(C/'Authored'/f'shirt_fp_{rig}.json');p=np.array(d['positions']);new=p.copy();nf=np.array(native['triangles']);np0=np.array(native['positions']);tree=BVHTree.FromPolygons(np0.tolist(),nf.tolist(),all_triangles=True);bones={b['name']:b for b in d['bones']};names={b['index']:b['name'] for b in d['bones']};byname={b['name']:b['index'] for b in d['bones']};f=np.array(d['triangles']);m=np.array(d['triangle_materials']);webbing_slots={i for i,name in enumerate(d['material_slots']) if 'Webbing' in name};webbing=set(np.unique(f[np.isin(m,list(webbing_slots))]).tolist());side_of=[max(['l','r'],key=lambda s:sum(w for bi,w in ws if names[bi].endswith('_'+s))) for ws in d['weights']];intervals={};original_p=np.array(original['positions']);_,weld=np.unique(np.round(original_p,5),axis=0,return_inverse=True);normal=np.zeros((int(weld.max())+1,3));corner=np.array(original['normals'])
    for j in range(3):np.add.at(normal,weld[f[:,j]],corner[:,j])
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    for side in ['l','r']:
        ids=np.array([i for i,s in enumerate(side_of) if s==side]);w=np.array(bones['hand_'+side]['position']);axis=unit(w-np.array(bones['lowerarm_'+side]['position']));cut=shirt['cloth_production']['contact'][side]['cut_cm'];start=cut-1.3;end=cut-.2;intervals[side]=[start,end]
        for i in ids:
            dist=-np.dot(p[i]-w,axis);alpha=float(smooth((dist-start)/(end-start)))
            if alpha<=0:continue
            center=w-axis*dist;direction=unit(p[i]-center);hit=tree.ray_cast(Vector(center+direction*15),Vector(-direction),15.)
            if hit[0] is None:raise RuntimeError('Native cuff skin ray missed '+rig+' '+side)
            outward=np.dot(normal[weld[i]],direction)>=0;height=(.15 if outward else .07) if i in webbing else (.085 if outward else .025);target=np.array(hit[0])+direction*height;baseline=p[i] if i in webbing else original_p[i];new[i]=baseline*(1-alpha)+target*alpha;verts=nf[hit[2]];a,b,c=np0[verts];uv=np.linalg.lstsq(np.stack([b-a,c-a],axis=1),np.array(hit[0])-a,rcond=None)[0];coeff=np.clip([1-uv.sum(),uv[0],uv[1]],0,1);coeff/=coeff.sum();weights={bi:weight*(1-alpha) for bi,weight in d['weights'][i]}
            target_weights={}
            for vi,factor in zip(verts,coeff):
                for name,value in native['weights'][int(vi)].items():target_weights[name]=target_weights.get(name,0)+value*float(factor)
            if i in webbing:target_weights={name:value for name,value in target_weights.items() if name.startswith(('lowerarm','hand_'))}
            total=sum(target_weights.values())
            for name,value in target_weights.items():weights[byname[name]]=weights.get(byname[name],0)+value/total*alpha
            pairs=sorted(((bi,value) for bi,value in weights.items() if value>1e-7),key=lambda item:-item[1])[:8];total=sum(v for _,v in pairs);d['weights'][i]=[[bi,value/total] for bi,value in pairs]
    d['positions']=new.tolist();smooth_transport(d,p);delta=np.linalg.norm(new-p,axis=1);d['native_cuff_fit']=dict(method='current_native_skin_v2',native_sha256=row['sha256'],blend_intervals_cm=intervals,changed_vertices=int(np.count_nonzero(delta>1e-5)),max_move_cm=float(delta.max()),fingers_unchanged=True,cloth_thickness_cm=.06,webbing_thickness_cm=.08);write(file,d);print('LEGACY_GLOVE_CUFF_FITTED_TO_OWN_SKIN',rig,d['native_cuff_fit'],flush=True)
if __name__=='__main__':
    for rig in ['Body','Super90']:fit(rig)
