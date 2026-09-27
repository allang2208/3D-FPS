"""Apply the selected tailoring to current native fit surfaces, no animation edits."""
import json
import hashlib
import shutil
from pathlib import Path
import numpy as np
import tailored_fingerless_candidate as lib

P=lib.P
R=P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessV1'
OLD=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
CAND=lib.ROOT


def matrix(b):
    m=np.eye(4);m[:3,:3]=np.array(b['axes']).T;m[:3,3]=b['position'];return m


def local_coordinates(d,master,anatomy):
    p=np.array(d['positions']);local=np.zeros_like(p)
    for side in ('l','r'):
        own=np.array([sum(v for n,v in w.items() if n.endswith('_'+side))>.5 for w in d['weights']])
        if not own.any():continue
        frame,wrist=lib.frame(master['bones'],anatomy,side)
        transform=matrix(d['bones']['hand_'+side])@np.linalg.inv(matrix(master['bones']['hand_'+side]))
        original=(np.c_[p[own],np.ones(own.sum())]@np.linalg.inv(transform).T)[:,:3]
        local[own]=(original-wrist)@frame.T
    return local


def main():
    (R/'Authored').mkdir(parents=True,exist_ok=True)
    (R/'Textures').mkdir(exist_ok=True)
    for path in (CAND/'Textures').glob('T_TailoredFingerless_*.png'):shutil.copy2(path,R/'Textures'/path.name)
    shutil.copy2(CAND/'TailoredFingerless_Icon.png',R/'TailoredFingerless_Icon.png')
    master=lib.read(OLD/'FullShell/M4.json');baked=lib.read(CAND/'M4_baked_fullshell.json')
    anatomy=lib.read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    original_local=local_coordinates(master,master,anatomy)
    original_weights=master['weights'];groups={};manifest=[]
    # Store the current item recipe as a narrowly scoped publication baseline.
    cfg=lib.read(P/'Content/ColdSteelData/modular_outfits.json')
    (R/'before-item-recipe.json').write_text(json.dumps(cfg['items']['ue_field_gloves'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in lib.read(OLD/'manifest.json'):
        name=row['profile'];source=OLD/'FullShell'/(name+'.json');d=lib.read(source)
        if len(d['positions'])==len(master['positions']):
            pattern=original_local
        else:
            pattern=local_coordinates(d,master,anatomy)
        authored=lib.author(source,R/'Authored',pattern)
        authored.update(family='TailoredFingerlessV1',contract='Selected brown tailoring; native fitted skin boundaries; shared animation and timing')
        # A UV layout may be shared only by matching ordered native topology.
        selected=np.arange(len(baked['triangles']));canonical=baked
        sides={n[-1] for w in d['weights'] for n in w if n.endswith(('_l','_r'))}
        if len(sides)==1:
            side=next(iter(sides));own=np.array([sum(v for n,v in w.items() if n.endswith('_'+side))>.5 for w in baked['weights']])
            used=np.flatnonzero(own);remap=np.full(len(own),-1,dtype=int);remap[used]=np.arange(len(used))
            selected=np.flatnonzero(own[np.array(baked['triangles'])].all(1))
            canonical=dict(baked,triangles=remap[np.array(baked['triangles'])[selected]].tolist())
        if authored['triangles']==canonical['triangles']:
            authored['uv']=[baked['uv'][i] for i in selected];group='Shared';needs_bake=False
        else:
            # Body and locally closed single-hand caps keep their topology and
            # get their own UV bake. This never replaces their native seam fit.
            signature=hashlib.sha256(json.dumps(authored['triangles']).encode()).hexdigest()
            group=groups.setdefault(signature,name);needs_bake=group==name
        path=R/'Authored'/(name+'_fullshell.json')
        path.write_text(json.dumps(authored,separators=(',',':')))
        manifest.append(dict(profile=name,fullshell=str(path),material_group=group,bake_representative=needs_bake,
                             source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                             source_skin=str(OLD/'SkinCoverage'/(name+'_review.json'))))
        print('TAILORED_FAMILY_PROFILE',name,group,flush=True)
    (R/'author-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
