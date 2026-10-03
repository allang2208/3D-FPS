"""Local gill repair on the saved V08 master; original rig/actions retained."""
import json
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OLD = ROOT/'RecoveryOriginalV08'
OUT = ROOT/'RecoveryOriginalV09'
sys.path.insert(0, str(Path(__file__).parent))
import author_original_surfaces_v08 as support

def mesh_arrays(obj):
    p = np.empty((len(obj.data.vertices),3),np.float32)
    obj.data.vertices.foreach_get('co',p.ravel())
    f = np.asarray([list(poly.vertices) for poly in obj.data.polygons],np.int32)
    return p,f

def leaf_weight_and_normals(obj, high, ids, skin, names):
    hp,hf = mesh_arrays(high)
    tree = BVHTree.FromPolygons(hp.tolist(), hf.tolist(), all_triangles=True)
    target = np.asarray([v.co[:] for v in obj.data.vertices])
    faces = np.empty(len(target), np.int32)
    bary = np.empty((len(target),3),np.float32)
    for row, point in enumerate(target):
        hit,_,face,_ = tree.find_nearest(Vector(point))
        if face is None: raise RuntimeError('Original gill surface cannot supply local weights.')
        a,b,c = hp[hf[face]]
        ab,ac,q = b-a,c-a,np.asarray(hit)-a
        aa,bb,cc = float(ab@ab),float(ab@ac),float(ac@ac)
        den = aa*cc-bb*bb
        if abs(den)<1.e-12:
            w = np.asarray([1.,0.,0.])
        else:
            v=(cc*float(q@ab)-bb*float(q@ac))/den
            z=(aa*float(q@ac)-bb*float(q@ab))/den
            w=np.maximum([1-v-z,v,z],0.); w/=max(float(w.sum()),1.e-10)
        faces[row],bary[row] = face,w
    sources = ids[hf[faces]]
    field = np.zeros((len(target),len(names)),np.float32)
    rows = np.broadcast_to(np.arange(len(target))[:,None], (len(target),8))
    for corner in range(3):
        np.add.at(field,(rows.ravel(),skin['bone_indices'][sources[:,corner]].ravel()),
            (skin['bone_weights'][sources[:,corner]]*bary[:,corner,None]).ravel())
    top=np.argpartition(field,-8,axis=1)[:,-8:]
    values=np.take_along_axis(field,top,axis=1)
    order=np.argsort(-values,axis=1)
    top=np.take_along_axis(top,order,axis=1)
    values=np.take_along_axis(values,order,axis=1)
    values/=np.maximum(values.sum(axis=1,keepdims=True),1.e-10)
    support.assign(obj,names,top,values)
    original = np.load(ROOT/'Authoring/source_mesh.npz')['normals']
    n = original[sources]
    n = np.stack([n[:,:,0],-n[:,:,2],n[:,:,1]],axis=-1)
    normals = (n*bary[:,:,None]).sum(axis=1)
    normals /= np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-10)
    obj.data.normals_split_custom_set_from_vertices(normals.tolist())

def refine_leaf(obj, high):
    # Split only long, thin reduced faces. Existing points, silhouette and UVs
    # stay; new midpoint positions can follow the same original high surface.
    for modifier in list(obj.modifiers):
        if modifier.type=='SURFACE_DEFORM': obj.modifiers.remove(modifier)
    before=len(obj.data.polygons)
    bm=bmesh.new(); bm.from_mesh(obj.data)
    for _ in range(2):
        selected=set()
        for face in bm.faces:
            longest=max(face.edges,key=lambda e:e.calc_length())
            length=longest.calc_length()
            height=2*face.calc_area()/max(length,1.e-10)
            if length>6.0 and height<1.0: selected.add(longest)
        if not selected: break
        bmesh.ops.subdivide_edges(bm,edges=list(selected),cuts=1,use_grid_fill=False)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    return {'triangles_before':before,'triangles_after':len(obj.data.polygons),
        'policy':'Local subdivision of reduced triangles longer than 6 cm with height below 1 cm; existing UVs and points retained'}

