"""V2 cuff construction in centimetres; unchanged native bindings and grips."""
from collections import defaultdict
import numpy as np
import black_leather_detail as base
from black_leather_detail import *

V1=base.R
R=V1/'ReliefCuffV2'


def matrix(bone):
    # Mesh positions are already centimetres for both Body and FPS sources.
    # Imported root scales (1 versus 100) are not another geometry scale.
    out=np.eye(4);out[:3,:3]=unit(np.asarray(bone['axes'])).T
    out[:3,3]=bone['position'];return out


base.matrix=matrix


def prepare_source(source,master,anatomy):
    p,n,delta=to_canonical(source,master)
    triangles=np.asarray(source['triangles'])
    _,first,inverse=np.unique(np.round(p,4),axis=0,return_index=True,return_inverse=True)
    edges=defaultdict(list)
    for tri in triangles:
        for j in range(3):
            a,b=int(tri[j]),int(tri[(j+1)%3])
            edges[tuple(sorted((inverse[a],inverse[b])))].append((a,b))
    border=[pair[0] for pair in edges.values() if len(pair)==1]
    border_ids=sorted({int(inverse[v]) for edge in border for v in edge})
    directions=np.zeros_like(p);offset=np.zeros_like(p);forward=np.zeros_like(p)
    for side in ('l','r'):
        ids=np.array([i for i,w in enumerate(source['weights']) if sum(v for k,v in w.items() if k.endswith('_'+side))>.5])
        if not len(ids):continue
        f,wrist=frame(master['bones'],anatomy,side)
        coords=(p[ids]-wrist)@f.T
        radial=unit(n[ids]-(n[ids]@f[1])[:,None]*f[1])
        selected=np.array([first[v] for v in border_ids if first[v] in set(ids.tolist())])
        bc=(p[selected]-wrist)@f.T
        # Follow the actual native cuff cut, including the shorter Body cuff.
        theta=np.arctan2(coords[:,2],coords[:,0]);bt=np.arctan2(bc[:,2],bc[:,0])
        nearest=np.abs(np.angle(np.exp(1j*(theta[:,None]-bt[None,:])))).argmin(1)
        axial=coords[:,1]-bc[nearest,1]
        thickness=.30*(1-smooth(0,2.5,axial))
        offset[ids]=radial*thickness[:,None]
        directions[ids]=radial;forward[ids]=f[1]
    positions=np.asarray(source['positions'])+np.einsum('nij,nj->ni',delta,offset)
    ns=transported_normals(source,positions).tolist()
    out=dict(source,positions=positions.tolist(),normals=ns,
             triangles=triangles.tolist(),weights=[dict(w) for w in source['weights']],
             uv=list(source['uv']),triangle_materials=list(source['triangle_materials']))
    rings=[{v:int(first[v]) for v in border_ids}]
    # Rolled outer lip, end face, inner wall and 5.5 mm return. All rings use
    # their own original cuff-edge skin blend so they stay together in motion.
    for radius,along in [(.285,-.07),(.19,-.13),(.08,-.11),(.015,-.04),(.015,.55)]:
        row={}
        for v in border_ids:
            i=int(first[v]);cp=p[i]+directions[i]*radius+forward[i]*along
            dp=cp-p[i]
            pos=np.asarray(source['positions'][i])+delta[i]@dp
            row[v]=len(out['positions']);out['positions'].append(pos.tolist());out['weights'].append(dict(source['weights'][i]))
        rings.append(row)
    start=len(out['triangles'])
    for inner,outer in zip(rings[1:],rings[:-1]):
        for a,b in border:
            va,vb=int(inverse[a]),int(inverse[b])
            for face in ([outer[vb],outer[va],inner[va]],[outer[vb],inner[va],inner[vb]]):
                out['triangles'].append(face);out['triangle_materials'].append(0)
                out['uv'].append([[0,0],[0,0],[0,0]])
    # UE source triangles are clockwise. Average only the newly made cuff
    # vertices; preserve the authored split normals on all original faces.
    pos=np.asarray(out['positions']);new=np.asarray(out['triangles'][start:])
    normals=np.zeros_like(pos)
    cross=-np.cross(pos[new[:,1]]-pos[new[:,0]],pos[new[:,2]]-pos[new[:,0]])
    for j in range(3):np.add.at(normals,new[:,j],cross)
    normals=unit(normals)
    out['normals']+=normals[new].tolist()
    out['cuff_construction']={'outer_thickness_cm':.30,'inner_return_cm':.55,'added_triangles':len(new),'original_triangles':start}
    return out


def prepare():
    import shutil
    R.mkdir(parents=True,exist_ok=True)
    recipe=read(P/'Content/ColdSteelData/modular_outfits.json')['items']['ue_field_gloves_black']
    if not (R/'before-recipe.json').exists():write(R/'before-recipe.json',recipe)
    sources=read(V1/'native-sources.json');write(R/'native-sources.json',sources)
    master=read(V1/'Sources/M4.json');anatomy=read(ANATOMY)['anatomy']
    for name in sources:
        output=prepare_source(read(V1/'Sources'/(name+'.json')),master,anatomy)
        write(R/'Sources'/(name+'.json'),output)
        print('RELIEF_CUFF_SOURCE',name,output['cuff_construction'],flush=True)


if __name__=='__main__':prepare()
