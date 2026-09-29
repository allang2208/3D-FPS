"""Transport rigid plates and smooth shell/mail weights; preserve native liners."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
from original_leather_gloves import PROJECT as P, read, write

R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'


def rotation(bone):
    axes=np.asarray(bone['axes'],dtype=float)
    # Stored positions/geometry are already UE centimetres. M4 carries a 100
    # root scale whereas Body carries 1; applying that ratio would shrink armor.
    return (axes/np.linalg.norm(axes,axis=1)[:,None]).T


def main():
    root=R/'ArticulationSolve20260928/Candidate' if '--candidate' in sys.argv else R
    master=read(root/'Master/M4.json');parts=read(root/'parts.json')
    manifest=[];sources=read(R/'native-sources.json')
    for name,path in sources.items():
        if '--candidate' in sys.argv and name not in ('M4','M1911','DW715'):continue
        d=read(R/'Sources'/(name+'.json'))
        sides={n[-1] for w in d['weights'] for n in w if n.endswith(('_l','_r'))}
        for part in parts:
            bone=part['bone']
            if bone[-1] not in sides:continue
            sb=master['bones'][bone];tb=d['bones'][bone]
            rotate=rotation(tb)@rotation(sb).T
            vi=part['first_vertex'];nv=part['vertices'];fi=part['first_triangle'];nf=part['triangles']
            start=len(d['positions'])
            source_positions=np.asarray(master['positions'][vi:vi+nv])
            weights=master['weights'][vi:vi+nv]
            if part.get('binding')=='native_soft':
                positions=np.zeros_like(source_positions);rotations=np.zeros((nv,3,3))
                for bn in {b for w in weights for b in w}:
                    ids=np.array([i for i,w in enumerate(weights) if bn in w]);ws=np.array([weights[i][bn] for i in ids])
                    r=rotation(d['bones'][bn])@rotation(master['bones'][bn]).T
                    positions[ids]+=((source_positions[ids]-master['bones'][bn]['position'])@r.T+d['bones'][bn]['position'])*ws[:,None]
                    rotations[ids]+=r[None,:,:]*ws[:,None,None]
            else:
                positions=(source_positions-np.asarray(sb['position']))@rotate.T+np.asarray(tb['position'])
            d['positions'].extend(positions.tolist());d['weights'].extend(weights)
            d['triangles'].extend((np.asarray(master['triangles'][fi:fi+nf])-vi+start).tolist())
            normals=np.asarray(master['normals'][fi:fi+nf])
            normals=np.einsum('fkij,fkj->fki',rotations[np.asarray(master['triangles'][fi:fi+nf])-vi],normals) if part.get('binding')=='native_soft' else normals@rotate.T
            normals/=np.linalg.norm(normals,axis=2,keepdims=True)
            d['normals'].extend(normals.tolist());d['uv'].extend(master['uv'][fi:fi+nf]);d['triangle_materials'].extend([1]*nf)
        d['contract']='SteelGauntletV1: exact native liner; continuous deformable hand-back/wrist/thumb shell; rigid index/middle/ring/pinky plates; flexible mail; centimetre transport by normalized native bone frames; source animations unchanged'
        out=root/'Authored'/(name+'.json');out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
        manifest.append(dict(profile=name,authored=str(out),native_source=path,liner_material_group='Body' if name=='Body' else 'M4',triangles=len(d['triangles']),sides=sorted(sides)))
        print('STEEL_GAUNTLET_NATIVE_AUTHORED',name,len(d['triangles']),flush=True)
    write(root/'manifest.json',manifest)


if __name__=='__main__':main()
