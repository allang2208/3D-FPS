"""Soften the raised second eyelid inside each lens of Lin Zhi's original skin.
Run in background Blender. Coordinates are measured on the fixed 600 px source portrait.
The original rest mesh, weight maps, UVs, outer spectacle rim and bone transforms are retained.
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BODY = ROOT / "SourceAssets/VillageHerbalist/FullBody"
OUT = BODY / "FaceR2"
REVIEW = ROOT / "Saved/HerbalistFaceReview"
source = BODY / "UEAuthoringR1/VillageHerbalist.blend"
bpy.ops.wm.open_mainfile(filepath=str(source))
obj, = (o for o in bpy.context.scene.objects if o.type == "MESH")
rig = obj.find_armature()
mesh = obj.data
verts = np.array([v.co[:] for v in mesh.vertices], dtype=np.float64)
old = verts.copy()
loop_ids = np.array([c.vertex_index for c in mesh.loops])
normals = np.array([c.vector[:] for c in mesh.corner_normals], dtype=np.float64)
# Image projection is 30.24 cm across at the normalized 168 cm height.
cm_per_px = .0504
px = (verts[:,0] + .05105) / cm_per_px + 300.
py = (155.4 - verts[:,2]) / cm_per_px + 300.
def ease(x):
    t = np.clip(x, 0., 1.)
    return t*t*(3.-2.*t)
def design(u, v):
    return np.column_stack((np.ones_like(u), u, v, u*u, u*v, v*v))
touched = np.zeros(len(verts),dtype=bool)
relax = np.zeros(len(verts))
for cx,cy,rx,ry in [(241.,282.,39.,26.), (367.,280.,41.,26.)]:
    u=(px-cx)/rx
    v=(py-cy)/ry
    # Two broad bands of orbital skin above and below the false ledges supply the
    # local curvature. Exclude the bridge, the temples and the spectacle frame.
    radius=np.sqrt(u*u+v*v)
    samples=(abs(u)<.93)&(((v>.80)&(v<1.27))|((v<-.70)&(v>-.97)))&(old[:,1]<-5.)
    A=design(u[samples],v[samples])
    depths=old[samples,1]
    coeff=np.linalg.lstsq(A,depths,rcond=None)[0]
    for _ in range(5):
        residual=np.abs(A@coeff-depths)
        weight=np.minimum(1.,.12/np.maximum(residual,1.e-6))
        coeff=np.linalg.lstsq(A*weight[:,None],depths*weight,rcond=None)[0]
    curved=design(u,v)@coeff
    # A low oval remains over the globe rather than flattening the eye to a plane.
    globe=.14*np.exp(-1.55*u*u-2.6*v*v)
    target=curved-globe
    # The existing outer rim stands noticeably forward of the orbital surface.
    # Protect it at the edges even where the camera silhouettes overlap.
    w=ease((1.13-radius)/.33)*ease((-5.-old[:,1])/.65)
    edge=ease((abs(u)-.74)/.21)
    w*=1.-edge*ease((target-old[:,1]-.58)/.37)
    w*=.94
    delta=np.clip(target-old[:,1],-.42,1.05)
    verts[:,1]+=w*delta
    active=w>.0001
    touched|=active
    relax=np.maximum(relax,w)
    # Old split normals encode the steep inner walls of the generated ledges.
    # Rotate only the retouched loops towards the orbital surface normal.
    dx=(coeff[1]+2*coeff[3]*u+coeff[4]*v+3.10*u*globe)/(rx*cm_per_px)
    dz=-(coeff[2]+coeff[4]*u+2*coeff[5]*v+5.20*v*globe)/(ry*cm_per_px)
    tn=np.column_stack((dx,-np.ones_like(u),dz))
    tn/=np.linalg.norm(tn,axis=1)[:,None]
    lw=w[loop_ids,None]
    normals=normals*(1.-lw)+tn[loop_ids]*lw

# Relax the overhanging lid folds along the surface as well as in depth.
# Weld by position for this calculation so UV islands remain in contact.
_, rep, welded=np.unique(np.round(old,4),axis=0,return_index=True,return_inverse=True)
welded=welded.ravel()
edge=np.array([e.vertices[:] for e in mesh.edges])
edge=np.unique(np.sort(welded[edge],axis=1),axis=0)
both=np.concatenate((edge,edge[:,::-1]))
active=relax[rep][both[:,0]]>.001
orig,dst=both[active].T
ids=np.unique(orig)
inv=np.searchsorted(ids,orig)
degree=np.bincount(inv)
coords=verts[rep].copy()
strength=relax[rep][ids,None]*.69
for _ in range(26):
    avg=np.stack([np.bincount(inv,weights=coords[dst,i])/degree for i in range(3)],axis=1)
    coords[ids]+=strength*(avg-coords[ids])
verts[touched]=coords[welded[touched]]

# A few narrow remnants of the old folds face inward in front of the skin.
# Recess those triangles behind the continuous orbital surface, including their
# shared UV seam vertices, so a two-sided material cannot shade a black fleck.
tri=np.array([p.vertices[:] for p in mesh.polygons])
for _ in range(2):
    a,b,c=verts[tri].transpose(1,0,2)
    fn=np.cross(b-a,c-a)
    inward=fn[:,1]/np.maximum(np.linalg.norm(fn,axis=1),1.e-9)
    lid=relax[tri].min(1)
    folds=(lid>.51)&(inward>.35)
    inset=np.zeros(len(coords))
    for corner in tri[folds].T:
        np.maximum.at(inset,welded[corner], .075*lid[folds])
    verts[:,1]+=inset[welded]

mesh.vertices.foreach_set("co",verts.astype(np.float32).ravel())
mesh.update()
normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1.e-9)
mesh.normals_split_custom_set(normals.tolist())
mesh.update()
bpy.context.view_layer.update()
ready = "--publish" in sys.argv
dest=OUT if ready else REVIEW/"_work/geometry"
dest.mkdir(parents=True,exist_ok=True)
to_blender=np.array(json.loads((BODY/"UEAuthoringR1/rig.json").read_text())["source_to_cm"])
def rig_positions(p):
    native=(p-to_blender[:3,3])@np.linalg.inv(to_blender[:3,:3]).T
    return np.stack((native[:,0],native[:,2],-native[:,1]),axis=1).astype(np.float32)
np.savez_compressed(dest/"orbital-offsets.npz",original=rig_positions(old[touched]),
                    sculpted=rig_positions(verts[touched]))
if ready:
    for mat in obj.data.materials:
        bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        for role,socket in (("Color",bsdf.inputs["Base Color"]),("Normal",bsdf.inputs["Normal"])):
            tex=OUT/f"T_VillageHerbalist_{role}.png"
            if not tex.exists() or not socket.links:continue
            node=socket.links[0].from_node
            if role=="Normal":node=node.inputs["Color"].links[0].from_node
            if node.type=="TEX_IMAGE":
                node.image=bpy.data.images.load(str(tex),check_existing=True)
                node.image.colorspace_settings.name="sRGB" if role=="Color" else "Non-Color"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(dest/"VillageHerbalist.blend"),relative_remap=True)
info=dict(revision="FaceR2",source="UEAuthoringR1/VillageHerbalist.blend",
          changed_vertices=int(np.count_nonzero(abs(verts[:,1]-old[:,1])>.0001)),
          max_displacement_mm=float(np.linalg.norm(verts-old,axis=1).max()*10),triangles=len(mesh.polygons),
          bones=len(rig.data.bones),mesh_objects=[obj.name])
if ready:
    bpy.ops.object.select_all(action="DESELECT")
    for o in (obj,rig):o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    output=dest/"SK_VillageHerbalist.fbx"
    bpy.ops.export_scene.fbx(filepath=str(output),use_selection=True,
        object_types={"ARMATURE","MESH"},add_leaf_bones=False,use_armature_deform_only=False,
        armature_nodetype="NULL",bake_anim=False,apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="Y",axis_up="Z",use_mesh_modifiers=False,mesh_smooth_type="FACE",
        path_mode="RELATIVE",embed_textures=False)
    import hashlib
    info["fbx_sha256"]=hashlib.sha256(output.read_bytes()).hexdigest()
    (dest/"mesh-ready.json").write_text(json.dumps(info,indent=2))
print(json.dumps(info))

