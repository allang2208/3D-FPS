"""V3 shaped cuff construction in centimetres; unchanged native bindings and grips."""
from collections import defaultdict
import numpy as np
import black_leather_detail as base
from black_leather_detail import *

V1=base.R
R=V1/'TailoredSurfaceV3'


def matrix(bone):
    # Mesh positions are already centimetres for both Body and FPS sources.
    # Imported root scales (1 versus 100) are not another geometry scale.
    out=np.eye(4);out[:3,:3]=unit(np.asarray(bone['axes'])).T
    out[:3,3]=bone['position'];return out


base.matrix=matrix


def contact_polish(points,normals,weights,bones,anatomy):
    """Palmar contact zones follow each finger's local surface direction."""
    value=np.zeros(len(points))
    for side in ('l','r'):
        ids=np.array([i for i,w in enumerate(weights) if sum(v for k,v in w.items() if k.endswith('_'+side))>.5])
        if not len(ids):continue
        f,wrist=frame(bones,anatomy,side);q=(points[ids]-wrist)@f.T
        dorsal=np.tile(f[2],(len(ids),1));digits=np.zeros(len(ids));pads=np.zeros(len(ids))
        for spec in anatomy[side]['digits']:
            mass=np.array([weights[i].get(spec['bone'],0) for i in ids])
            if mass.max()<1.e-7:continue
            t=(points[ids]-np.asarray(spec['head']))@np.asarray(spec['axis'])/spec['length']
            dorsal+=mass[:,None]*(np.asarray(spec['dorsal'])-f[2])
            digits+=mass;pads+=mass*gauss(t,.48,.60)
        palm=smooth(.20,.83,-(unit(dorsal)*normals[ids]).sum(1))
        contact=.72*gauss(q[:,0],-.5,2.65)*gauss(q[:,1],4.5,2.7)*(1-np.clip(digits,0,1))+.94*pads
        value[ids]=np.clip(palm*contact,0,1)
    return value


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
    radii=np.full(len(p),.30);lip_shift=np.zeros(len(p))
    zones=np.zeros((len(p),4));zones[:,0]=contact_polish(p,n,source['weights'],master['bones'],anatomy)
    for side in ('l','r'):
        ids=np.array([i for i,w in enumerate(source['weights']) if sum(v for k,v in w.items() if k.endswith('_'+side))>.5])
        if not len(ids):continue
        f,wrist=frame(master['bones'],anatomy,side)
        coords=(p[ids]-wrist)@f.T
        radial=unit(n[ids]-(n[ids]@f[1])[:,None]*f[1])
        own=set(ids.tolist());selected=np.array([first[v] for v in border_ids if first[v] in own])
        bc=(p[selected]-wrist)@f.T
        # Follow the actual native cuff cut, including the shorter Body cuff.
        theta=np.arctan2(coords[:,2],coords[:,0]);bt=np.arctan2(bc[:,2],bc[:,0])
        order=np.argsort(bt);bt=bt[order];by=bc[order,1]
        border_y=np.interp(theta,np.r_[bt[-1]-2*np.pi,bt,bt[0]+2*np.pi],np.r_[by[-1],by,by[0]])
        axial=coords[:,1]-border_y
        dorsal=smooth(-.40,.70,radial@f[2])
        # The inner wrist remains thinner and locally compressed while the
        # dorsal edge retains a readable padded lip. No inward skin offset.
        compressed=1-.14*gauss(np.cos(theta),-.77,.20)-.09*gauss(np.cos(theta),.78,.18)
        rim=(.17+.15*dorsal)*compressed
        fade=1-smooth(0,2.5,axial)
        folds=(.044*gauss(axial,.80+.11*np.sin(theta*2),.23)
               -.017*gauss(axial,1.13+.10*np.sin(theta*2),.17)
               +.022*gauss(axial,1.63+.12*np.sin(theta*3),.26))
        folds*=fade*smooth(.15,.48,axial)*(.25+.75*(1-dorsal))
        thickness=np.maximum(rim*fade+folds,0)
        edge_wobble=(.026*np.sin(2*theta+.6)+.014*np.sin(3*theta-.4))
        offset[ids]=radial*thickness[:,None]+f[1]*((edge_wobble*fade)[:,None])
        directions[ids]=radial;forward[ids]=f[1]
        radii[ids]=rim;lip_shift[ids]=edge_wobble
        zones[ids,1]=1-smooth(.42,1.55,axial)
        zones[ids,2]=gauss(axial,1.2,.80)*(1-dorsal)*smooth(.2,.6,axial)
        zones[ids,3]=dorsal
    positions=np.asarray(source['positions'])+np.einsum('nij,nj->ni',delta,offset)
    ns=transported_normals(source,positions).tolist()
    out=dict(source,positions=positions.tolist(),normals=ns,
             triangles=triangles.tolist(),weights=[dict(w) for w in source['weights']],
             uv=list(source['uv']),triangle_materials=list(source['triangle_materials']),surface_zones=zones.tolist())
    rings=[{v:int(first[v]) for v in border_ids}]
    # Rolled outer lip, end face, inner wall and 5.5 mm return. All rings use
    # their own original cuff-edge skin blend so they stay together in motion.
    for radius,along in [(.285,-.07),(.19,-.13),(.08,-.11),(.015,-.04),(.015,.55)]:
        row={}
        for v in border_ids:
            i=int(first[v]);scale=radii[i]/.30
            ring_radius=radius*scale if radius>.015 else radius
            cp=p[i]+directions[i]*ring_radius+forward[i]*(along*(.70+.30*scale)+lip_shift[i])
            dp=cp-p[i]
            pos=np.asarray(source['positions'][i])+delta[i]@dp
            row[v]=len(out['positions']);out['positions'].append(pos.tolist());out['weights'].append(dict(source['weights'][i]))
            out['surface_zones'].append([0.,1.,0.,float(zones[i,3])])
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
    out['cuff_construction']={'dorsal_thickness_cm':.32,'inner_wrist_thickness_cm':.17,
        'side_compression_fraction':.14,'inner_return_cm':.55,'added_triangles':len(new),'original_triangles':start,
        'real_soft_folds':True,'grip_geometry_unchanged':True}
    return out


def prepare():
    import shutil
    R.mkdir(parents=True,exist_ok=True)
    recipe=read(P/'Content/ColdSteelData/modular_outfits.json')['items']['ue_field_gloves_black']
    previous=read(V1/'ReliefCuffV2/published.json')['recipe']
    if recipe!=previous and recipe.get('appearance_family')!='BlackLeatherTailoredSurfaceV3':
        raise RuntimeError('The black glove has another appearance revision; preserve it before replacing this item')
    if not (R/'before-recipe.json').exists():write(R/'before-recipe.json',recipe)
    sources=read(V1/'native-sources.json');write(R/'native-sources.json',sources)
    master=read(V1/'Sources/M4.json');anatomy=read(ANATOMY)['anatomy']
    for name in sources:
        output=prepare_source(read(V1/'Sources'/(name+'.json')),master,anatomy)
        write(R/'Sources'/(name+'.json'),output)
        print('RELIEF_CUFF_SOURCE',name,output['cuff_construction'],flush=True)


if __name__=='__main__':prepare()