def repair_proxy(proxy, high, ids, skin, names, old_panel):
    for modifier in list(proxy.modifiers):
        if modifier.type=='CLOTH': proxy.modifiers.remove(modifier)
    bm=bmesh.new(); bm.from_mesh(proxy.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    removed=[]
    for face in bm.faces:
        # This proxy was extracted from the back-facing original shell. After
        # collapse/midpoint pairing, folded side faces must not cancel its
        # interpolated normals or enter a nearly singular cloth prism.
        if abs(face.normal.y)<.15 or face.calc_area()<.002:
            removed.append(face)
        elif face.normal.y<0:
            face.normal_flip()
    if removed: bmesh.ops.delete(bm,geom=removed,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose: bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(proxy.data); bm.free(); proxy.data.update()
    if not len(proxy.data.polygons): raise RuntimeError('Original gill proxy lost all supported faces.')
    hp,_=mesh_arrays(high)
    kd=KDTree(len(hp))
    for i,p in enumerate(hp): kd.insert(Vector(p),i)
    kd.balance()
    nearest=np.asarray([ids[kd.find(v.co)[1]] for v in proxy.data.vertices],np.int32)
    support.assign(proxy,names,skin['bone_indices'][nearest],skin['bone_weights'][nearest])
    positions=np.asarray([v.co[:] for v in proxy.data.vertices])
    prior=np.asarray(old_panel['vertices_cm']); prior[:,1]*=-1
    old_tree=KDTree(len(prior))
    for i,p in enumerate(prior): old_tree.insert(Vector(p),i)
    old_tree.balance()
    index=np.asarray([old_tree.find(v.co)[1] for v in proxy.data.vertices],np.int32)
    maximum=np.asarray(old_panel['max_distance_cm'])[index]
    pin=np.asarray(old_panel['pin_weights'])[index]
    fold=skin['fold_source_distance_cm'][nearest,int(old_panel['id'])]
    free=np.clip((fold-2.)/12.,0,1); free=free*free*(3-2*free)
    maximum=maximum*free; pin=np.maximum(pin,1-free)
    group=proxy.vertex_groups.new(name='M07_Pin')
    for i,value in enumerate(pin):
        if value>0: group.add([i],float(value),'REPLACE')
    cloth=proxy.modifiers.new('M07_ClothAuthoring_Disabled','CLOTH')
    cloth.settings.vertex_group_mass=group.name
    cloth.settings.mass=.22; cloth.settings.quality=6
    cloth.settings.air_damping=3; cloth.settings.tension_stiffness=18
    cloth.settings.compression_stiffness=18; cloth.settings.shear_stiffness=12
    cloth.settings.bending_stiffness=.65
    cloth.collision_settings.use_collision=True
    cloth.collision_settings.distance_min=1.
    cloth.collision_settings.use_self_collision=True
    cloth.collision_settings.self_distance_min=.8
    cloth.show_viewport=cloth.show_render=False
    panel=dict(old_panel)
    panel.update({'vertices_cm':np.c_[positions[:,0],-positions[:,1],positions[:,2]].tolist(),
        'max_distance_cm':maximum.tolist(),'pin_weights':pin.tolist(),
        'vertex_count':len(positions),'triangle_count':len(proxy.data.polygons),
        'source_original_vertices':nearest.tolist(),'folded_proxy_faces_removed':len(removed),
        'proxy_orientation':'One original back-facing shell; degenerate/folded side faces excluded from hidden simulation only'})
    return panel

def author():
    OUT.mkdir(parents=True,exist_ok=True)
    skin=np.load(OUT/'gill_skin_weights_v09.npz')
    weights=json.loads((OUT/'gill_skin_weights_v09.json').read_text(encoding='utf-8'))
    names=weights['bone_names']
    old_manifest=json.loads((OLD/'cloth_ue_manifest_original_v08.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'M07_Original_Skinned_Master_V08.blend'))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    rig.animation_data_clear(); rig.data.pose_position='REST'
    for pose in rig.pose.bones: pose.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    display=[bpy.data.objects['M07_OriginalBody_Display']]
    proxies=[]; panels=[]; refinements=[]
    for label in range(1,7):
        high=bpy.data.objects[f'M07_OriginalGill_{label:02d}_High']
        ids=np.asarray([v.value for v in high.data.attributes['source_vertex_id'].data],np.int32)
        support.assign(high,names,skin['bone_indices'][ids],skin['bone_weights'][ids])
        game=bpy.data.objects[f'M07_OriginalGill_{label:02d}_Display']
        refinements.append({'panel':label,**refine_leaf(game,high)})
        leaf_weight_and_normals(game,high,ids,skin,names)
        proxy=bpy.data.objects[f'M07_OriginalGill_{label:02d}_Simulation']
        panels.append(repair_proxy(proxy,high,ids,skin,names,old_manifest['panels'][label-1]))
        game['gill_repair_revision']='OriginalV09 common-fold weights and smooth cloth blending'
        display.append(game); proxies.append(proxy)
        print('M07_V09_GILL_AUTHORED '+str(label),flush=True)
    # Isolated leg-overlay spill can also touch a body-labelled membrane edge.
    # Restore those source rows in the high master. Actual limbs remain V08.
    body_high=bpy.data.objects['M07_OriginalBody_High']
    ids=np.asarray([v.value for v in body_high.data.attributes['source_vertex_id'].data],np.int32)
    spill=skin['leg_overlay_spill_rows'][ids]
    for local in np.flatnonzero(spill):
        for group in body_high.vertex_groups: group.remove([int(local)])
        source_id=ids[local]
        for index,value in zip(skin['bone_indices'][source_id],skin['bone_weights'][source_id]):
            if value>0: body_high.vertex_groups[names[int(index)]].add([int(local)],float(value),'REPLACE')
    body=display[0]
    corrected_body=0
    if 'source_vertex_id' in body.data.attributes:
        body_ids=np.asarray([v.value for v in body.data.attributes['source_vertex_id'].data],np.int32)
        for local in np.flatnonzero(skin['leg_overlay_spill_rows'][body_ids]):
            for group in body.vertex_groups: group.remove([int(local)])
            source_id=body_ids[local]
            for index,value in zip(skin['bone_indices'][source_id],skin['bone_weights'][source_id]):
                if value>0: body.vertex_groups[names[int(index)]].add([int(local)],float(value),'REPLACE')
            corrected_body+=1
    manifest=dict(old_manifest); manifest['panels']=panels
    manifest['shared_fold_pinning']=True
    manifest['method']='V08 reference with corrected common-fold skin fields, locally oriented original hidden proxies and continuous cloth capture transitions'
    (OUT/'cloth_ue_manifest_original_v09.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    support.export(OUT/'SK_M07_Display_OriginalV09.fbx',rig,display)
    support.export(OUT/'SK_M07_ClothBuildSource_OriginalV09.fbx',rig,[*display,*proxies])
    rig.data.pose_position='POSE'
    idle=bpy.data.actions.get('A_M07_Idle')
    if idle:
        rig.animation_data_create(); rig.animation_data.action=idle
        if idle.slots: rig.animation_data.action_slot=idle.slots[0]
    bpy.context.scene.frame_set(0)
    destination=OUT/'M07_Original_Skinned_Master_V09.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
    report={'revision':'OriginalV09','saved_source':str(destination),'source_master':str(OLD/'M07_Original_Skinned_Master_V08.blend'),
        'scope':'Original gill shared-fold weights, local thin-triangle refinement, hidden proxy orientation, membrane-edge overlay spill',
        'bone_count':len(rig.data.bones),'reference_skeleton':'SK_M07_ReferenceOriginalV08','animations_reauthored':False,
        'original_gill_geometry_reconstructed':False,'original_uv_retained':True,'body_geometry_changed':False,
        'body_display_overlay_spill_vertices_restored':corrected_body,'gill_weights':str(OUT/'gill_skin_weights_v09.json'),
        'gill_refinements':refinements,'proxy_panels':[{k:p[k] for k in ['id','vertex_count','triangle_count','folded_proxy_faces_removed']} for p in panels],
        'display_triangles':sum(len(o.data.polygons) for o in display),'simulation_played':False,'tested':False,'rendered':False}
    (OUT/'gill_delivery_v09.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M07_V09_LOCAL_GILL_MASTER_AND_EXPORTS_SAVED',flush=True)

if __name__=='__main__': author()
