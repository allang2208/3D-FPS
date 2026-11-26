"""Seat the approved Meshy head on the master artisan's existing R4 neck and transfer the native weights."""
import gzip
import json
import math
import sys
import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import trimesh
from pattern import ROOT, SRC
sys.path.insert(0,str(ROOT/"Tools/VillageCarpenterNPC/Head"))
from fit_head import native_neck, bridge_faces, split_overfull_edges, NATIVE_ALBEDO
from prepare_head import crop, interpolate, ring, sample_linear_color, sample_nose, unit

OUT=SRC/"HeadR4"
MODEL=OUT/"Head/Head.glb"

def read_head():
    # trimesh applies the glTF scene transform before fitting; the distributed GLB contains its own textures.
    scene=trimesh.load_scene(MODEL,process=False)
    meshes=scene.dump()
    if len(meshes)!=1:raise ValueError("Expected a single textured head surface")
    mesh=meshes[0]
    uv=np.array(mesh.visual.uv,dtype=float)
    uv[:,1]=1.-uv[:,1]
    mat=mesh.visual.material
    mat.baseColorTexture.convert("RGB").save(OUT/"T_ArtisanHead.png")
    mat.normalTexture.convert("RGB").save(OUT/"T_ArtisanHeadDetail.png")
    orm=np.asarray(mat.metallicRoughnessTexture.convert("RGB")).copy()
    # glTF packs roughness in green and metalness in blue; AO may be independent.
    orm[:,:,0]=np.asarray(mat.occlusionTexture.convert("L").resize((orm.shape[1],orm.shape[0]))) if mat.occlusionTexture else 255
    Image.fromarray(orm).save(OUT/"T_ArtisanHeadORM.png")
    return np.asarray(mesh.vertices)[:,[0,2,1]],np.asarray(mesh.vertex_normals)[:,[0,2,1]],uv,np.asarray(mesh.faces)

def neck_skin(points,uv,triangles,tint):
    base=np.asarray(Image.open(NATIVE_ALBEDO).convert("RGB"))
    h,w=base.shape[:2]
    mask=np.zeros((h,w),np.float32)
    for indices in triangles:
        face=uv[indices]*[w,h]-.5
        lo=np.maximum(np.floor(face.min(0)).astype(int),0)
        hi=np.minimum(np.ceil(face.max(0)).astype(int)+1,[w,h])
        if np.any(hi<=lo):continue
        a,b,c=face
        transform=np.column_stack([b-a,c-a])
        if abs(np.linalg.det(transform))<1e-7:continue
        yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]]
        s,t=np.linalg.inv(transform)@np.vstack(((xx-a[0]).ravel(),(yy-a[1]).ravel()))
        s,t=s.reshape(xx.shape),t.reshape(xx.shape)
        inside=(s>=0)&(t>=0)&(s+t<=1)
        z0,z1,z2=points[indices,2]
        fade=np.clip((z0+(z1-z0)*s+(z2-z0)*t-150.4)/4.1,0,1)
        patch=mask[lo[1]:hi[1],lo[0]:hi[0]]
        patch[inside]=fade[inside]**2*(3-2*fade[inside])
    mask=cv2.dilate(mask,np.ones((3,3),np.uint8))[:,:,None]
    s=base.astype(np.float32)/255.
    linear=np.where(s<=.04045,s/12.92,((s+.055)/1.055)**2.4)*(1.+mask*(tint-1.))
    color=np.where(linear<=.0031308,12.92*linear,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    Image.fromarray(np.uint8(np.clip(color*255+.5,0,255))).save(OUT/"T_ArtisanNeck.png")

def main():
    raw,n,uv,tri=read_head()
    (lp,ln,luv,lw,lf,lower_edges),native,weights,head_bone,skeleton=native_neck()
    crown,tip=sample_nose(raw)
    scale=(180.6-164.9)/(crown-tip[2])
    pos=(raw-tip)*scale+[0.,13.2,164.9]
    head_w=[weights[i] if z<161 and (y>-6.0 or z<156.9) else {head_bone:1.}
            for i,(_,y,z) in zip(cKDTree(native).query(pos)[1],pos)]
    # Crop only at the neck; the low knot, frame, jaw and beard remain on the generated head.
    cut=max(154.85,float(pos[:,2].min())+.40)
    if cut>157.5:raise ValueError(f"Source neck ends too high for this collar ({cut:.2f})")
    p,n,uv,ws,f,upper_edges=crop(pos,n,uv,head_w,tri,cut,True)
    center=np.median(lp[lower_edges],axis=0)
    la,li=ring(lp,lower_edges,center)
    ha,hi=ring(p,upper_edges,center)
    angles=np.arctan2(p[:,1]-center[1],p[:,0]-center[0])
    target=np.column_stack([np.interp(angles,la,lp[li,i],period=math.tau) for i in (0,1)])
    fade=np.clip((cut+1.85-p[:,2])/1.85,0.,1.)
    fade=fade*fade*(3.-2.*fade)
    p[:,:2]+=(target-p[:,:2])*fade[:,None]
    collar=cKDTree(lp[li,:2])
    moved=np.flatnonzero(fade>0)
    for k,j in zip(moved,li[collar.query(p[moved,:2])[1]]):
        ws[k]=interpolate(ws[k],lw[j],fade[k])
        n[k]=unit(n[k]*(1-fade[k])+ln[j]*fade[k])
    mapped=li[collar.query(p[hi,:2])[1]]
    join=bridge_faces(p[hi],lp[li],ha,la)
    locations=np.vstack((p,lp,p[hi],lp[li]))
    normals=np.vstack((n,ln,ln[mapped],ln[li]))
    coords=np.vstack((uv,luv,luv[mapped],luv[li]))
    triangles=np.vstack((f,lf+len(p),join+len(p)+len(lp)))
    bone_rows=ws+lw+[ws[i] for i in hi]+[lw[i] for i in li]
    ids=np.r_[np.zeros(len(f),dtype=int),np.ones(len(lf)+len(join),dtype=int)]
    remap,triangles,ids=split_overfull_edges(locations,triangles,ids)
    geometry=dict(p=locations[remap].round(6).tolist(),n=normals[remap].round(7).tolist(),uv=coords[remap].round(7).tolist(),
                  tri=triangles.tolist(),w=[list(bone_rows[i].items()) for i in remap],m=ids.tolist(),materials=["Head","Neck"])
    with gzip.open(OUT/"Head.json.gz","wt",encoding="utf8",compresslevel=3) as stream:
        json.dump(geometry,stream,separators=(",",":"))
    seam=sample_linear_color(OUT/"T_ArtisanHead.png",uv[hi])
    base=sample_linear_color(NATIVE_ALBEDO,luv[li])
    tint=np.clip(seam/np.maximum(.005,base),.30,3.)
    neck_skin(lp,luv,lf,tint)
    report=dict(skeleton=skeleton,source="Head/Head.glb",raw_triangles=len(tri),fitted_triangles=len(ids),
                head_triangles=int((ids==0).sum()),crown_cm=180.6,uniform_scale=scale,neck_cut_cm=cut,
                neck_color_multiplier=tint.tolist(),nose_source=tip.tolist())
    (OUT/"fit.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print("Fitted",report["raw_triangles"],"source triangles to the native neck at",round(cut,2),"cm")

if __name__=="__main__":main()
