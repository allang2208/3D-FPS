"""M-08 local dorsal aperture rebuild. Background authoring only; no preview/test run.
Preserves input file, body surface, original texture images and source scale.
"""
import bpy, bmesh, json, math, time, shutil
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SOURCE=Path(r"C:\Users\allan\Downloads\Meshy_AI_Mawbound_Leviathan_1004040702_texture.glb")
OUT=Path(r"D:\FPS3D\FPSGAME\SourceAssets\Monsters\LurkerM08\BackRebuildV01_20261004")
OUT.mkdir(parents=True,exist_ok=True)
TEXTURES=OUT/"Textures"
TEXTURES.mkdir(exist_ok=True)
started=time.time()
def log(msg): print("M08_BUILD "+msg,flush=True)
def move_collection(obj,col):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    col.objects.link(obj)
def smoothstep(x):
    x=max(0.0,min(1.0,x)); return x*x*(3-2*x)

PARAMS={
    "aperture_center_x":-0.00055,
    "aperture_center_z":0.205,
    "aperture_radius_x":0.105,
    "aperture_radius_z":0.121,
    "longitudinal_half_length":1.10,
    "radial_segments":128,
    "longitudinal_segments":96,
    "rim_bevel_source_units":0.006,
    "rim_bevel_segments":4,
    "patch_atlas_resolution":[1024,1024],
    "surface_treatment":"source color and roughness reprojection; organic nonmetal inner wall",
    "source_scale_preserved":True,
}
(OUT/"build_parameters.json").write_text(json.dumps(PARAMS,indent=2),encoding="utf-8")
archive=OUT/"Meshy_original.glb"
if not archive.exists(): shutil.copy2(SOURCE,archive)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(archive),merge_vertices=True,import_shading='NORMALS')
source=next(o for o in bpy.context.scene.objects if o.type=='MESH')
source.name="M08_Original_Reference"
original_collection=bpy.data.collections.new("SOURCE_original_hidden")
bpy.context.scene.collection.children.link(original_collection)
move_collection(source,original_collection)
guide_collection=bpy.data.collections.new("CONSTRUCTION_aperture")
bpy.context.scene.collection.children.link(guide_collection)
result_collection=bpy.data.collections.new("DELIVERY_rebuilt_back")
bpy.context.scene.collection.children.link(result_collection)

