"""Partition an existing forest-village planting stream without changing any records or their order."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
from scipy.spatial import cKDTree
from generate_slope_grass import POINT
from forest_wood_retirement import active_points

THEMES={'丘陵景观':'HillsLandscape','道路景观':'RoadLandscape'}

def store(points,terrain,dest,road_count=None,extra_count=None,*,only=None):
    if only is not None:
        only=THEMES.get(only,only)
        if only not in THEMES.values() or dest is None:raise ValueError('Choose a theme and output directory')
    records=np.fromfile(points/'planting.bin',POINT)
    palette=(points/'reference-meshes.txt').read_text(encoding='utf-8-sig').splitlines()
    lines=[np.loadtxt(terrain/(k+'-road.csv'),delimiter=',',skiprows=1)[:,:2] for k in ('gate','quarry')]
    guide=cKDTree(np.concatenate(lines))
    # The existing R14/R16 verge reaches 13.3 m. Use the source root, before mesh pivot correction.
    road=guide.query(np.c_[records['x'],records['y']]*.01)[0]<=13.3
    wet=[16+i for i,p in enumerate(palette) if 'SM_RiverDense_grass_04_03_mesh.' in p]
    road[np.isin(records['slot'],[15,*wet])]=False
    if road_count is None:
        info=points/'distribution.json'
        if info.exists():
            record=json.loads(info.read_text());road_count=record['roadside_candidates'];extra_count=record['wood_candidates']
    if extra_count:
        if not (0<=road_count<=extra_count<=len(road)):raise ValueError('Invalid dressing ownership range')
        wood=[16+i for i,p in enumerate(palette) if '/WoodlandDressing/Wood/' in p]
        if not np.isin(records['slot'][-extra_count:],wood).all():raise ValueError('Wood point order disagrees with its source recipe')
        start=len(road)-extra_count
        road[start:]=False;road[start:start+road_count]=True
    source_hash=hashlib.sha1(memoryview(records)).digest()
    # Bind ownership bits to the exact combined input. All older source files still support combined bakes.
    if only is None:
        mask_file=points/'planting.roadbits'
        staging=mask_file.with_suffix('.roadbits.tmp')
        staging.write_bytes(source_hash+np.packbits(road,bitorder='little').tobytes())
        staging.replace(mask_file)
    if dest is None:return
    dest.mkdir(exist_ok=True,parents=True)
    info={'source_sha1':source_hash.hex(),'corridor_m':13.3,'themes':{}}
    for name,mask in [('HillsLandscape',~road),('RoadLandscape',road)]:
        if only is not None and name!=only:continue
        out=dest/name;out.mkdir(exist_ok=True)
        (out/'theme.id').write_text(name,encoding='ascii')
        held,active_palette=active_points(records[mask],palette)
        held.tofile(out/'planting.bin')
        (out/'reference-meshes.txt').write_text('\n'.join(active_palette)+'\n',encoding='utf-8')
        if name=='HillsLandscape':
            for key in ('harvest-trees.f32','study-granite.i32'):shutil.copy2(points/key,out/key)
        info['themes'][name]=len(held)
        catalog=json.loads(Path(__file__).with_name('landscape_themes.json').read_text(encoding='utf-8-sig'))
        recipe=next(v for v in catalog['themes'] if v['id']==name)
        (out/'theme.json').write_text(json.dumps(dict(recipe,points=len(held),input_sha1=source_hash.hex()),ensure_ascii=False,indent=2),encoding='utf-8')
    if only is None:(dest/'partition.json').write_text(json.dumps(info,indent=2))
    return info

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('points',type=Path);parser.add_argument('terrain',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--theme',choices=[*THEMES,*THEMES.values()])
    a=parser.parse_args();store(a.points,a.terrain,a.output,only=a.theme)

