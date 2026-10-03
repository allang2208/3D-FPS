"""Repair hidden gill proxy islands; retain every visible vertex and weight."""
import copy
import heapq
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import prepare_gill_contacts_v18 as old

ROOT=old.ROOT
OUT=ROOT/'MembraneStabilityV31/Proxy'


def topology(points,faces):
    adjacent=[{} for _ in points]
    for a,b,c in faces:
        for i,j in ((a,b),(b,c),(c,a)):
            d=float(np.linalg.norm(points[i]-points[j]))
            adjacent[i][j]=adjacent[j][i]=d
    remaining=set(range(len(points)));components=[]
    while remaining:
        stack=[remaining.pop()];part=[]
        while stack:
            i=stack.pop();part.append(i)
            for j in adjacent[i]:
                if j in remaining:remaining.remove(j);stack.append(j)
        components.append(part)
    return adjacent,components


def author():
    OUT.mkdir(parents=True,exist_ok=True)
    original=ROOT/'BodyMotionV18/Proxy/M07_Original_GillContacts_V18.blend'
    cloth=json.loads((ROOT/'BodyMotionV18/Proxy/cloth_ue_manifest_v18.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(original))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    rig.animation_data_clear();rig.data.pose_position='REST'
    scene=bpy.context.scene;scene.frame_set(0)
    collection=bpy.data.collections.new('M07_StableMembraneProxyV31')
    scene.collection.children.link(collection)
    material=bpy.data.materials['M07_GillSimulation']
    proxies=[];panels=[];details=[]
    for index in range(1,7):
        source=bpy.data.objects[f'M07_OriginalGill_{index:02d}_SimulationV18']
        points=np.asarray([v.co[:] for v in source.data.vertices],float)
        faces=np.asarray([list(f.vertices) for f in source.data.polygons],int)
        edge=np.stack((points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,1]],points[faces[:,0]]-points[faces[:,2]]),axis=1)
        lengths=np.linalg.norm(edge,axis=2)
        quality=2*np.sqrt(3)*np.linalg.norm(np.cross(edge[:,0],-edge[:,2]),axis=1)/np.maximum((lengths*lengths).sum(axis=1),1.e-12)
        keep=(quality>=.06)&(lengths.max(axis=1)<=35.)
        used,remapped=np.unique(faces[keep].ravel(),return_inverse=True)
        p,f=points[used],remapped.reshape(-1,3)
        proxy=old.surface.make_mesh(f'M07_OriginalGill_{index:02d}_SimulationV31',p,f,material,collection)
        # Copy surviving proxy skin rows exactly; no display reweight or bind edit.
        names={g.index:g.name for g in source.vertex_groups if g.name in rig.data.bones}
        groups={n:proxy.vertex_groups.new(name=n) for n in names.values()}
        for new_id,source_id in enumerate(used):
            for group in source.data.vertices[int(source_id)].groups:
                if group.group in names:
                    groups[names[group.group]].add([new_id],group.weight,'REPLACE')
        old.surface.bind(proxy,rig)
        panel=copy.deepcopy(cloth['panels'][index-1])
        initial=np.asarray(panel['max_distance_cm'])[used]
        maximum=initial*(12.,9.,7.)[(index-1)%3]/max(float(initial.max()),1.e-6)
        adjacent,components=topology(p,f)
        skin_islands=[]
        for component in components:
            if not np.any(initial[component]<1.e-5):
                maximum[component]=0.
                skin_islands.append(component)
        # A geodesic ramp from the real pins limits the travel gradient; an
        # unanchored fragment follows its existing bone skin instead of cloth.
        distance=np.full(len(p),np.inf)
        pending=[]
        for i in np.flatnonzero(maximum<1.e-5):
            distance[i]=0.;heapq.heappush(pending,(0.,int(i)))
        while pending:
            d,i=heapq.heappop(pending)
            if d>distance[i]:continue
            for j,length in adjacent[i].items():
                candidate=d+length
                if candidate<distance[j]:
                    distance[j]=candidate;heapq.heappush(pending,(candidate,j))
        maximum=np.minimum(maximum,distance*.32)
        # Relax abrupt changes in the original mask without moving any point.
        for _ in range(4):
            previous=maximum.copy()
            for i,neighbors in enumerate(adjacent):
                if not neighbors or previous[i]<=0.:continue
                average=sum(previous[j] for j in neighbors)/len(neighbors)
                maximum[i]=min(previous[i],.7*previous[i]+.3*average)
        limit=(12.,9.,7.)[(index-1)%3]
        pin=proxy.vertex_groups.new(name='M07_Pin')
        for i,value in enumerate(maximum):
            pin.add([i],float(1.-value/limit),'REPLACE')
        proxy['panel_id']=index
        proxy['display_export_excluded']=True
        proxy.hide_render=True
        panel.update(vertices_cm=np.c_[p[:,0],-p[:,1],p[:,2]].tolist(),
            max_distance_cm=maximum.tolist(),pin_weights=(1-maximum/limit).tolist(),
            vertex_count=len(p),triangle_count=len(f),
            attachment_surface_distance_cm=np.asarray(panel['attachment_surface_distance_cm'])[used].tolist(),
            proxy_revision='MembraneStabilityV31: stable faces, unanchored fragment skinning, smooth bounded travel')
        panels.append(panel);proxies.append(proxy)
        details.append(dict(panel=index,old_vertices=len(points),old_triangles=len(faces),
            vertices=len(p),triangles=len(f),removed_hidden_triangles=int((~keep).sum()),
            skin_only_unanchored_islands=len(skin_islands),skin_only_unanchored_vertices=sum(map(len,skin_islands)),
            fixed_vertices=int((maximum<1.e-5).sum()),max_distance_cm=float(maximum.max()),
            remaining_unanchored_components=sum(not np.any(maximum[c]<1.e-5) for c in components),
            triangle_quality_min=float(quality[keep].min()),longest_edge_cm=float(lengths[keep].max())))
        print('M07_V31_STABLE_PROXY '+json.dumps(details[-1]),flush=True)
    cloth.update(panels=panels,revision='MembraneStabilityV31',
        method='Original-surface hidden proxy, skin-only unsupported fragments, local smooth travel and original collision budget',
        proxy_topology_modified=True,geometry_modified=False,tested=False,runtime_tested=False,rendered=False)
    fbx=OUT/'SK_M07_ClothBuildSource_MembraneV31.fbx'
    old.surface.export(fbx,rig,proxies)
    cloth_file=OUT/'cloth_ue_manifest_v31.json'
    old.write(cloth_file,cloth)
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj not in proxies:
            obj.hide_set(True)
    blend=OUT/'M07_MembraneStability_V31.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    old.write(OUT/'proxy_manifest_v31.json',dict(revision='MembraneStabilityV31',source=str(blend),
        original_source=str(original),simulation_fbx=str(fbx),cloth_manifest=str(cloth_file),panels=details,
        simulation_vertices=sum(d['vertices'] for d in details),simulation_triangles=sum(d['triangles'] for d in details),
        display_geometry_modified=False,display_weights_modified=False,uv_modified=False,reference_pose_modified=False,
        source_saved=True,fbx_exported=True,ue_imported=False,ue_saved=False,requested_source_inspection=True,
        runtime_tested=False,rendered=False,user_review_pending=True))
    print('M07_V31_PROXY_SOURCE_SAVED '+str(OUT),flush=True)


if __name__=='__main__':author()
