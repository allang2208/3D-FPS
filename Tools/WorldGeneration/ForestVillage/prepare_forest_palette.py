"""Replace existing R19 canopy/rock sites deterministically on the official hill."""
from pathlib import Path
import json,sys
import numpy as np
from generate_slope_grass import POINT
def prepare(src,original,donor):
    grass=src/'Grass'
    rows=np.fromfile(original/'Grass/planting.bin',POINT)
    palette=(original/'Grass/reference-meshes.txt').read_text().splitlines()
    study=json.loads((donor/'reference.json').read_text())
    rng=np.random.default_rng(309177)
    canopy=np.flatnonzero(rows['slot']<2)
    outer=np.column_stack([rows[k][canopy] for k in ('x','y','yaw')])
    local=np.concatenate([np.fromfile(donor/(name+'.f32'),'<f4').reshape(-1,8)[:,[0,1,3]]
                          for name in study['pcg']['Forest path - Canopy']])
    trees=np.concatenate([outer,local])
    keep=np.ones(len(rows),dtype=bool)
    # Each 12 m cell owns at most one harvest ID. Choose among its actual PCG positions.
    chosen={}
    for i in rng.permutation(len(trees)):
        xy=tuple(np.floor(trees[i,:2]/1200.).astype(int))
        if xy not in chosen:chosen[xy]=i
    selected=np.asarray([chosen[k] for k in sorted(chosen) if rng.random()<.33])
    trees[selected].astype('<f4').tofile(grass/'harvest-trees.f32')
    keep[canopy[selected[selected<len(outer)]]]=False
    pool=sorted(json.loads((src/'rock-pool.json').read_text()),key=lambda m:m['mesh'])
    widths=np.array([r['width_cm'] for r in pool])
    if np.any(widths<=0):raise ValueError('Invalid granite extent')
    first=16+len(palette);palette.extend([p['mesh'] for p in pool])
    replace=[]
    study_xy=[]
    for name in study['pcg']['Forest path - Rocks']:
        slot=next(i+16 for i,p in enumerate(palette) if p.rsplit('.',1)[-1]==name)
        sites=np.flatnonzero(rows['slot']==slot)
        sites=sites[rng.random(len(sites))<.52]
        keep[sites]=False
        group=rows[sites].copy()
        a=np.fromfile(donor/(name+'.f32'),'<f4').reshape(-1,8)
        a=a[rng.random(len(a))<.52]
        study_xy.extend(a[:,:2])
        inside=np.empty(len(a),POINT)
        inside['x'],inside['y'],inside['yaw'],inside['size']=a[:,0],a[:,1],a[:,3],a[:,4]
        # The incoming width is in centimetres and matches the original rock footprint.
        group=np.concatenate([group,inside]);group['size']*=study['footprints'][name][2]*200.
        replace.append(group)
    group=np.concatenate(replace)
    variants=np.arange(len(group))%len(pool);rng.shuffle(variants)
    group['slot']=first+variants
    group['size']/=widths[variants]
    np.floor(np.array(study_xy)+.5).astype('<i4').tofile(grass/'study-granite.i32')
    with (grass/'planting.bin').open('wb') as f:
        rows[keep].tofile(f);group.tofile(f)
    (grass/'reference-meshes.txt').write_text('\n'.join(palette)+'\n')
    (src/'variation.json').write_text(json.dumps(dict(harvest_sites=len(selected),study_trees=int((selected>=len(outer)).sum()),
        granite_sites=len(group),study_rocks=len(study_xy),granite_meshes=len(pool),seed=309177),indent=2))
if __name__=='__main__':prepare(*map(Path,sys.argv[1:]))
