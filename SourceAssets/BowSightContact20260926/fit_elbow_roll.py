"""Choose support upper-arm roll from local surface overlaps, keeping all joint centres fixed."""
import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;src=P/'generated_actions.py';text=src.read_text().split('bpy.ops.wm.read_factory_settings')[0]
needle='world[up]=mat(shoulder,du@rest[up].to_3x3())'
rows=[]
for amount in (0.,.25,.5,.75,1.):
    ns={'__file__':str(src)}
    altered=text.replace(needle,"if side=='l':\n            compatible=limb_frame(ud,hands[side]@ref_across)@limb_frame(ru,ref_across).transposed()\n            du=du.to_quaternion().slerp(compatible.to_quaternion(),"+str(amount)+").to_matrix()\n        "+needle)
    exec(compile(altered,str(src),'exec'),ns);d=ns['data'];rp=[ns['R']@Vector(p) for p in d['positions']]
    faces=[f for f,m in zip(d['triangles'],d['triangle_materials']) if m<2 and sum(w for n,w in d['weights'][f[0]].items() if n.endswith('_l'))>.5]
    row={'weight':amount,'states':[]}
    for role,t in [('Idle',0),('Draw',0),('Draw',.7),('Draw',1.4)]:
        pose=ns['pose'](role,t);skin={n:pose[n]@ns['rest'][n].inverted() for n in pose}
        pts=[sum((skin[n]@p*w for n,w in weights.items()),Vector()) for p,weights in zip(rp,d['weights'])]
        tree=BVHTree.FromPolygons(pts,faces,all_triangles=True);count=0
        for a,b in tree.overlap(tree):
            if a>=b or set(faces[a])&set(faces[b]):continue
            if any((pts[i]-pts[j]).length<.015 for i in faces[a] for j in faces[b]):continue
            count+=1
        row['states'].append({'role':role,'t':t,'overlaps':count})
    rows.append(row)
out=P.parents[1]/'Saved/BowSightContact20260926'
(out/'elbow-roll-fit.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
