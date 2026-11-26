"""Measure broad stone contact in exported geometry for the flat village pad."""
import json
import numpy as np
from wall_support_geometry import ROOT,load_mesh,rotate_vertices,bottom_profile

def longest_run(mask,step):
    longest=run=0
    for yes in mask:
        run=run+1 if yes else 0
        longest=max(longest,run)
    return longest*step

catalog={}
for letter in 'ABCD':
    for suffix in ('','_Mossy'):
        name='SM_H_StoneWall_00A_Piece'+letter+suffix
        v,f=load_mesh(name)
        # B and C have unsupported ledges when inverted. A/D have viable demo flips.
        for roll in ((0,180) if letter in 'AD' else (0,)):
            q=rotate_vertices(v,[0,0,roll]);xs,bottom=bottom_profile(q,f)
            bottom=bottom[np.isfinite(bottom)]
            ground=float(np.quantile(bottom,.90)+8.)
            while longest_run(bottom>ground-4.,2.)>20.:
                ground+=1.
            catalog[name+':'+str(roll)]=dict(ground_cm=round(ground,4),
                stone_min_cm=round(float(q[:,2].min()),4),stone_max_cm=round(float(q[:,2].max()),4),
                contact_fraction=round(float(np.mean(bottom<=ground-4.)),4),
                longest_unsupported_cm=longest_run(bottom>ground-4.,2.))
target=ROOT/'SourceAssets/TemperateHillsVillage/wall-support.json'
target.write_text(json.dumps(dict(version=1,source='Unreal static-mesh LOD0 triangles; OBJ X,Z,Y restored to UE X,Y,Z',
    max_wall_height_cm=130,contact_margin_cm=8,profiles=catalog),indent=2)+'\n',encoding='utf-8')
print('WALL_SUPPORT_PROFILES',len(catalog))
