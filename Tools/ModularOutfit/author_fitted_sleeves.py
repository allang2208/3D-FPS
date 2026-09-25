"""Rebuild sweater cuffs against V7 skin, keeping the existing upper sleeves.

Blender background authoring only. No animations or bare-hand assets are edited.
The original garment already has inner/outer faces: do not Solidify it again.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

PROJECT=Path(__file__).resolve().parents[2]
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925/FittedSleevesV1'
BARE=PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7'
SOURCES=PROJECT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def reflect(v):return Vector((v[0],-v[1],v[2]))
def unreflect(v):return [v.x,-v.y,v.z]
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def bind(b):
    m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m
def normalized(w):
    w=dict(sorted(((n,v) for n,v in w.items() if v>1e-7),key=lambda x:-x[1])[:8]);total=sum(w.values())
    return {n:v/total for n,v in w.items()}

source=read(ROOT/'M4_shirt_before.json');native=read(SOURCES/'M4.json')
bare=read(BARE/'M4_original.json')
frames=read(PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
names=sorted({n for w in source['weights']+bare['weights'] for n in w})
name_id={n:i for i,n in enumerate(names)}
matrices={n:bind(native['bones'][n])@np.linalg.inv(bind(source['bones'][n])) for n in {n for w in source['weights'] for n in w}}
positions=[reflect((sum(matrices[n]*w for n,w in weights.items())@np.append(p,1))[:3])
           for p,weights in zip(source['positions'],source['weights'])]
mesh=bpy.data.meshes.new('ExistingSweaterCanonical')
mesh.from_pydata(positions,[],source['triangles']);mesh.update()
bm=bmesh.new();bm.from_mesh(mesh)
deform=bm.verts.layers.deform.verify();uv_layer=bm.loops.layers.uv.verify()
normal_layer=bm.loops.layers.float_vector.new('OriginalSurfaceNormal')
bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
for v,w in zip(bm.verts,source['weights']):
    for n,value in w.items():v[deform][name_id[n]]=value
for face,uvs,ns in zip(bm.faces,source['uv'],source['normals']):
    for loop,uv,n in zip(face.loops,uvs,ns):
        loop[uv_layer].uv=(uv[0],1-uv[1]);loop[normal_layer]=reflect(n)
# Weld only the segment being rebuilt. The old shoulder caps have coincident,
# intentionally separate patches; globally merging them makes non-manifold edges.
fit_frames=[]
for side in ('l','r'):
    hand=reflect(native['bones']['hand_'+side]['position'])
    elbow=reflect(native['bones']['lowerarm_'+side]['position'])
    axis=(hand-elbow).normalized();fit_frames.append((side,hand,axis))
    selected=[x for x in bm.verts if (x.co.x<0 if side=='l' else x.co.x>0) and (x.co-hand).dot(axis)>-17]
    bmesh.ops.remove_doubles(bm,verts=selected,dist=.0001)
skin_positions=[reflect(p) for p in bare['positions']]
forearm_vertices={v for f,m in zip(bare['triangles'],bare['triangle_materials']) if m==1 for v in f}
hand_vertices={v for f,m in zip(bare['triangles'],bare['triangle_materials']) if m==2 for v in f}
seam_ids=sorted(forearm_vertices&hand_vertices)
reports=[]

for side in ('l','r'):
    wrist=reflect(native['bones']['hand_'+side]['position'])
    elbow=reflect(native['bones']['lowerarm_'+side]['position'])
    axis=(wrist-elbow).normalized()
    dorsal=reflect(frames[side]['dorsal']);u=(dorsal-axis*dorsal.dot(axis)).normalized();v=axis.cross(u)
    same_side=lambda p: p.x<0 if side=='l' else p.x>0
    seam=[skin_positions[i] for i in seam_ids if same_side(skin_positions[i])]
    seam_center=sum(seam,Vector())/len(seam)
    end_center=seam_center+axis*.65  # 6.5 mm overlap with the retained wrist skin/glove region.
    end_t=(end_center-wrist).dot(axis)
    def angle(p,center):
        q=p-center;return math.atan2(q.dot(v),q.dot(u))%(2*math.pi)
    boundary=sorted((angle(p,seam_center),(p-seam_center).dot(u),(p-seam_center).dot(v)) for p in seam)
    def periodic(samples,theta):
        angles=[s[0] for s in samples]
        return np.asarray([np.interp(theta,[angles[-1]-2*math.pi]+angles+[angles[0]+2*math.pi],
                                     [samples[-1][j]]+[s[j] for s in samples]+[samples[0][j]])
                           for j in range(1,len(samples[0]))])
    faces=[f for f in bare['triangles'] if all(same_side(skin_positions[i]) for i in f)
           and -22<sum((skin_positions[i]-wrist).dot(axis) for i in f)/3<1]
    bvh=BVHTree.FromPolygons(skin_positions,faces,all_triangles=True)
    def skin_weights(point):
        nearest,normal,fi,distance=bvh.find_nearest(point)
        f=faces[fi];a,b,c=[skin_positions[i] for i in f]
        bary=barycentric_transform(nearest,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        weights={}
        for i,factor in zip(f,bary):
            for n,w in bare['weights'][i].items():weights[n]=weights.get(n,0)+max(0,factor)*w
        return normalized(weights)
    cut_t=-13.0;plane=wrist+axis*cut_t
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                          dist=.00001,plane_co=plane,plane_no=axis,clear_outer=True,clear_inner=False)
    edges=[e for e in bm.edges if e.is_boundary and all(abs((p.co-plane).dot(axis))<.001 for p in e.verts)]
    adjacent={}
    for e in edges:
        for vi in e.verts:adjacent.setdefault(vi,[]).append(e.other_vert(vi))
    remaining=set(adjacent);loops=[]
    while remaining:
        start=next(iter(remaining));loop=[];current=start;previous=None
        while current not in loop:
            loop.append(current);remaining.discard(current)
            candidates=[x for x in adjacent[current] if x!=previous]
            if len(adjacent[current])!=2:raise RuntimeError('Non-manifold original cuff cut '+side)
            previous,current=current,candidates[0]
        loops.append(loop)
    if len(loops)!=2:raise RuntimeError('Expected the existing inner and outer sleeve layers: '+str((side,[len(x) for x in loops])))
    center=sum((x.co for loop in loops for x in loop),Vector())/sum(map(len,loops))
    loops.sort(key=lambda loop:sum((x.co-center).length for x in loop)/len(loop),reverse=True)
    for vertex in bm.verts:
        if not same_side(vertex.co):continue
        a=smooth(-17,cut_t,(vertex.co-wrist).dot(axis))
        if a<=0:continue
        old={names[n]:w for n,w in vertex[deform].items()}
        new=skin_weights(vertex.co);blend={n:old.get(n,0)*(1-a)+new.get(n,0)*a for n in old.keys()|new.keys()}
        vertex[deform].clear()
        for n,w in normalized(blend).items():vertex[deform][name_id[n]]=w

    def make_face(verts,uvs,direction):
        coords=[p.co for p in verts]
        if (coords[1]-coords[0]).cross(coords[2]-coords[0]).dot(direction)<0:
            verts=list(reversed(verts));uvs=list(reversed(uvs))
        face=bm.faces.new(verts)
        for loop,uv in zip(face.loops,uvs):loop[uv_layer].uv=uv

    def bridge(a,b,sa,sb,inward=False,rim=False):
        aa=[angle(x.co,center if sa==0 else end_center) for x in a]
        bb=[angle(x.co,end_center) for x in b]
        i=j=0;n=len(a);m=len(b)
        def vertex_uv(vert,progress,theta):return (theta/(2*math.pi),.25+progress*.22)
        while i<n or j<m:
            an=(aa[(i+1)%n]-aa[0])%(2*math.pi) if i+1<n else 2*math.pi
            bn=(bb[(j+1)%m]-bb[0])%(2*math.pi) if j+1<m else 2*math.pi
            if j==m or (i<n and an<=bn):
                tri=[a[i%n],a[(i+1)%n],b[j%m]]
                uv=[vertex_uv(tri[0],sa,aa[i%n]),vertex_uv(tri[1],sa,aa[(i+1)%n]),vertex_uv(tri[2],sb,bb[j%m])];i+=1
            else:
                tri=[a[i%n],b[(j+1)%m],b[j%m]]
                uv=[vertex_uv(tri[0],sa,aa[i%n]),vertex_uv(tri[1],sb,bb[(j+1)%m]),vertex_uv(tri[2],sb,bb[j%m])];j+=1
            if max(x[0] for x in uv)-min(x[0] for x in uv)>.5:uv=[(x+1 if x<.5 else x,y) for x,y in uv]
            mid=sum((x.co for x in tri),Vector())/3
            radial=mid-wrist-axis*(mid-wrist).dot(axis)
            make_face(tri,uv,axis if rim else (-radial if inward else radial))

    ends=[];count=96
    for layer,loop in enumerate(loops):
        loop.sort(key=lambda x:angle(x.co,center))
        samples=[(angle(x.co,center),(x.co-center).dot(u),(x.co-center).dot(v)) for x in loop]
        previous=loop;last_s=0
        for s in (.12,.26,.42,.57,.70,.81,.90,.96,1.0):
            blend=smooth(0,1,s);ring=[]
            ring_center=center.lerp(end_center,s)
            for k in range(count):
                theta=2*math.pi*k/count
                initial=periodic(samples,theta);target=periodic(boundary,theta)
                target+=np.asarray([math.cos(theta),math.sin(theta)])*(.50 if layer==0 else .30)
                radial=initial*(1-blend)+target*blend
                # Low-amplitude compression folds outside the narrow cuff band.
                radius_add=.10*math.sin(math.pi*s)**2*math.sin(5*math.pi*s)
                radial+=np.asarray([math.cos(theta),math.sin(theta)])*radius_add
                point=ring_center+u*float(radial[0])+v*float(radial[1])
                vertex=bm.verts.new(point)
                for n,w in skin_weights(point).items():vertex[deform][name_id[n]]=w
                ring.append(vertex)
            bridge(previous,ring,last_s,s,inward=layer==1)
            previous=ring;last_s=s
        ends.append(previous)
    bridge(ends[0],ends[1],1,1,rim=True)
    reports.append({'side':side,'original_cut_loops':[len(x) for x in loops],'cut_cm':cut_t,
                    'new_cuff_end_cm_from_wrist':end_t,'skin_overlap_cm':.65,'cuff_inner_clearance_cm':.30,
                    'fabric_thickness_cm':.20,'radial_samples':count})
    print('SLEEVE_CUFF_AUTHORED',side,reports[-1],flush=True)

bmesh.ops.triangulate(bm,faces=list(bm.faces))
bm.normal_update();bm.verts.ensure_lookup_table();bm.verts.index_update()
p=[unreflect(x.co) for x in bm.verts]
weights=[normalized({names[i]:w for i,w in x[deform].items()}) for x in bm.verts]
triangles=[];uv=[];normals=[]
for face in bm.faces:
    triangles.append([loop.vert.index for loop in face.loops])
    uv.append([[loop[uv_layer].uv.x,1-loop[uv_layer].uv.y] for loop in face.loops])
    row=[]
    for loop in face.loops:
        affected=any((loop.vert.co.x<0 if side=='l' else loop.vert.co.x>0) and (loop.vert.co-hand).dot(axis)>-17
                     for side,hand,axis in fit_frames)
        normal=loop.vert.normal if affected or loop[normal_layer].length<.5 else loop[normal_layer].normalized()
        row.append(unreflect(normal))
    normals.append(row)
canonical={'positions':p,'weights':weights,'triangles':triangles,'uv':uv,'normals':normals}
(ROOT/'sleeves_master.json').write_text(json.dumps(canonical,separators=(',',':')),encoding='utf-8')
bm.free();bpy.data.meshes.remove(mesh)

inverse={n:np.linalg.inv(bind(b)) for n,b in native['bones'].items()}
config=read(PROJECT/'Content/ColdSteelData/modular_outfits.json');manifest=[]
for source_path,profile in config['profiles'].items():
    name=profile['rig_profile']
    if name=='Body':continue
    target=read(SOURCES/f'{name}.json')
    side=-1 if np.mean(np.asarray(target['positions'])[:,0])<0 else 1
    single=len(target['positions'])<15000
    ids=[i for i,x in enumerate(p) if not single or x[0]*side>0];remap={v:i for i,v in enumerate(ids)}
    faces=[i for i,f in enumerate(triangles) if all(v in remap for v in f)]
    matrices={n:bind(target['bones'][n])@inverse[n] for n in {n for i in ids for n in weights[i]}}
    positions=[];linears={}
    for i in ids:
        matrix=sum(matrices[n]*w for n,w in weights[i].items())
        positions.append((matrix@np.append(p[i],1))[:3].tolist());linears[i]=np.linalg.inv(matrix[:3,:3]).T
    ns=[]
    for fi in faces:
        row=[]
        for corner,i in enumerate(triangles[fi]):
            normal=linears[i]@np.asarray(normals[fi][corner]);normal/=np.linalg.norm(normal);row.append(normal.tolist())
        ns.append(row)
    raw=(BARE/'Authored'/f'{name}.json').read_bytes()
    data={'profile':name,'source':source_path,'skeleton':target['skeleton'],
          'binding_source':profile['original_gloved_source'],'base_mesh':profile['native_bare_skin'],
          'bare_authored_sha256':hashlib.sha256(raw).hexdigest(),'positions':positions,
          'weights':[weights[i] for i in ids],'triangles':[[remap[v] for v in triangles[fi]] for fi in faces],
          'uv':[uv[fi] for fi in faces],'normals':ns,'triangle_materials':[0]*len(faces),
          'contract':'Original sweater upper sleeves; fitted V7 cuffs with 6.5 mm overlap and 2 mm existing-layer thickness; native bones; no simulation or new animation'}
    path=OUT/f'{name}.json';path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    manifest.append({'profile':name,'source':source_path,'authored':str(path),'vertices':len(ids),'triangles':len(faces)})
    print('FITTED_SLEEVES_AUTHORED',name,len(ids),len(faces),flush=True)
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(ROOT/'cuff-authoring.json').write_text(json.dumps({'cuffs':reports,'cloth_physics_added':False,'runtime_tested':False},indent=2)+'\n',encoding='utf-8')
