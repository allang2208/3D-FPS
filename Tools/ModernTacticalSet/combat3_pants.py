"""Settle a sewn trouser proxy, then carry all native layers through that field."""
import bpy,bmesh,sys,numpy as np,copy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cloth import R,B,read,write,settle,mesh,smooth
from shirt_geometry import smooth_transport
def main(rig):
    d=read(B/'Authored'/f'pants_{rig}.json');body=read(R/'Inputs'/f'Body_{rig}.json');p=np.array(d['positions']);f=np.array(d['triangles']);mat=np.array(d['triangle_materials']);n=np.array(d['normals']).mean(1);center=p[f].mean(1);bt=BVHTree.FromPolygons(body['positions'],body['triangles'],all_triangles=True)
    keep=[]
    for i,q in enumerate(center):
        if d['material_slots'][mat[i]] not in ['TS01_RangerRipstop','TS01_RangerNylon','TS01_CharcoalStretch']:continue
        hit=bt.find_nearest(Vector(q))
        if hit[0] is not None and np.dot(q-np.array(hit[0]),n[i])>.015:keep.append(i)
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    ob=mesh('SewnTrouserOuter',p,f[keep].tolist());bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00003)
    unseen=set(bm.faces);islands=[]
    while unseen:
        first=next(iter(unseen));group={first};stack=[first]
        while stack:
            face=stack.pop()
            for edge in face.edges:
                for other in edge.link_faces:
                    if other not in group:group.add(other);stack.append(other)
        unseen-=group;islands.append(group)
    largest=max(islands,key=lambda group:sum(face.calc_area() for face in group));bmesh.ops.delete(bm,geom=[face for group in islands if group is not largest for face in group],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    if len(ob.data.polygons)>16000:
        mod=ob.modifiers.new('PhysicalClothProxy','DECIMATE');mod.ratio=16000/len(ob.data.polygons);bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();q=np.array([v.co[:] for v in ob.data.vertices])*[100,-100,100];tri=np.array([list(face.vertices) for face in ob.data.polygons]);pins=np.maximum(smooth((q[:,2]-91.5)/4.0),1-smooth((q[:,2]-17)/5));rest=q.copy();rest[:,2]=97-(97-q[:,2])*1.085
    bones={b['name']:np.array(b['position']) for b in body['bones']}
    for side,sign in [('l',1),('r',-1)]:
        ids=np.flatnonzero(q[:,0]*sign>0);knee=bones['calf_'+side];pad=np.exp(-((q[ids,2]-knee[2])/5.5)**4)*smooth((q[ids,1]-knee[1])/5);pins[ids]=np.maximum(pins[ids],pad*.8)
    print('TROUSER_PROXY',rig,len(q),len(tri),flush=True);moved=settle('Trousers_'+rig,q,tri,rest,pins,body,frames=42);tree=BVHTree.FromPolygons(q.tolist(),tri.tolist(),all_triangles=True)
    for kind,cut in [('pants',17),('pants_boot',35),('pants_short',23),('pants_high',58),('pants_tactical',38)]:
        out=read(B/'Authored'/f'{kind}_{rig}.json');original=np.array(out['positions']);new=original.copy();faces=np.array(out['triangles']);cloth=np.unique(faces[[not out['material_slots'][i].startswith('NATIVE:') for i in out['triangle_materials']]])
        for i in cloth:
            pt=original[i];factor=float((1-smooth((pt[2]-91.5)/4))*smooth((pt[2]-cut)/6))
            if factor<=0:continue
            hit=tree.find_nearest(Vector(pt))
            if hit[0] is None:continue
            face=tri[hit[2]];before=[Vector(v) for v in q[face]];after=[Vector(v) for v in moved[face]];delta=np.array(barycentric_transform(hit[0],*before,*after))-np.array(hit[0]);new[i]+=delta*factor
        out['positions']=new.tolist();smooth_transport(out,original);out['cloth_production']=dict(method='Offline sewn trouser proxy; native-body collision; common displacement for shell, facing, seams and pockets',native_waist_preserved_above_cm=95.5,boot_tuck_preserved_below_cm=cut)
        out['materials']=[m.replace('CombatShirtR2','CombatShirtR3') for m in out['materials']];write(R/'Authored'/f'{kind}_{rig}.json',out);print('NATIVE_TROUSER_FOLDS',rig,kind,flush=True)
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1])