source.data.calc_loop_triangles()
vertices=np.empty(len(source.data.vertices)*3,np.float32)
source.data.vertices.foreach_get("co",vertices);vertices=vertices.reshape(-1,3)
triangles=np.empty(len(source.data.loop_triangles)*3,np.int32)
source.data.loop_triangles.foreach_get("vertices",triangles);triangles=triangles.reshape(-1,3)
source_uv=np.empty(len(source.data.loops)*2,np.float32)
source.data.uv_layers.active.data.foreach_get("uv",source_uv)
source_uv=source_uv.reshape(-1,3,2)
tree=BVHTree.FromObject(source,bpy.context.evaluated_depsgraph_get(),deform=False,cage=False)
original_material=source.data.materials[0]
bsdf=next(n for n in original_material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
base_image=bsdf.inputs["Base Color"].links[0].from_node.image
source_images=[n.image for n in original_material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
mr_image=next(im for im in source_images if im.name=="Image_1")

result=source.copy();result.data=source.data.copy();result.name="M08_BackRebuilt_V01"
result_collection.objects.link(result)
result["source_file"]=str(SOURCE)
result["revision"]="V01 dorsal four-support canopy, front/rear aperture"
result["status"]="Authoring output; not user-tested or UE-imported"
source.hide_render=True
source.hide_set(True)
source.hide_viewport=True
original_collection.hide_render=True

# Organic bore profile. It intersects only the upper central dorsal region.
def profile(theta,y):
    flare=0.015*smoothstep(abs(y-0.08)/0.9)
    rx=PARAMS["aperture_radius_x"]+flare
    rz=PARAMS["aperture_radius_z"]+flare*0.30
    wave=1.0+0.012*math.cos(4*theta)+0.007*math.cos(10*theta)*math.cos(2*y)
    return (PARAMS["aperture_center_x"]+rx*math.cos(theta)*wave,
            y,
            PARAMS["aperture_center_z"]+rz*math.sin(theta)*wave)

N=PARAMS["radial_segments"];L=PARAMS["longitudinal_segments"];half=PARAMS["longitudinal_half_length"]
cverts=[];cfaces=[];cuv=[]
for k in range(L+1):
    y=-half+2*half*k/L
    for j in range(N):
        cverts.append(profile(2*math.pi*j/N,y))
for k in range(L):
    for j in range(N):
        a=k*N+j;b=k*N+(j+1)%N;c=(k+1)*N+(j+1)%N;d=(k+1)*N+j
        cfaces.append((a,b,c,d))
        cuv.append(((j/N,k/L),((j+1)/N,k/L),((j+1)/N,(k+1)/L),(j/N,(k+1)/L)))
cfaces.append(tuple(reversed(range(N))));cuv.append(tuple((0,0) for j in range(N)))
cfaces.append(tuple(L*N+j for j in range(N)));cuv.append(tuple((0,1) for j in range(N)))
mesh=bpy.data.meshes.new("DorsalAperture_ControlMesh")
mesh.from_pydata(cverts,[],cfaces);mesh.update()
cutter=bpy.data.objects.new("DorsalAperture_Control",mesh);guide_collection.objects.link(cutter)
uv=mesh.uv_layers.new(name="UVMap")
for poly,coords in zip(mesh.polygons,cuv):
    for li,co in zip(poly.loop_indices,coords): uv.data[li].uv=co
# Closed solid with outward normals for the exact subtraction.
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()

patch_material=bpy.data.materials.new("M08_RebuiltInnerArch_PBR")
patch_material.use_nodes=True
patch_material.diffuse_color=(.7,.6,.56,1)
result.data.materials.append(patch_material)
cutter.data.materials.append(original_material)
cutter.data.materials.append(patch_material)
for p in cutter.data.polygons:p.material_index=1

bpy.ops.object.select_all(action='DESELECT')
result.select_set(True);bpy.context.view_layer.objects.active=result
cut=result.modifiers.new("Back_Through_Aperture","BOOLEAN")
cut.operation='DIFFERENCE';cut.solver='EXACT';cut.object=cutter
cut.material_mode='TRANSFER'
log("Applying local aperture subtraction")
bpy.ops.object.modifier_apply(modifier=cut.name)
cutter.display_type='WIRE';cutter.hide_render=True;cutter.hide_set(True)
cutter.hide_viewport=True;guide_collection.hide_render=True

# Round only the intersection rim; original distant face/hand/limb topology is retained.
log("Rounding cut rim and assigning continuous inner-wall UV")
bm=bmesh.new();bm.from_mesh(result.data)
edges=[e for e in bm.edges if len(e.link_faces)==2 and e.link_faces[0].material_index!=e.link_faces[1].material_index]
bevel_result=bmesh.ops.bevel(bm,geom=edges,offset=PARAMS["rim_bevel_source_units"],
    segments=PARAMS["rim_bevel_segments"],profile=.5,affect='EDGES',
    clamp_overlap=True,loop_slide=True,material=1)
uv_layer=bm.loops.layers.uv.get("UVMap")
for face in bm.faces:
    if face.material_index!=1:continue
    face.smooth=True
    us=[]
    for loop in face.loops:
        co=loop.vert.co
        flare=.015*smoothstep(abs(co.y-.08)/.9)
        theta=math.atan2((co.z-PARAMS["aperture_center_z"])/(PARAMS["aperture_radius_z"]+flare*.30),
                         (co.x-PARAMS["aperture_center_x"])/(PARAMS["aperture_radius_x"]+flare))
        us.append((theta%(2*math.pi))/(2*math.pi))
    seam=max(us)-min(us)>.5
    for loop,u in zip(face.loops,us):
        if seam and u<.5:u+=1
        loop[uv_layer].uv=(u,(loop.vert.co.y+half)/(2*half))
# Finalize only authored polygons for glTF tangent generation; imported faces are triangles already.
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3],
    quad_method='BEAUTY',ngon_method='BEAUTY')
bm.to_mesh(result.data);bm.free();result.data.update()

# Original source normals are retained away from the newly authored rim.
log("Restoring source surface normals away from the aperture")
cut_vertices=set()
for p in result.data.polygons:
    if p.material_index==1:cut_vertices.update(p.vertices)
preserve=result.vertex_groups.new(name="OriginalSurfaceNormals")
kept=[v.index for v in result.data.vertices if v.index not in cut_vertices]
preserve.add(kept,1.0,'REPLACE')
normal_transfer=result.modifiers.new("PreserveOriginalSurfaceNormals","DATA_TRANSFER")
normal_transfer.object=source
normal_transfer.use_loop_data=True
normal_transfer.data_types_loops={'CUSTOM_NORMAL'}
normal_transfer.loop_mapping='POLYINTERP_NEAREST'
normal_transfer.vertex_group=preserve.name
bpy.ops.object.modifier_apply(modifier=normal_transfer.name)
restored_group=result.vertex_groups.get('OriginalSurfaceNormals')
if restored_group is not None:result.vertex_groups.remove(restored_group)

# Build a dedicated patch atlas from the original PBR surface at nearest positions.
# New inner wall has its own UVs, not stretched unrelated islands from the old mesh.
W,H=PARAMS["patch_atlas_resolution"]
nearest_uv=np.empty((H,W,2),np.float32)
log("Reprojecting original skin colors and roughness to the new wall atlas")
for row in range(H):
    y=-half+2*half*(row+.5)/H
    for col in range(W):
        theta=2*math.pi*(col+.5)/W
        point=Vector(profile(theta,y))
        pos,normal,idx,dist=tree.find_nearest(point)
        tri=vertices[triangles[idx]]
        a=tri[1]-tri[0];b=tri[2]-tri[0];d=np.asarray(pos)-tri[0]
        aa=float(np.dot(a,a));ab=float(np.dot(a,b));bb=float(np.dot(b,b))
        da=float(np.dot(d,a));db=float(np.dot(d,b))
        denom=aa*bb-ab*ab
        if abs(denom)<1e-22:
            u=v=0.0
        else:
            u=(bb*da-ab*db)/denom;v=(aa*db-ab*da)/denom
        nearest_uv[row,col]=source_uv[idx,0]*(1-u-v)+source_uv[idx,1]*u+source_uv[idx,2]*v
    if row%128==0:log("Atlas row "+str(row)+"/"+str(H))

