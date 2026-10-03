"""Two continuous hidden drapes over the retained V35 membrane display skin."""
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
V35=ROOT/'MembraneSkinV35'
OUT=ROOT/'WitchClothV36'
ROWS,COLS=39,15

def smooth(t):
    t=np.clip(t,0.,1.)
    return t*t*(3.-2.*t)

def solve():
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    from scipy.ndimage import gaussian_filter,gaussian_filter1d
    src=np.load(V35/'surface_input.npz');skin=np.load(V35/'skin_solution.npz')
    p,w=src['p'],skin['weights']
    labels=src['labels'];names=src['names'].tolist()
    eligible=(labels>0)|((labels==0)&skin['changed'])
    # Shared display seams get a common continuous mobility field. All actual
    # body/limb vertices remain fixed, including those near a cloth envelope.
    _,first,weld=np.unique(np.round(p/.001).astype(np.int32),axis=0,return_index=True,return_inverse=True)
    points=p[first];fixed=np.zeros(len(first),bool);np.logical_or.at(fixed,weld,~eligible)
    edges=np.unique(np.sort(weld[src['e']],axis=1),axis=0);edges=edges[edges[:,0]!=edges[:,1]]
    a,b=edges.T;length=np.linalg.norm(points[a]-points[b],axis=1)
    graph=coo_matrix((np.r_[length,length],(np.r_[a,b],np.r_[b,a])),shape=(len(points),len(points))).tocsr()
    touching=np.unique(edges[fixed[a]^fixed[b]])
    seeds=touching[fixed[touching]]
    distance=dijkstra(graph,directed=False,indices=seeds,min_only=True)
    alpha=smooth(distance[weld]/22.)*eligible
    alpha=np.rint(alpha*255).astype(np.uint8)
    panels=[];all_p=[];all_w=[];all_f=[];offset=0
    for panel,sign in enumerate((1,-1),1):
        ids=np.flatnonzero(eligible&(p[:,0]*sign>0))
        cloud=p[ids].copy();cloud[:,0]*=sign
        z=np.linspace(float(cloud[:,2].max()+2),float(cloud[:,2].min()-2),ROWS)
        lows=[];highs=[]
        for height in z:
            band=cloud[np.abs(cloud[:,2]-height)<10.]
            if len(band)<8:band=cloud[np.argsort(np.abs(cloud[:,2]-height))[:64]]
            lows.append(max(1.,float(np.percentile(band[:,0],.5))-3.))
            highs.append(max(lows[-1]+12.,float(np.percentile(band[:,0],99.5))+3.))
        low=gaussian_filter1d(lows,.65);high=gaussian_filter1d(highs,.65)
        u=np.linspace(0,1,COLS)
        x=low[:,None]+(high-low)[:,None]*u
        zz=np.broadcast_to(z[:,None],x.shape)
        # Fit one smooth middle sheet, not a collapsed collection of folded
        # front/back triangles. The original visible folds keep their offsets.
        tree=cKDTree(cloud[:,[0,2]])
        dist,near=tree.query(np.c_[x.ravel(),zz.ravel()],k=20)
        influence=1./np.maximum(dist,1.)**2;influence/=influence.sum(axis=1,keepdims=True)
        y=gaussian_filter((cloud[near,1]*influence).sum(axis=1).reshape(x.shape),(.9,.8))
        q=np.c_[x.ravel()*sign,y.ravel(),zz.ravel()]
        dist,near=cKDTree(p[ids]).query(q,k=8)
        influence=1./np.maximum(dist,.5)**2;influence/=influence.sum(axis=1,keepdims=True)
        qw=(w[ids[near]]*influence[:,:,None]).sum(axis=1)
        best=np.argsort(-qw,axis=1)[:,:8];packed=np.zeros_like(qw)
        np.put_along_axis(packed,best,np.take_along_axis(qw,best,axis=1),axis=1)
        packed/=packed.sum(axis=1,keepdims=True)
        faces=[]
        for row in range(ROWS-1):
            for col in range(COLS-1):
                v=row*COLS+col
                faces.extend(((v,v+COLS,v+1),(v+1,v+COLS,v+COLS+1)))
        faces=np.asarray(faces,np.int32)
        if sign<0:faces=faces[:,::-1]
        mobility=smooth((z[0]-zz-14.)/72.)*smooth((u[None,:]-.075)/.30)
        maximum=(28.*mobility).ravel()
        panels.append(dict(id=f'{panel:02d}',vertices_cm=(q*np.asarray([1,-1,1])).tolist(),max_distance_cm=maximum.tolist(),
            vertices=len(q),triangles=len(faces),fixed_vertices=int((maximum==0).sum()),connected_sheet=True))
        all_p.append(q);all_w.append(packed);all_f.append(faces+offset);offset+=len(q)
    np.savez_compressed(OUT/'cloth_source.npz',p=np.concatenate(all_p),w=np.concatenate(all_w),f=np.concatenate(all_f),alpha=alpha,names=names,offsets=src['offsets'])
    previous=json.loads((ROOT/'BodyMotionV18/Proxy/cloth_ue_manifest_v18.json').read_text())
    manifest=dict(revision='WitchClothV36',panels=panels,collision_capsules=previous['collision_capsules'],
        template='/Game/Monsters/WitchRebuilt/SK_WitchRebuilt:WitchRebuilt_LowerDrape07',
        display_source=str(V35/'M07_MembraneSkinV35.blend'),physical_vertices=offset,physical_triangles=len(np.concatenate(all_f)),
        display_blend_vertex_count=int((alpha>0).sum()),maximum_travel_cm=28.,display_transition_cm=22.,
        cloth_resume_distance_cm=1200.,cloth_suspend_distance_cm=1600.,runtime_tested=False,rendered=False)
    (OUT/'cloth_manifest_v36.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

def author():
    import bpy
    from mathutils import Matrix
    sys.path.insert(0,str(Path(__file__).parent))
    import author_original_surfaces_v08 as surfaces
    OUT.mkdir(parents=True,exist_ok=True)
    subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',str(Path(__file__).resolve()),'--solve'],check=True)
    data=np.load(OUT/'cloth_source.npz')
    bpy.ops.wm.open_mainfile(filepath=str(V35/'M07_MembraneSkinV35.blend'))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    rig.animation_data_clear();rig.data.pose_position='REST'
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    display=[bpy.data.objects['M07_OriginalBody_Display']]+[bpy.data.objects[f'M07_OriginalGill_{i:02d}_Display'] for i in range(1,7)]
    for label,obj in enumerate(display):
        mesh=obj.data;original=mesh.color_attributes.active_color
        # Retain the existing RGB identity labels, use alpha only for capture.
        rgb=np.ones((len(mesh.loops),4),np.float32)
        if original:
            for loop in mesh.loops:
                rgb[loop.index]=original.data[loop.index if original.domain=='CORNER' else loop.vertex_index].color
        for attr in list(mesh.color_attributes):mesh.color_attributes.remove(attr)
        color=mesh.color_attributes.new(name='M07_ClothMobility',type='BYTE_COLOR',domain='CORNER')
        start,end=data['offsets'][label:label+2]
        for loop in mesh.loops:
            value=rgb[loop.index];value[3]=float(data['alpha'][start+loop.vertex_index])/255.
            color.data[loop.index].color=value
        mesh.color_attributes.active_color_index=0
    material=bpy.data.materials.get('M07_GillSimulation') or bpy.data.materials.new('M07_GillSimulation')
    collection=bpy.data.collections.new('M07_ContinuousDrapesV36');bpy.context.scene.collection.children.link(collection)
    proxy=surfaces.make_mesh('M07_ContinuousDrapesV36',data['p'],data['f'],material,collection)
    names=data['names'].tolist();weights=data['w'];best=np.argsort(-weights,axis=1)[:,:8]
    surfaces.assign(proxy,names,best,np.take_along_axis(weights,best,axis=1));surfaces.bind(proxy,rig)
    surfaces.export(OUT/'SK_M07_ClothProxyV36.fbx',rig,[proxy])
    surfaces.export(OUT/'SK_M07_Display_ClothV36.fbx',rig,display)
    proxy.hide_render=True;proxy.hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M07_WitchClothV36.blend'),compress=True)
    print('M07_V36_SOURCE_EXPORTED',flush=True)

if __name__=='__main__':
    if '--solve' in sys.argv:solve()
    else:author()
