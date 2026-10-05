"""M08 V02: localized dorsal surface fairing; no render or acceptance tests."""
import bpy,bmesh,math,json,time,heapq
from pathlib import Path
import numpy as np

PREVIOUS=Path(r"D:\FPS3D\FPSGAME\SourceAssets\Monsters\LurkerM08\BackRebuildV01_20261004")
OUT=Path(r"D:\FPS3D\FPSGAME\SourceAssets\Monsters\LurkerM08\BackRebuildV02_20261004")
OUT.mkdir(parents=True,exist_ok=True)
START=time.time()
PARAMS={
    "source_blend":str(PREVIOUS/"M08_BackRebuilt_V01.blend"),
    "transition_geodesic_radius":0.038,
    "local_max_edge_length":0.008,
    "subdivide_rounds":3,
    "fairing_iterations":120,
    "taubin_lambda":0.45,
    "taubin_mu":-0.46,
    "aperture_upper_narrowing":0.10,
    "aperture_vertical_soft_variation":0.0045,
    "aperture_center":[-0.00055,0.205],
    "safety_region":{"abs_x_max":0.27,"y_min":-0.73,"y_max":0.89,"z_min":0.052},
    "source_scale_preserved":True,
}
def log(s):print("M08_V02 "+s,flush=True)
def smoothstep(x):
    x=max(0.,min(1.,x));return x*x*(3.-2.*x)
def eligible(v):
    x,y,z=v.co
    return abs(x)<.27 and -.73<y<.89 and z>.052
bpy.ops.wm.open_mainfile(filepath=str(PREVIOUS/"M08_BackRebuilt_V01.blend"))
obj=bpy.data.objects["M08_BackRebuilt_V01"]
source=bpy.data.objects["M08_Original_Reference"]
obj.name="M08_BackRebuilt_V02"
obj["revision"]="V02 local organic aperture and membrane-edge fairing"
obj["status"]="Saved authoring candidate; not user-tested"
obj.hide_viewport=False;obj.hide_set(False)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True);bpy.context.view_layer.objects.active=obj
log("Building local membrane/rim selection")
bm=bmesh.new();bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table();bm.verts.index_update()
seeds={v for f in bm.faces if f.material_index==1 for v in f.verts}
# Drop only tiny detached cutting fragments in the authored back region.
visited=set();remove_verts=[];fragment_count=0
for seed in list(seeds):
    if seed in visited:continue
    component=[];stack=[seed];visited.add(seed)
    while stack:
        v=stack.pop();component.append(v)
        for e in v.link_edges:
            n=e.other_vert(v)
            if n not in visited:visited.add(n);stack.append(n)
    if len(component)>600 or not all(eligible(v) for v in component):continue
    bounds=[max(v.co[i] for v in component)-min(v.co[i] for v in component) for i in range(3)]
    if max(bounds)<.035:
        fragment_count+=1;remove_verts.extend(component)
if remove_verts:bmesh.ops.delete(bm,geom=remove_verts,context='VERTS')
bm.verts.ensure_lookup_table();bm.verts.index_update()
seeds={v for f in bm.faces if f.material_index==1 for v in f.verts if eligible(v)}
radius=PARAMS["transition_geodesic_radius"]
dist=np.full(len(bm.verts),np.inf,dtype=np.float64)
queue=[]
for v in seeds:dist[v.index]=0.;heapq.heappush(queue,(0.,v.index))
while queue:
    d,i=heapq.heappop(queue)
    if d>dist[i] or d>radius:continue
    v=bm.verts[i]
    for e in v.link_edges:
        n=e.other_vert(v)
        if not eligible(n):continue
        nd=d+e.calc_length()
        if nd<radius and nd<dist[n.index]:
            dist[n.index]=nd;heapq.heappush(queue,(nd,n.index))
layer=bm.verts.layers.float.new("M08_V02_LocalFairingWeight")
for v in bm.verts:
    if np.isfinite(dist[v.index]):
        w=1.-smoothstep(dist[v.index]/radius)
        w*=smoothstep((v.co.z-.052)/.035)
        v[layer]=w
    else:v[layer]=0.
log("Adding local surface resolution")
for i in range(PARAMS["subdivide_rounds"]):
    edges=[e for e in bm.edges if min(v[layer] for v in e.verts)>.025 and e.calc_length()>.008]
    if not edges:break
    bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True,smooth=0.)
bm.verts.ensure_lookup_table();bm.verts.index_update()
weights=np.asarray([v[layer] for v in bm.verts],dtype=np.float64)
pairs=np.asarray([(e.verts[0].index,e.verts[1].index) for e in bm.edges
                  if weights[e.verts[0].index]>.00001 or weights[e.verts[1].index]>.00001],dtype=np.int32)