def image_array(im):
    data=np.empty(im.size[0]*im.size[1]*4,np.float32)
    im.pixels.foreach_get(data);return data.reshape(im.size[1],im.size[0],4)
def sample(im,uv):
    pixels=image_array(im);ih,iw=pixels.shape[:2]
    x=np.clip(uv[:,:,0],0,1)*(iw-1);y=np.clip(uv[:,:,1],0,1)*(ih-1)
    x0=np.floor(x).astype(np.int32);y0=np.floor(y).astype(np.int32)
    x1=np.minimum(x0+1,iw-1);y1=np.minimum(y0+1,ih-1)
    ax=(x-x0)[...,None];ay=(y-y0)[...,None]
    return ((pixels[y0,x0]*(1-ax)+pixels[y0,x1]*ax)*(1-ay)+
            (pixels[y1,x0]*(1-ax)+pixels[y1,x1]*ax)*ay)
color=sample(base_image,nearest_uv)
mr=sample(mr_image,nearest_uv)
color[:,:,3]=1
mr[:,:,0]=1;mr[:,:,2]=0;mr[:,:,3]=1
# Gentle roughness lift for fresh organic cut wall; keep the source variation.
mr[:,:,1]=np.clip(mr[:,:,1],.25,.82)
def save_atlas(name,pixels,space):
    im=bpy.data.images.new(name,width=W,height=H,alpha=True)
    im.colorspace_settings.name=space
    im.pixels.foreach_set(np.ascontiguousarray(pixels,dtype=np.float32).ravel())
    im.filepath_raw=str(TEXTURES/(name+".png"));im.file_format='PNG'
    im.save();im.pack();return im
new_color=save_atlas("M08_ArchInterior_BaseColor",color,'sRGB')
new_mr=save_atlas("M08_ArchInterior_MetallicRoughness",mr,'Non-Color')
nodes=patch_material.node_tree.nodes;links=patch_material.node_tree.links
p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
ct=nodes.new('ShaderNodeTexImage');ct.image=new_color
mt=nodes.new('ShaderNodeTexImage');mt.image=new_mr
sep=nodes.new('ShaderNodeSeparateColor');sep.mode='RGB'
links.new(ct.outputs['Color'],p.inputs['Base Color'])
links.new(mt.outputs['Color'],sep.inputs['Color'])
links.new(sep.outputs['Green'],p.inputs['Roughness'])
links.new(sep.outputs['Blue'],p.inputs['Metallic'])
p.inputs['Metallic'].default_value=0
# Original tangent normal map remains on the retained mesh; new rounded wall uses
# its own smooth geometric normals, avoiding an incorrect transferred tangent frame.
for im in source_images:
    if not im.packed_file:im.pack()

log("Saving editable source and revised GLB")
bpy.ops.object.select_all(action='DESELECT')
result.hide_set(False);result.select_set(True);bpy.context.view_layer.objects.active=result
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene["m08_stage"]="Local dorsal rebuild only; no rig, game integration or user test"
bpy.context.scene["m08_source_scale"]="Retained original Meshy scale; not assigned final game size"
blend_path=OUT/"M08_BackRebuilt_V01.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path),compress=True)
glb_path=OUT/"M08_BackRebuilt_V01.glb"
bpy.ops.export_scene.gltf(filepath=str(glb_path),export_format='GLB',
    use_selection=True,export_materials='EXPORT',export_normals=True,
    export_tangents=True,export_animations=False,export_image_format='AUTO')
result.data.calc_loop_triangles()
receipt={
    "source":str(SOURCE),"preserved_copy":str(archive),"blend":str(blend_path),
    "glb":str(glb_path),"parameters":PARAMS,
    "output_vertices":len(result.data.vertices),
    "output_triangles":len(result.data.loop_triangles),
    "materials":[m.name for m in result.data.materials],
    "authored_inner_wall_faces":sum(p.material_index==1 for p in result.data.polygons),
    "seconds":round(time.time()-started,2),
    "stage":"saved authoring output, not tested",
    "preview_rendered":False,"ue_imported":False,
    "geometry_scope":"local central upper-back aperture and rounded transition only",
    "source_texture_scope":"original color, metallic-roughness, normal maps kept; new inner-wall color and roughness reprojected",
    "known_limit":"No deformation, game, visual acceptance or self-intersection tests were run."
}
(OUT/"build_receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
log("SAVED "+json.dumps(receipt))
