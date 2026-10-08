"""Restore the complete original oral surface into the reduced M14, offline.

The old Meshy reduction cut through tooth tips. Keep source oral topology,
reduce it conservatively with fixed borders, and stitch those borders to the
reduced body. Each LOD shares that seam and the production V15 skin/morphs.
"""
import bpy, bmesh, numpy as np
import json, sys, time, traceback, gc
from pathlib import Path
from mathutils import Matrix

P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/MonsterAI'))
import author_meshy_remesh_v3 as shared
OUT=P/'SourceAssets/AlienGeometry20261006/RemeshV4Teeth/SpiralPillarM14'
OUT.mkdir(parents=True,exist_ok=True)
OLD=P/'SourceAssets/AlienGeometry20261006/RemeshV3/SpiralPillarM14'
SOURCE=P/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15/Authoring/M14_SupportSkin_v15.blend'
START=time.time()
REPORT=dict(species='SpiralPillarM14',revision='TeethRemeshV4',complete=False,ue_imported=False,
    source=str(SOURCE),reduced_body=str(OLD/'SpiralPillarM14_RemeshV3.blend'),lods=[],tested=False,
    animations_reauthored=False,repair='Restore full tooth shells, roots and oral surface; stitched fixed borders')

def log(s):print('M14_TEETH_V4 '+str(s),flush=True)
def record():
    REPORT['seconds']=round(time.time()-START,2)
    (OUT/'authoring.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def arrays(obj):
    mesh=obj.data;mesh.calc_loop_triangles()
    p=shared.coords(obj);f=shared.triangles(obj)
    loops=np.empty_like(f);mesh.loop_triangles.foreach_get('loops',loops.ravel())
    uv=np.empty((len(mesh.loops),2),np.float32);mesh.uv_layers.active.data.foreach_get('uv',uv.ravel())
    pi=np.empty(len(f),np.int32);mesh.loop_triangles.foreach_get('polygon_index',pi)
    mi=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('material_index',mi)
    return p,f,uv[loops],mi[pi]

def make(name,p,f,uv,mats,mi):
    ids,inv=np.unique(f,return_inverse=True)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(p[ids].tolist(),[],inv.reshape(-1,3).tolist());mesh.update()
    mesh.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uv,np.float32).ravel())
    for mat in mats:mesh.materials.append(mat)
    mesh.polygons.foreach_set('material_index',np.asarray(mi,np.int32))
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000008)
    bm.to_mesh(mesh);bm.free();mesh.update()
    return obj

