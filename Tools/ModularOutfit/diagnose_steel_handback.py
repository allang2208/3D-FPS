"""User-requested hand-back coverage diagnosis in the native rest pose."""
import json
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from original_leather_gloves import read,write
from build_steel_gauntlets import select_side,unit
from derive_steel_gauntlet_family import rotation


def main():
    root=R/'HandBackDiagnosis/Candidate' if '--candidate' in sys.argv else R
    profile=sys.argv[sys.argv.index('--profile')+1] if '--profile' in sys.argv else 'M4'
    reference=read(R/'Sources/M4.json');source=read(R/'Sources'/(profile+'.json'))
    master=read(root/'Master/M4.json') if profile=='M4' else read(R/'Authored'/(profile+'.json'))
    anatomy=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    report={}
    for side in ('r','l'):
        z=unit(anatomy[side]['dorsal']);w0=np.asarray(reference['bones']['hand_'+side]['position'])
        y=np.asarray(reference['bones']['middle_01_'+side]['position'])-w0;y=unit(y-z*(y@z));x=unit(np.cross(y,z))
        if x@(np.asarray(reference['bones']['thumb_01_'+side]['position'])-w0)<0:x=-x
        transform=rotation(source['bones']['hand_'+side])@rotation(reference['bones']['hand_'+side]).T
        x,y,z=(transform@v for v in (x,y,z));w=np.asarray(source['bones']['hand_'+side]['position'])
        faces=select_side(source,side);skin=BVHTree.FromPolygons([Vector(p) for p in source['positions']],faces,all_triangles=True)
        core=np.asarray([sum(v for b,v in ws.items() if b=='hand_'+side or ('metacarpal_'+side in b)) for ws in source['weights']])
        steel_faces=[face for face,material in zip(master['triangles'],master['triangle_materials'])
            if material==1 and all(any(b.endswith('_'+side) for b in master['weights'][vi]) for vi in face)]
        steel=BVHTree.FromPolygons([Vector(p) for p in master['positions']],steel_faces,all_triangles=True)
        hits=[];misses=[];rows={}
        for vy in np.arange(.2,9.61,.2):
            row=[]
            for vx in np.arange(-6.5,6.51,.2):
                origin=w+x*vx+y*vy+z*12
                hit,normal,fi,_=skin.ray_cast(Vector(origin),Vector(-z),24.)
                if hit is None or core[faces[fi]].mean()<.65 or abs(np.asarray(normal)@z)<.30:continue
                mhit,_,_,_=steel.ray_cast(Vector(origin),Vector(-z),24.)
                covered=mhit is not None and (np.asarray(mhit)-np.asarray(hit))@z>.02
                target=hits if covered else misses;target.append([float(vx),float(vy)])
                row.append(float(vx))
            if row:rows[round(float(vy),2)]=[min(row),max(row)]
        report[side]=dict(target_samples=len(hits)+len(misses),covered_samples=len(hits),
            coverage_fraction=len(hits)/max(1,len(hits)+len(misses)),uncovered_xy=misses,palm_rows=rows)
    label=sys.argv[sys.argv.index('--label')+1] if '--label' in sys.argv else 'current'
    write(R/'HandBackDiagnosis'/(label+'.json'),report)
    for side,row in report.items():print('HAND_BACK_COVERAGE',profile,side,row['covered_samples'],row['target_samples'],round(row['coverage_fraction'],4),flush=True)


if __name__=='__main__':main()
