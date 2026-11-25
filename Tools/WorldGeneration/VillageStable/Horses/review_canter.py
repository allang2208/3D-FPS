"""Render the original GLB and the two evaluated UE clips on the same textured horse."""
import argparse
import json
from pathlib import Path

import numpy as np
from numba import njit
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation

from prepare_horse import Horse, SOURCE


def skin_frames(horse, samples):
    mesh = horse.doc["meshes"][0]["primitives"][0]
    skin = horse.doc["skins"][0]

    def raw(index, width):
        a = horse.doc["accessors"][index]
        b = horse.doc["bufferViews"][a["bufferView"]]
        dtype = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[a["componentType"]]
        return np.frombuffer(horse.bin, dtype, a["count"] * width,
                             b.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(-1, width)

    attr = mesh["attributes"]
    rest = raw(attr["POSITION"], 3)
    joints, weights = raw(attr["JOINTS_0"], 4), raw(attr["WEIGHTS_0"], 4)
    inverse = raw(skin["inverseBindMatrices"], 16).reshape(-1, 4, 4).transpose(0, 2, 1)
    bind = np.linalg.inv(inverse)
    nodes = skin["joints"]
    names = [horse.nodes[n]["name"].lower() for n in nodes]
    ref = {k.lower(): v for k, v in samples["bind"].items()}
    ue_bind = np.array([ref[n] for n in names])
    p = ue_bind[:, :3]
    q = bind[:, :3, 3]
    u, _, vt = np.linalg.svd((p-p.mean(0)).T @ (q-q.mean(0)))
    axes = u @ vt
    scale = np.sum((p-p.mean(0)) @ axes * (q-q.mean(0))) / np.sum((p-p.mean(0))**2)
    to_source = lambda pts: (pts-p.mean(0)) @ axes * scale + q.mean(0)
    bind_error = np.linalg.norm(to_source(p)-q, axis=1).max()
    if bind_error > .015:
        raise ValueError(f"Source/UE bind registration differs by {bind_error:.4f} m")

    count = len(samples["after"])
    _, native = horse.sample(horse.clips["canter_loop"], np.linspace(0, 1, count))
    def deformation(label):
        if label == "source":
            rotation = np.stack([horse.world_rot(n, native, count).as_matrix() for n in nodes], axis=1)
            location = np.stack([horse.world_pos(n, native, count) for n in nodes], axis=1)
            return rotation @ inverse[None, :, :3, :3], location
        poses = [{k.lower(): v for k, v in frame.items()} for frame in samples[label]]
        data = np.array([[frame[n] for n in names] for frame in poses])
        posed = Rotation.from_quat(data[:, :, 3:].reshape(-1, 4)).as_matrix().reshape(count,-1,3,3)
        delta = posed @ Rotation.from_quat(ue_bind[:, 3:]).as_matrix().transpose(0,2,1)
        return axes.T @ delta @ axes, to_source(data[:,:,:3])

    collection = {}
    soles = {}
    for n in ("toe_r", "finger_r", "toe_l", "finger_l"):
        weighted = np.sum((joints == names.index(n)) * weights, axis=1) > .65
        soles[n] = np.flatnonzero(weighted & (rest[:,1] < rest[weighted,1].min()+.018))
    for label in ("source", "before", "after"):
        delta, locations = deformation(label)
        verts = np.zeros((count,len(rest),3), np.float32)
        for j in range(len(nodes)):
            w = ((joints == j) * weights).sum(1)
            ids = np.flatnonzero(w > 0)
            verts[:,ids] += (np.einsum("fij,vj->fvi",delta[:,j],rest[ids]-q[j])+locations[:,j,None])*w[ids,None]
        collection[label] = verts
    return collection, soles, raw(mesh["indices"],1).reshape(-1,3), raw(attr["TEXCOORD_0"],2)


@njit
def draw_mesh(canvas, vertices, tris, uv, tex):
    h,w,_ = canvas.shape
    depth = np.full((h,w), -1.e9)
    for tri in tris:
        a,b,c = vertices[tri[0]],vertices[tri[1]],vertices[tri[2]]
        dx1,dy1=b[0]-a[0],b[1]-a[1]
        dx2,dy2=c[0]-a[0],c[1]-a[1]
        det=dx1*dy2-dx2*dy1
        if abs(det)<.01:
            continue
        # Screen-space axes are orthogonal and equally scaled, including depth.
        nx=dy1*(c[2]-a[2])-dy2*(b[2]-a[2])
        ny=dx2*(b[2]-a[2])-dx1*(c[2]-a[2])
        sign=1 if det>=0 else -1
        light=.76+.31*max(0.,sign*(-.28*nx-.78*ny+.51*det)/np.sqrt(nx*nx+ny*ny+det*det))
        for y in range(max(0,int(np.floor(min(a[1],b[1],c[1])))),min(h,int(max(a[1],b[1],c[1]))+1)):
            for x in range(max(0,int(np.floor(min(a[0],b[0],c[0])))),min(w,int(max(a[0],b[0],c[0]))+1)):
                px,py=x+.5-a[0],y+.5-a[1]
                v=(px*dy2-py*dx2)/det
                t=(dx1*py-dy1*px)/det
                s=1.-v-t
                if min(s,v,t)<0:
                    continue
                z=s*a[2]+v*b[2]+t*c[2]
                if z<=depth[y,x]:
                    continue
                depth[y,x]=z
                uu=(s*uv[tri[0],0]+v*uv[tri[1],0]+t*uv[tri[2],0])%1.
                vv=(s*uv[tri[0],1]+v*uv[tri[1],1]+t*uv[tri[2],1])%1.
                rgb=tex[int(vv*tex.shape[0]),int(uu*tex.shape[1])]
                for k in range(3):
                    canvas[y,x,k]=min(255,rgb[k]*light)
    return canvas


def main():
    args=argparse.ArgumentParser()
    args.add_argument("poses",type=Path)
    args.add_argument("output",type=Path)
    args.add_argument("--rate-base",type=float,default=6.6)
    opt=args.parse_args()
    data=json.loads(opt.poses.read_text())
    horse=Horse((SOURCE/"Originals/WarhorseLite.glb").read_bytes())
    verts, soles, tris, uv=skin_frames(horse,data)
    period=data["period"]
    vel={"source":5.05,"before":11.6,"after":11.6}
    rate={"source":1., "before":2., "after":11.6/opt.rate_base}
    measures={}
    for label,frames in verts.items():
        spans={}
        for hoof,plant in zip(soles,[1,6,7,11]):
            # Same two source-frame interval in the middle of each planted stance.
            i=4*plant+3; j=i+8
            track=frames[:,soles[hoof]].mean(1)
            dt=(j-i)*period/80/rate[label]
            spans[hoof]=round(float(((track[j,2]-track[i,2])+vel[label]*dt)*100),2)
        measures[label]=spans
    opt.output.mkdir(parents=True,exist_ok=True)
    (opt.output/"hoof-slip.json").write_text(json.dumps(measures,indent=2))
    print(measures,flush=True)
    texture=np.array(Image.open(SOURCE/"Exchange/Warhorse_BaseColor.png").convert("RGB").resize((1024,1024)))
    w,h=370,278
    font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",16)
    small=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",13)
    title=ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc",22)
    look=np.deg2rad(13)
    elev=np.deg2rad(6)
    def project(points):
        x,y,z=points.T
        side=np.sin(look)*z+np.cos(look)*x
        screen_z=z*np.cos(look)-x*np.sin(look)
        return np.stack((w*.48+screen_z*100,241-(y*np.cos(elev)-side*np.sin(elev))*100,
                         (side*np.cos(elev)+y*np.sin(elev))*100),axis=1)
    labels=[("source","作者原始跑步","Warhorse Lite · 原始节奏"),("before","调整前","骑乘极速 · 旧支撑时序"),("after","调整后","骑乘极速 · 新支撑时序")]
    images=[]
    # Four original strides, eight before and just over seven fitted strides.
    for frame in range(80):
        time=frame/30.
        image=Image.new("RGB",(3*w+4,h+66),(32,37,37))
        header=ImageDraw.Draw(image)
        header.text((16,7),"战马跑步  /  落蹄与回摆对照",font=title,fill="#faf6ea")
        header.text((17,38),"同一模型、材质与机位    |    地面刻线间隔 0.5 米    |    后两栏均以 11.6 米/秒前进",font=small,fill="#d2d2c4")
        for col,(label,name,sub) in enumerate(labels):
            panel=Image.new("RGB",(w,h),(217,220,211))
            d=ImageDraw.Draw(panel)
            d.rectangle((0,210,w,h),fill=(196,185,164))
            d.line((0,242,w,242),fill=(132,121,105))
            for k in range(-6,7):
                offset=k*.5-(time*vel[label])%.5
                x=int(w*.48+offset*100*np.cos(look))
                d.line((x,243,x-3,251), fill=(148,137,119),width=2)
            ix=(time*rate[label]/period%1)*80
            i=int(ix)
            geom=verts[label][i]*(1-(ix-i))+verts[label][i+1]*(ix-i)
            panel=Image.fromarray(draw_mesh(np.array(panel),project(geom),tris,uv,texture))
            d=ImageDraw.Draw(panel)
            d.text((12,5),name,font=font,fill="#192d29")
            d.text((12,28),sub,font=small,fill="#42544e")
            image.paste(panel,(col*(w+2),66))
        images.append(image)
    # One shared palette keeps the coat and the grid stable between frames.
    palette=images[0].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    seq=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in images]
    seq[0].save(opt.output/"warhorse-canter.gif",save_all=True,append_images=seq[1:],loop=0,
                duration=[10*(round((i+1)*100/30)-round(i*100/30)) for i in range(len(seq))],
                disposal=1,optimize=False)


if __name__ == "__main__":
    main()
