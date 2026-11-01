from pathlib import Path
exec(compile((Path(__file__).parent/'author_profiles.py').read_text().split('report={};previews={};modified={}')[0],'setup','exec'))
from mathutils.bvhtree import BVHTree
patch=json.loads((O/'profile_patch.json').read_text())['profiles'];groups={g.index:g.name for g in skin.vertex_groups};ids=[v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if under(groups[g.group],'hand_l'))>.7];result={}
for label,profiles in (('before',original),('after',patch)):
    clip=ue['clips']['idle'];entry=next(c for c in profiles['base'] if c['base']==clip['path']);row,_=local_pose(clip,entry,0);set_pose(row);deps=bpy.context.evaluated_depsgraph_get();body=bpy.data.objects['M24_base'].evaluated_get(deps);me=body.to_mesh();tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons]);body.to_mesh_clear();ob=skin.evaluated_get(deps);me=ob.to_mesh();depths=[]
    for i in ids:
        p=ob.matrix_world@me.vertices[i].co;hit=tree.find_nearest(p)
        if hit[0] is None or hit[3]>.02 or (p-hit[0]).dot(hit[1])>=-.001:continue
        votes=0
        for direction in (Vector((1,.037,.019)).normalized(),Vector((.031,1,.017)).normalized(),Vector((.029,.023,1)).normalized()):
            origin=p.copy();count=0
            for _ in range(20):
                loc,normal,index,d=tree.ray_cast(origin,direction,2.)
                if loc is None:break
                count+=1;origin=loc+direction*.00001
            votes+=count%2
        if votes>=2:
            depths.append(hit[3]*1000)
            if hit[3]>.007:
                root=row['WPN_root']@rest['WPN_root'].inverted();print('DEEP_CONTACT',label,groups[max(skin.data.vertices[i].groups,key=lambda g:g.weight).group],round(hit[3]*1000,2),list(root.to_quaternion().inverted()@hit[1]),flush=True)
    ob.to_mesh_clear();result[label]={'inside_vertices_over_1mm':len(depths),'max_penetration_mm':max(depths,default=0.)}
(O/'contact.json').write_text(json.dumps(result,indent=2));print('IDLE_CONTACT',json.dumps(result),flush=True)
