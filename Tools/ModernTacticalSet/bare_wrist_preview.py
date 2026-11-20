"""Render the same M870 idle pose with the original and repaired skin coverage."""
import gzip
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from bare_wrist_review import ROOT, SET, load
from native_glove_review import Skin, component


def unit(v):
    return v/np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-10)


def main():
    sources = SET/"NativeGloveR1/Read"
    pose = json.load(gzip.open(sources/"M870_poses.json.gz","rt"))
    names = pose["names"]
    local = pose["clips"]["A_M870_idle"]["local"][0]
    world = component(local,[names.index(p) if p in names else -1 for p in pose["parents"]])
    cloth = Skin(load(SET/"CombatShirtR4/Authored/shirt_fp_Super90.json"),names,False)
    skin_source = load(sources/"M870_Jason.json")
    native = Skin(skin_source,names,False)
    verts = np.vstack([cloth.skin(world),native.skin(world)])
    palette = np.array([[119,105,73],[90,77,54],[75,67,52],[156,139,92],[106,94,69],[197,145,109]])
    w,h,scale = 410,225,2
    out = Image.new("RGB",(2*w,2*h+69),(29,33,35))
    draw = ImageDraw.Draw(out)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",17)
    for col, label in enumerate(("原袖口","修订后")):
        draw.text((col*w+12,8),label,font=font,fill="#f2f0ea")
    for row, side in enumerate("lr"):
        wrist = world[names.index("hand_"+side),:3,3]
        elbow = world[names.index("lowerarm_"+side),:3,3]
        ahead = unit(wrist-elbow)
        across = unit(world[names.index("index_01_"+side),:3,3]-world[names.index("pinky_01_"+side),:3,3])
        sight = unit(across-ahead*(ahead@across))
        horizontal = ahead
        vertical = unit(np.cross(sight,horizontal))
        center = wrist - 2*horizontal
        proj = (verts-center)@np.array([horizontal,vertical,sight]).T
        xy = np.rint((proj[:,:2]*[18,-18]+[w/2,h/2])*scale).astype(int)
        ref = native.points-np.array(skin_source["bones"]["hand_"+side]["position"])
        for col in (0,1):
            # At this view scale every face near the receding mask edge is under the sleeve.
            mask = native.mats==2
            if col:
                mask |= (native.mats==1) & (np.linalg.norm(ref[native.faces],axis=2).mean(1)<11.0)
            faces = np.concatenate([cloth.faces,native.faces[mask]+len(cloth.points)])
            regions = np.concatenate([cloth.mats,np.full(mask.sum(),5)])
            focus = np.linalg.norm(verts[faces].mean(1)-center,axis=1)<16
            faces,regions = faces[focus],regions[focus]
            tri = proj[faces]
            n = unit(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]))
            n[n[:,2]<0] *= -1
            shade = .66+.43*np.maximum(0,n@unit(np.array([-.4,.5,.85])))
            rgb = np.clip(palette[regions]*shade[:,None],0,255).astype("uint8")
            img = Image.new("RGB",(w*scale,h*scale),(56,67,75))
            p = ImageDraw.Draw(img)
            for i in np.argsort(tri[:,:,2].mean(1)):
                p.polygon([tuple(v) for v in xy[faces[i]]],fill=tuple(rgb[i]))
            out.paste(img.resize((w,h),Image.Resampling.LANCZOS),(col*w,38+row*h))
        draw.text((12,44+row*h),"左腕" if side=="l" else "右腕",font=font,fill="#f2f0ea")
    draw.text((12,2*h+43),"M870 待机网格对照 · 同一机位、同一姿态 · 简化材质",font=font,fill="#cdd3d3")
    out.save(ROOT/"m870-bare-wrists.jpg",quality=92)


if __name__ == "__main__":
    main()