def boundary_rings(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
    adjacency={}
    for e in bm.edges:
        if e.is_boundary:
            a,b=[v.index for v in e.verts]
            adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    rings=[];unseen=set(adjacency)
    while unseen:
        stack=[unseen.pop()];component=[]
        while stack:
            v=stack.pop();component.append(v)
            for other in adjacency[v]:
                if other in unseen:unseen.remove(other);stack.append(other)
        if any(len(adjacency[v])!=2 for v in component):continue
        start=min(component);order=[start];prev=None;current=start
        while True:
            nxt=next(x for x in adjacency[current] if x!=prev)
            if nxt==start:break
            order.append(nxt);prev,current=current,nxt
        rings.append(np.array(order,dtype=np.int32))
    bm.free()
    return rings

def patch_mask(p,f,scale,bottom,radius):
    c=p[f].mean(1);x=c[:,0]/scale;h=c[:,2]/scale+bottom;d=-c[:,1]/scale
    r=np.sqrt((x/.17)**2+((h+.455)/.19)**2)
    return (r<radius)&(d>.10)&(h<-.18)

def freeze_border_reduce(src,name,ratio):
    obj=shared.duplicate(src,name)
    if ratio>=.999:return obj
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
    border={v.index for e in bm.edges if e.is_boundary for v in e.verts};bm.free()
    group=obj.vertex_groups.new(name='ReduceInteriorOnly')
    interior=[v.index for v in obj.data.vertices if v.index not in border]
    group.add(interior,1.,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('FixedBorderReduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    # Blender's collapse implementation excludes edges touching weight-zero
    # vertices, so every boundary remains identical across all four LODs.
    mod.vertex_group=group.name;mod.vertex_group_factor=1.
    bpy.ops.object.modifier_apply(modifier=mod.name);obj.vertex_groups.clear()
    return obj

def zipper(a,b,p):
    # Orient the two geometric cycles alike, align a nearby starting pair,
    # then find a monotone triangulation minimizing connecting edge lengths.
    distance=np.linalg.norm(p[a][:,None,:]-p[b][None,:,:],axis=2)
    ia,ib=np.unravel_index(distance.argmin(),distance.shape)
    a=np.roll(a,-ia);b=np.roll(b,-ib)
    tangent_a=p[a[1]]-p[a[-1]];tangent_b=p[b[1]]-p[b[-1]]
    if np.dot(tangent_a,tangent_b)<0:b=np.r_[b[0],b[:0:-1]]
    aa=np.r_[a,a[0]];bb=np.r_[b,b[0]];n=len(a);m=len(b)
    costs=np.linalg.norm(p[aa][:,None,:]-p[bb][None,:,:],axis=2)**2
    dp=np.full((n+1,m+1),np.inf);step=np.zeros((n+1,m+1),np.uint8);dp[0,0]=0
    for i in range(n+1):
        for j in range(m+1):
            if not i and not j:continue
            left=dp[i-1,j] if i else np.inf;below=dp[i,j-1] if j else np.inf
            if left<=below:dp[i,j]=left+costs[i,j];step[i,j]=1
            else:dp[i,j]=below+costs[i,j];step[i,j]=2
    result=[];i=n;j=m
    while i or j:
        if step[i,j]==1:result.append((aa[i-1],aa[i],bb[j]));i-=1
        else:result.append((aa[i],bb[j],bb[j-1]));j-=1
    return result

def stitch(body,oral,source,projection,source_uv,mats):
    bp,bf,bu,bm=arrays(body);op,of,ou,om=arrays(oral)
    p=np.concatenate((bp,op));offset=len(bp)
    oldrings=boundary_rings(oral);bodyrings=boundary_rings(body);used=set();bridges=[];seams=[]
    for old in sorted(oldrings,key=len,reverse=True):
        center=op[old].mean(0)
        choices=[(float(np.linalg.norm(bp[r].mean(0)-center)),i,r) for i,r in enumerate(bodyrings) if i not in used]
        distance,i,new=min(choices,key=lambda x:x[0])
        if distance>.08:raise RuntimeError('No body border for oral patch '+str((len(old),distance,center)))
        used.add(i);bridges.extend(zipper(new,old+offset,p))
        seams.append(dict(source_border=len(old),body_border=len(new),center_distance_m=distance))
    bridge=np.asarray(bridges,np.int32)
    # Project collar corners separately. Clamping every corner to the tiny
    # source triangle under the centroid produces degenerate UVs and visible
    # normal-map facets; only cross-island triangles use plane extrapolation.
    idx,bary=projection.at(p[bridge].mean(1));src_tri=projection.p[projection.f[idx]]
    vi,vw=projection.at(p[bridge].reshape(-1,3))
    direct=np.einsum('ij,ijk->ik',vw,source_uv[vi]).reshape(-1,3,2)
    atlas_seam=np.max(np.linalg.norm(direct-np.roll(direct,1,axis=1),axis=2),axis=1)>.10
    uvs=[]
    for corner in range(3):
        a=src_tri[:,1]-src_tri[:,0];b=src_tri[:,2]-src_tri[:,0];q=p[bridge[:,corner]]-src_tri[:,0]
        aa=(a*a).sum(1);ab=(a*b).sum(1);bb=(b*b).sum(1);qa=(q*a).sum(1);qb=(q*b).sum(1)
        den=np.maximum(aa*bb-ab*ab,1e-24);u=(bb*qa-ab*qb)/den;v=(aa*qb-ab*qa)/den
        weights=np.stack([1-u-v,u,v],axis=1)
        uvs.append(np.einsum('ij,ijk->ik',weights,source_uv[idx]))
    collar_uv=direct;collar_uv[atlas_seam]=np.stack(uvs,axis=1)[atlas_seam]
    f=np.concatenate((bf,of+offset,bridge));uv=np.concatenate((bu,ou,collar_uv))
    mi=np.concatenate((bm,om,np.full(len(bridge),4,np.int32)))
    result=make('M14_TeethRemeshV4',p,f,uv,mats,mi)
    bmsh=bmesh.new();bmsh.from_mesh(result.data);bmesh.ops.recalc_face_normals(bmsh,faces=list(bmsh.faces));bmsh.to_mesh(result.data);bmsh.free()
    result.data.polygons.foreach_set('use_smooth',np.ones(len(result.data.polygons),bool))
    return result,seams

def run():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    source=bpy.data.objects['M14_SoftDeathMesh'];rig=bpy.data.objects['M14_Rig']
    rig.animation_data_clear();rig.data.pose_position='REST'
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    if source.data.shape_keys:
        source.data.shape_keys.animation_data_clear()
        for key in source.data.shape_keys.key_blocks:key.value=0
    bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    with bpy.data.libraries.load(str(OLD/'SpiralPillarM14_RemeshV3.blend'),link=False) as (a,b):b.objects=['M14_RemeshV3']
    low=b.objects[0];bpy.context.scene.collection.objects.link(low)
    # The existing object's parent carries identity; bake its world points into
    # the new unparented construction meshes below.
    sp,sf,su,sm=arrays(source);lp,lf,lu,lm=arrays(low)
    scale=float(rig['source_scale'])
    _,_,raw,_,_=shared.glb(P/'SourceAssets/SpiralPillarM14Meshy20261004/Original/Meshy_AI_Veiled_Maw_M_14_1004025810_texture.glb')
    bottom=float(raw[:,1].min());del raw
    source_mask=patch_mask(sp,sf,scale,bottom,1.04);low_mask=patch_mask(lp,lf,scale,bottom,1.08)
    mouth=source.data.materials[1].copy();mouth.name='Kept_M14_Mouth'
    mats=list(low.data.materials)+[mouth]
    oral=make('OriginalOralPatch',sp,sf[source_mask],su[source_mask],mats,np.full(source_mask.sum(),4,np.int32))
    body=make('ReducedBodyWithoutDamagedMouth',lp,lf[~low_mask],lu[~low_mask],mats,lm[~low_mask])
    projection=shared.Projection(sp,sf)
    log(dict(original_oral_faces=int(source_mask.sum()),removed_damaged_faces=int(low_mask.sum()),oral_borders=[len(x) for x in boundary_rings(oral)]))
    REPORT.update(original_triangles=len(sf),previous_triangles=len(lf),removed_damaged_triangles=int(low_mask.sum()),source_oral_triangles=int(source_mask.sum()),
        materials={m.name:dict(source_material_name='M14_'+m.name.rsplit('_',1)[-1],new_texture=i<4) for i,m in enumerate(mats)},
        textures=json.loads((OLD/'authoring.json').read_text(encoding='utf8'))['textures'],
        retained_design=['V15 49 bone production rig','nine existing death shape keys','V21 bite and slam animations unchanged','complete tooth shells and oral cavity'])
    record();result=None
    for level,(body_ratio,oral_target) in enumerate(((1.,60000),(.38,28000),(.14,14000),(.05,7000))):
        log('build LOD '+str(level))
        b=freeze_border_reduce(body,'Body_LOD'+str(level),body_ratio)
        o=freeze_border_reduce(oral,'Oral_LOD'+str(level),oral_target/len(oral.data.polygons))
        obj,seams=stitch(b,o,source,projection,su,mats)
        shared.transfer(source,obj,rig,projection=projection)
        file=OUT/('SpiralPillarM14_LOD'+str(level)+'.fbx');shared.export([obj],rig,file)
        REPORT['lods'].append(dict(level=level,file=str(file),triangles=len(shared.triangles(obj)),vertices=len(obj.data.vertices),
            mouth_triangles=len(o.data.polygons),seams=seams,morphs=[k.name for k in obj.data.shape_keys.key_blocks if k.name!='Basis']))
        record()
        for part in (b,o):bpy.data.objects.remove(part,do_unlink=True)
        if level==0:result=obj;result.hide_set(True);result.hide_render=True
        else:bpy.data.objects.remove(obj,do_unlink=True)
    for obj in list(bpy.data.objects):
        if obj not in (result,rig):bpy.data.objects.remove(obj,do_unlink=True)
    result.hide_set(False);result.hide_render=False;result.name='M14_TeethRemeshV4'
    rig.data.pose_position='POSE'
    for im in bpy.data.images:
        if im.users and not im.packed_file:im.pack()
    bpy.context.preferences.filepaths.save_version=0
    blend=OUT/'SpiralPillarM14_TeethRemeshV4.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    REPORT.update(complete=True,blend=str(blend),bones=[b.name for b in rig.data.bones])
    record();log('SAVED '+json.dumps(REPORT['lods']))

if __name__=='__main__':
    try:run()
    except Exception:
        REPORT['error']=traceback.format_exc();record();raise
