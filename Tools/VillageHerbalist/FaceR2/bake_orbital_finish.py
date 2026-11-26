"""Bake the intact reference eyes onto the revised orbital surfaces using their existing UVs."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Face"))
import author_face_texture as face

def project_sculpt(offset_path):
    xy, depth, uv, tris=face.primitive()
    old=np.column_stack(((xy[:,0]-300.)/face.PROJECTION_SCALE,
                         1.681-xy[:,1]/face.PROJECTION_SCALE,depth))
    edit=np.load(offset_path)
    distance,indices=cKDTree(edit["original"]).query(old)
    matches=distance<2.e-5
    if np.count_nonzero(matches)<500:
        raise RuntimeError("Rest mesh coordinates do not match the orbital sculpt")
    moved=old.copy()
    moved[matches]+=edit["sculpted"][indices[matches]]-edit["original"][indices[matches]]
    xy=np.column_stack((300.+moved[:,0]*face.PROJECTION_SCALE,(1.681-moved[:,1])*face.PROJECTION_SCALE)).astype(np.float32)
    return xy,moved[:,2].astype(np.float32),uv,tris

def draw_eyes(reference):
    yy,xx=np.indices((face.H*face.SS,face.W*face.SS),dtype=np.float32)/face.SS
    weights=np.zeros_like(xx)
    colors=np.zeros((*xx.shape,3),np.float32)
    for center, refcenter, angle, outline in [
        ((231.5,231.6),(233.,85.),-.065,[(194,221),(201,214),(219,211),(241,211),(252,214),(264,220),(270,229),(267,244),(258,252),(238,258),(216,256),(199,251),(193,242)]),
        ((350.,231.),(267.1,84.8),.015,[(315,224),(321,214),(337,209),(357,209),(375,210),(389,213),(396,219),(396,238),(388,249),(373,255),(351,257),(331,252),(316,247),(310,237)])]:
        sx=(xx-center[0])/3.1+refcenter[0]
        sy=(yy-center[1]-angle*(xx-center[0]))/2.95+refcenter[1]
        # Sample the eyelid and under-eye skin inside the reference frame. Its outer wire
        # already exists as physical geometry on the target model.
        sy=np.maximum(sy,80.6+.009*(sx-refcenter[0])**2)
        sample=cv2.remap(reference,sx,sy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
        # The original full-body reference resolves each iris in only a few
        # pixels. Keep its colour and aperture, and restore the dark pupil,
        # outer iris edge and single upper-lid line at the atlas resolution.
        dx=xx-center[0]
        dy=yy-center[1]-angle*dx
        arch=np.maximum(0.,1.-(dx/23.)**2)**.68
        upper=-6.8*arch
        lower=5.6*arch
        def feather(value):
            value=np.clip(value,0.,1.)
            return value*value*(3.-2.*value)
        opening=feather((dy-upper+.5)/1.8)*feather((lower-dy+.5)/1.8)*feather((23.-abs(dx))/2.)
        shade=sample*1.04+[13.,12.,11.]
        def tint(colour,opacity):
            nonlocal shade
            shade=shade*(1.-opacity[...,None])+np.array(colour)*opacity[...,None]
        radius=np.sqrt(dx*dx+(dy+.50)**2)
        tint((185.,164.,152.),opening*feather((radius-6.)/4.)*.28)
        iris=opening*feather((8.4-radius)/1.5)
        tint((80.,65.,49.),iris*.66)
        tint((47.,41.,36.),iris*feather((radius-5.9)/1.25)*.76)
        tint((30.,28.,28.),opening*feather((3.8-radius)/1.35)*.93)
        lash=np.exp(-((dy-upper+.24)/1.02)**2)*feather((22.-abs(dx))/4.)
        tint((59.,46.,38.),.59*lash)
        glint=np.exp(-((dx+2.55)**2+(dy+3.3)**2)/(1.15**2))*opening
        tint((203.,191.,167.),glint*.71)
        w=face.mask_polygon(outline,5.0)
        active=w>0
        colors[active]=shade[active]
        weights[active]=w[active]
    return colors.clip(0,255),weights

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--sculpt",type=Path,required=True)
    parser.add_argument("--dest",type=Path,required=True)
    args=parser.parse_args()
    args.dest.mkdir(parents=True,exist_ok=True)
    xy,depth,uv,tris=project_sculpt(args.sculpt)
    zb,ids,texcoord=face.projection(xy,depth,uv,tris)
    color=np.array(Image.open(face.R1/face.COLOR).convert("RGB"))
    ref=np.array(Image.open(face.BODY/"MeshyR1/Inputs/01_front.png").convert("RGB")).astype(np.float32)
    old_view=face.render_texels(color,texcoord,ids)
    target,weight=face.patch_layer(ref,old_view)
    eye_rgb,eye_weight=draw_eyes(ref)
    select=eye_weight>weight
    target[select]=eye_rgb[select];weight[select]=eye_weight[select]
    target,weight=face.spectacle_surfaces(old_view,target,weight,zb,ref)
    uvpx=uv*np.array([color.shape[1],color.shape[0]],dtype=np.float32)-.5
    baked,affected=face.bake_visible(xy,depth,tris,uvpx,ids,zb,target,weight,color)
    color_padding=face.extend_seams(color,baked,affected,uvpx,tris)
    Image.fromarray(baked).save(args.dest/face.COLOR)
    normal_name=face.COLOR.replace("Color","Normal")
    normal=np.array(Image.open(face.R1/normal_name).convert("RGB"))
    # The old tangent-space ridges describe the discarded false eyelid. Retain small
    # residual texture under a soft transition into the existing cheeks and brows.
    neutral=np.full_like(target,128.);neutral[:,:,2]=255.
    softened,nb=face.bake_visible(xy,depth,tris,uvpx,ids,zb,neutral,eye_weight*.94,normal)
    normal_padding=face.extend_seams(normal,softened,nb,uvpx,tris)
    Image.fromarray(softened).save(args.dest/normal_name)
    info={"revised_visible_color_texels":int(affected.sum()),"revised_visible_normal_texels":int(nb.sum()),
          "unused_atlas_padding_color_normal":[int(color_padding),int(normal_padding)],
          "source":"UEAuthoringR1 original atlases + FaceR2 orbital-offsets + MeshyR1/Inputs/01_front.png",
          "outputs":{name:hashlib.sha256((args.dest/name).read_bytes()).hexdigest() for name in (face.COLOR,normal_name)}}
    (args.dest/"orbital-bake.json").write_text(json.dumps(info,indent=2))
    (args.dest/"face_texture_source.json").write_text(json.dumps(info,indent=2))
    print(json.dumps(info))
if __name__=="__main__":
    main()

