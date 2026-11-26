"""Rebuild grass and wet-bank dressing on the authoritative pool raster without reassigning harvest IDs."""
from pathlib import Path
import sys
import shutil
import numpy as np

from continuous_meadow import bake
from generate_forest_reference import sedge_points
from generate_slope_grass import POINT, generate, grid_at

def prepare(root,out):
    grass=out/'Grass';flora=root/'VillageFlora-R20'
    paths=(grass/'reference-meshes.txt').read_text(encoding='utf-8-sig').splitlines()
    bank='/Game/WorldGeneration/TemperateHills/RiverEcologyDense/SM_RiverDense_grass_04_03_mesh.SM_RiverDense_grass_04_03_mesh'
    sedge=16+paths.index(bank)
    original=np.fromfile(flora/'Grass/planting.bin',POINT)
    # Keep the dry forest, including the R20 granite variants. The per-cell author regenerates the grass.
    original[~np.isin(original['slot'],[12,13,14,sedge])].tofile(out/'planting.bin')
    generate(out,grass,root/'WildGrass-oilox20',verge_in_green=True,understory=True)
    shore=np.fromfile(grass/'pond_shore.u8','u1').reshape(1025,1025)/255.
    depth=np.fromfile(grass/'pond_depth.u8','u1').reshape(4097,4097).astype('f4')
    rng=np.random.default_rng(237855)
    x,y,yaw,size=sedge_points(shore,rng)
    water=grid_at(depth,x,y,step=.25)
    keep=(grid_at(shore,x,y)>.01)&((water==0)|((water<=9)&(rng.random(x.size)<.2)))
    points=np.empty(len(x),POINT)
    points['x'],points['y'],points['yaw'],points['size'],points['slot']=x*100,y*100,yaw,size,sedge
    with (grass/'planting.bin').open('ab') as stream:points[keep].tofile(stream)
    (out/'Turf').mkdir(exist_ok=True)
    for filename in ('T_VillageGrass_B.png','T_VillageGrass_N.png'):shutil.copy2(flora/'Turf'/filename,out/'Turf'/filename)
    z=np.fromfile(out/'region.i16','<i2').reshape(1025,1025).astype('f4')
    paint=np.fromfile(out/'paint.rg8','u1').reshape(1025,1025,2)
    bake(out,out,z,paint)
    from landscape_theme_points import store
    store(grass,out,None,0,0)

if __name__=='__main__':prepare(Path(sys.argv[1]),Path(sys.argv[2]))