ids=np.unique(pairs.ravel())
mapping=np.full(len(bm.verts),-1,dtype=np.int32);mapping[ids]=np.arange(len(ids))
pairs=mapping[pairs]
coords=np.asarray([tuple(bm.verts[int(i)].co) for i in ids],dtype=np.float64)
original=coords.copy();w=weights[ids]
# Restrained organic shaping, smoothly attached to the retained body.
cx,cz=PARAMS["aperture_center"]
theta=np.arctan2((coords[:,2]-cz)/.121,(coords[:,0]-cx)/.105)
coords[:,0]+=w*(-.10*np.sin(theta)+.018*np.cos(4.*theta))*(coords[:,0]-cx)
coords[:,2]+=w*.0045*np.cos(2.*theta)
# Volume-preserving local diffusion: neighboring anchors outside the zone do not move.
a,b=pairs[:,0],pairs[:,1]
length=np.linalg.norm(original[a]-original[b],axis=1)
ew=1./np.maximum(length,.001)
src=np.concatenate([a,b]);dst=np.concatenate([b,a]);ew=np.concatenate([ew,ew])
den=np.bincount(src,weights=ew,minlength=len(ids))
def diffuse(factor):
    total=np.column_stack([np.bincount(src,weights=coords[dst,c]*ew,minlength=len(ids)) for c in range(3)])
    mean=total/np.maximum(den[:,None],1e-12)
    coords[:]+=factor*w[:,None]*(mean-coords)
log("Fairing membrane transition strip")
for i in range(PARAMS["fairing_iterations"]):
    diffuse(PARAMS["taubin_lambda"])
    diffuse(PARAMS["taubin_mu"])
for index,co in zip(ids,coords):
    bm.verts[int(index)].co=co
# The local selection is retained in the editable file for further sculpting.
bm.normal_update()
for f in bm.faces:
    if any(v[layer]>.00001 for v in f.verts):f.smooth=True
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3],
                     quad_method='BEAUTY',ngon_method='BEAUTY')
bm.verts.ensure_lookup_table();bm.verts.index_update()
final_weights=[float(v[layer]) for v in bm.verts]
bm.to_mesh(obj.data);bm.free();obj.data.update()

log("Blending normals into retained source surface")
preserve=obj.vertex_groups.new(name="M08_V02_NormalPreservation")
# Quantized bands are only for normal mixing, never for geometry deformation.
bands={}
for i,weight in enumerate(final_weights):
    bucket=int(round((1.-weight)*64))
    if bucket>0:bands.setdefault(bucket,[]).append(i)
for bucket,indices in bands.items():preserve.add(indices,bucket/64.,'REPLACE')
modifier=obj.modifiers.new("OriginalSurfaceNormalBlend","DATA_TRANSFER")
modifier.object=source;modifier.use_loop_data=True
modifier.data_types_loops={'CUSTOM_NORMAL'}
modifier.loop_mapping='POLYINTERP_NEAREST'
modifier.vertex_group=preserve.name
bpy.ops.object.modifier_apply(modifier=modifier.name)
group=obj.vertex_groups.get("M08_V02_NormalPreservation")
if group:obj.vertex_groups.remove(group)
selection=obj.vertex_groups.new(name="M08_BackRefinementRegion")
selection_bands={}
for i,weight in enumerate(final_weights):
    bucket=int(round(weight*64))
    if bucket>0:selection_bands.setdefault(bucket,[]).append(i)
for bucket,indices in selection_bands.items():selection.add(indices,bucket/64.,'REPLACE')
for im in bpy.data.images:
    if not im.packed_file:im.pack()

bpy.context.preferences.filepaths.save_version=0
bpy.context.scene["m08_stage"]="V02 dorsal edge refinement only; no new rig or UE integration"
blend=OUT/"M08_BackRebuilt_V02.blend"
glb=OUT/"M08_BackRebuilt_V02.glb"
log("Saving V02 Blender source and GLB")
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
    export_materials='EXPORT',export_normals=True,export_tangents=True,
    export_animations=False,export_image_format='AUTO')
obj.data.calc_loop_triangles()
receipt={
    "source":str(PREVIOUS/"M08_BackRebuilt_V01.blend"),
    "blend":str(blend),"glb":str(glb),
    "vertices":len(obj.data.vertices),"triangles":len(obj.data.loop_triangles),
    "localized_refinement_vertices":sum(w>.00001 for w in final_weights),
    "removed_small_cut_fragments":fragment_count,
    "parameters":PARAMS,"seconds":round(time.time()-START,2),
    "status":"saved authoring output; not visually accepted or game-tested",
    "preview_rendered":False,"ue_imported":False,
    "uv_and_textures":"Existing face UVs and packed textures retained; local subdivision interpolates UVs.",
}
(OUT/"build_parameters.json").write_text(json.dumps(PARAMS,indent=2),encoding='utf-8')
(OUT/"build_receipt.json").write_text(json.dumps(receipt,indent=2),encoding='utf-8')
log("SAVED "+json.dumps(receipt))
