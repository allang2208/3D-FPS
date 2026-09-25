"""Replace the glove cuff geometry by a continuous wrist loft on the native rig.

Retained surfaces keep their original weights. New cut vertices interpolate the
original surface; new wrist rings blend the two cut-boundary bindings.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector

PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4';ROOT=BASE/'RefinedSkinV3'
source=json.loads((BASE/'M4_original.json').read_text());shape=json.loads((ROOT/'hand_refit.json').read_text())
def point(p):return Vector((p[0],-p[1],p[2]))*.01
def vector(p):return Vector((p[0],-p[1],p[2])).normalized()
def ue(p):return [p.x*100,-p.y*100,p.z*100]
def un(p):return [p.x,-p.y,p.z]
bpy.ops.wm.open_mainfile(filepath=str(BASE/'M4_OriginalShape_BareHands_Editable.blend'))
obj=bpy.data.objects['M4_OriginalShape_BareHands'];obj.shape_key_clear()
mesh=bpy.data.meshes.new('M4_RefinedSkin_ContinuousWrist')
mesh.from_pydata([point(v) for v in shape['positions']],[],[list(reversed(t)) for t in source['triangles']]);mesh.update()
obj.data=mesh;obj.vertex_groups.clear()
bone_names=sorted({n for w in source['weights'] for n in w});group={n:obj.vertex_groups.new(name=n).index for n in bone_names}
for i,w in enumerate(source['weights']):
    for n,v in w.items():obj.vertex_groups[n].add([i],v,'REPLACE')
uv=mesh.uv_layers.new(name='NativeGrip_SkinUV')
for poly,coords,mat in zip(mesh.polygons,source['uv'],shape['triangle_materials']):
    poly.material_index=mat;poly.use_smooth=True
    for li,(u,v) in zip(poly.loop_indices,reversed(coords)):
        uv.data[li].uv=(u*.74 if mat==2 else u,1-v)
bm=bmesh.new();bm.from_mesh(mesh)
deform=bm.verts.layers.deform.active;uvlayer=bm.loops.layers.uv.active
normal_layers=[bm.loops.layers.float.new('SourceNormal'+str(i)) for i in range(3)]
for face,ns in zip(bm.faces,shape['normals']):
    for loop,n in zip(face.loops,reversed(ns)):
        v=vector(n)
        for j in range(3):loop[normal_layers[j]]=v[j]
# UV splits describe one physical surface; weld exact seam positions before
# cutting. This does not merge separate fingers or alter their bind weights.
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000008)
bm.normal_update()
reports=[]
for side in ('l','r'):
    fr=shape['anatomy'][side];origin=point(fr['wrist']);axis=vector(fr['forward']);dorsal=vector(fr['dorsal'])
    across=dorsal.cross(axis).normalized()
    if across.dot(vector(fr['across']))<0:across=-across
    def longitudinal(v):return (v.co-origin).dot(axis)
    def belongs(v):return v.co.x<0 if side=='l' else v.co.x>0
    cuts=(-.043,.027)
    for cut in cuts:
        vs=[v for v in bm.verts if belongs(v)];selected=set(vs)
        es=[e for e in bm.edges if all(v in selected for v in e.verts)]
        fs=[f for f in bm.faces if all(v in selected for v in f.verts)]
        bmesh.ops.bisect_plane(bm,geom=vs+es+fs,plane_co=origin+axis*cut,plane_no=axis,dist=.0000001)
    remove=[f for f in bm.faces if belongs(f.verts[0]) and cuts[0]+1e-7<sum(longitudinal(v) for v in f.verts)/len(f.verts)<cuts[1]-1e-7]
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    rings=[];centers=[];angles=[]
    for cut in cuts:
        edges=[e for e in bm.edges if e.is_boundary and all(belongs(v) and abs(longitudinal(v)-cut)<.00001 for v in e.verts)]
        adjacency={}
        for e in edges:
            a,b=e.verts;adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
        if not adjacency or any(len(v)!=2 for v in adjacency.values()):raise RuntimeError('Wrist cut must be a single closed skin loop')
        center=sum((v.co for v in adjacency),Vector())/len(adjacency)
        ring=sorted(adjacency,key=lambda v:math.atan2((v.co-center).dot(dorsal),(v.co-center).dot(across))%(2*math.pi))
        rings.append(ring);centers.append(center)
        angles.append([math.atan2((v.co-center).dot(dorsal),(v.co-center).dot(across))%(2*math.pi) for v in ring])
    def sample(ring,values,center,angle):
        import bisect
        upper=bisect.bisect_right(values,angle);hi=upper%len(ring);lo=(upper-1)%len(ring)
        a=values[lo];b=values[hi]
        if b<=a:b+=2*math.pi
        t=angle
        if t<a:t+=2*math.pi
        alpha=(t-a)/max(b-a,1e-9)
        radial=(ring[lo].co-center).length*(1-alpha)+(ring[hi].co-center).length*alpha
        weights={}
        for vertex,blend in ((ring[lo],1-alpha),(ring[hi],alpha)):
            for g,w in vertex[deform].items():weights[g]=weights.get(g,0)+w*blend
        return radial,weights
    count=72;rows=[rings[0]];fractions=[0.];ring_angles=[angles[0]]
    for j in range(1,12):
        f=j/12;center=centers[0].lerp(centers[1],f);row=[]
        for k in range(count):
            theta=2*math.pi*k/count
            r0,w0=sample(rings[0],angles[0],centers[0],theta)
            r1,w1=sample(rings[1],angles[1],centers[1],theta)
            radius=r0*(1-f)+r1*f
            v=bm.verts.new(center+(across*math.cos(theta)+dorsal*math.sin(theta))*radius)
            for g in set(w0)|set(w1):v[deform][g]=w0.get(g,0)*(1-f)+w1.get(g,0)*f
            row.append(v)
        rows.append(row);fractions.append(f);ring_angles.append([2*math.pi*k/count for k in range(count)])
    rows.append(rings[1]);fractions.append(1.);ring_angles.append(angles[1])
    def face(vertices,parameters):
        f=bm.faces.new(vertices);f.material_index=2;f.smooth=True
        for loop,(long,angle) in zip(f.loops,parameters):
            loop[uvlayer].uv=(.77+.21*long,1-(.04+(0 if side=='l' else .5)+.42*angle/(2*math.pi)))
    for index in range(len(rows)-1):
        lo,hi=rows[index:index+2];aa,bb=ring_angles[index:index+2];i=j=0
        # Periodic angular zipper accommodates the unchanged cut-loop counts.
        while i<len(lo) or j<len(hi):
            an=aa[(i+1)%len(lo)]+(2*math.pi if i+1>=len(lo) else 0)
            bn=bb[(j+1)%len(hi)]+(2*math.pi if j+1>=len(hi) else 0)
            ta=aa[i%len(lo)]+(2*math.pi if i>=len(lo) else 0)
            tb=bb[j%len(hi)]+(2*math.pi if j>=len(hi) else 0)
            if i<len(lo) and (j>=len(hi) or an<=bn):
                face([lo[i%len(lo)],lo[(i+1)%len(lo)],hi[j%len(hi)]],[(fractions[index],ta),(fractions[index],an),(fractions[index+1],tb)]);i+=1
            else:
                face([lo[i%len(lo)],hi[(j+1)%len(hi)],hi[j%len(hi)]],[(fractions[index],ta),(fractions[index+1],bn),(fractions[index+1],tb)]);j+=1
    reports.append({'side':side,'removed_cuff_faces':len(remove),'cut_loop_vertices':[len(r) for r in rings],
        'new_rings':11,'ring_vertices':count,'range_cm':[100*x for x in cuts]})

bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
for side in ('l','r'):
    fs=[f for f in bm.faces if (f.verts[0].co.x<0)==(side=='l')]
    direction=sum(f.normal.dot(Vector([sum(l[layer] for l in f.loops)/len(f.loops) for layer in normal_layers])) for f in fs)
    if direction<0:
        for f in fs:f.normal_flip()
bm.normal_update()
bm.verts.ensure_lookup_table();bm.verts.index_update();bm.faces.ensure_lookup_table()
positions=[ue(v.co) for v in bm.verts]
weights=[{bone_names[g]:w for g,w in v[deform].items() if w>0} for v in bm.verts]
triangles=[];uvs=[];normals=[];mats=[]
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
for f in bm.faces:
    # These Blender faces have already been oriented against the native
    # outward normals above. The Y reflection alone converts their winding
    # to UE; reversing them again makes the complete arm inside-out.
    loops=list(f.loops);triangles.append([l.vert.index for l in loops]);mats.append(f.material_index)
    uvs.append([[l[uvlayer].uv.x,1-l[uvlayer].uv.y] for l in loops]);row=[]
    for l in loops:
        n=l.vert.normal if f.material_index==2 else Vector([l[layer] for layer in normal_layers])
        if n.length<.5:n=l.vert.normal
        row.append(un(n.normalized()))
    normals.append(row)
out={**source,'positions':positions,'weights':weights,'triangles':triangles,'uv':uvs,'normals':normals,'triangle_materials':mats,
     'surface_winding':'ue_native'}
out.pop('source_vertex_ids',None);out.pop('source_triangle_ids',None)
(ROOT/'M4_original.json').write_text(json.dumps(out,separators=(',',':')))
shape.update({'positions':positions,'normals':normals,'triangle_materials':mats,'new_topology':True,
              'hand_vertices':[any(f.material_index==2 for f in v.link_faces) for v in bm.verts],
              'surface_winding':'ue_native'})
shape.pop('source_vertex_ids',None);shape.pop('source_triangle_ids',None)
(ROOT/'M4_bare_shape.json').write_text(json.dumps(shape,separators=(',',':')))
bm.to_mesh(mesh);bm.free();mesh.update()
for name in ('OriginalSleeves','OriginalForearmSkin','RefinedBareSkin'):mesh.materials.append(bpy.data.materials.new(name))
mesh.materials[0]=bpy.data.objects['SK_Manny_Arms_Export'].data.materials[0]
obj['AuthoringContract']='Native grip surfaces retained; glove cuff removed and continuous wrist lofted; boundary weights interpolated locally.'
obj.name='M4_OriginalShape_BareHands'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'M4_OriginalShape_BareHands_Editable.blend'))
(ROOT/'wrist_authoring.json').write_text(json.dumps(reports,indent=2))
print('CONTINUOUS_WRIST_SOURCE_SAVED',len(positions),len(triangles))
