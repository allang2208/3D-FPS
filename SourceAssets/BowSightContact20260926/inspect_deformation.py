"""User-requested source deformation inspection; does not run the game."""
import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path('D:/FPS3D/FPSGAME');out=root/'Saved/BowSightContact20260926';rows=[]
for label,path in [('before','SourceAssets/DarkBow20260925/ReferenceUpgradeV10/author_actions.py'),('after','SourceAssets/BowSightContact20260926/generated_actions.py')]:
    src=root/path;ns={'__file__':str(src)}
    exec(compile(src.read_text(encoding='utf8').split('bpy.ops.wm.read_factory_settings')[0],str(src),'exec'),ns)
    d=ns['data'];restpoints=[ns['R']@Vector(p) for p in d['positions']]
    faces=[f for f,m in zip(d['triangles'],d['triangle_materials']) if m<2 and sum(w for n,w in d['weights'][f[0]].items() if n.endswith('_l'))>.5]
    for role,t in [('Idle',0),('Draw',0),('Draw',1.4)]:
        pose=ns['pose'](role,t);skin={n:pose[n]@ns['rest'][n].inverted() for n in pose}
        points=[sum((skin[n]@p*w for n,w in weights.items()),Vector()) for p,weights in zip(restpoints,d['weights'])]
        # Disconnected or wildly stretched triangles signal an authoring/skin
        # problem; report metrics without treating them as visual acceptance.
        ratios=[]
        for a,b,c in faces:
            old=(restpoints[b]-restpoints[a]).cross(restpoints[c]-restpoints[a]).length
            new=(points[b]-points[a]).cross(points[c]-points[a]).length
            if old>1e-6:ratios.append(new/old)
        tree=BVHTree.FromPolygons(points,faces,all_triangles=True)
        pairs=[]
        for a,b in tree.overlap(tree):
            if a>=b or set(faces[a])&set(faces[b]):continue
            # Duplicated seam vertices can share coordinates without an index.
            if any((points[i]-points[j]).length<.015 for i in faces[a] for j in faces[b]):continue
            pairs.append((a,b))
        rows.append({'version':label,'role':role,'t':t,'left_arm_faces':len(faces),
            'triangles_area_ratio_above_4':sum(x>4 for x in ratios),
            'triangles_area_ratio_below_025':sum(x<.25 for x in ratios),
            'nonadjacent_surface_overlap_pairs':len(pairs),
            'overlap_locations_cm':[list(sum((points[i] for i in faces[a]),Vector())/3) for a,b in pairs[:6]],
            'overlap_bones':sorted({n for a,b in pairs for i in faces[a] for n in d['weights'][i]})})
(out/'deformation-inspection.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
