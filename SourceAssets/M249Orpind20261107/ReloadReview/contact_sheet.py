"""Draw the same isolated mesh surfaces before and after the contact fit."""
import pickle
from pathlib import Path
import numpy as np
from numba import njit
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation

here = Path(__file__).resolve().parent
folder = here.parents[2] / "Saved/M249ReloadReview"
def load(p):
    with p.open("rb") as handle:
        return pickle.load(handle)

def matrices(a):
    a = np.array(a)
    m = np.tile(np.eye(4),(len(a),1,1))
    m[:,:3,:3] = Rotation.from_quat(a[:,3:7]).as_matrix() * a[:,None,7:]
    m[:,:3,3] = a[:,:3]
    return m

d = load(folder/"geometry.pkl")
v = np.array(d["vertices"])
f = np.array(d["faces"])
slots = np.array(d["sections"])
names = d["names"]
lookup = dict(zip(d["used"],range(len(names))))
weights = d["weights"]
dominant = np.array([names[lookup[max(row,key=lambda w:w[1])[0]]] for row in weights])
mask = np.isin(slots,[i for i,n in enumerate(d["slots"]) if n.endswith("__NewBelt")])
mask |= (slots == d["slots"].index("Skin_Hand")) & np.char.endswith(dominant[f[:,0]],"_r")
ids, tris = np.unique(f[mask],return_inverse=True)
tris = tris.reshape(-1,3)
colors = np.where((slots[mask] == d["slots"].index("Skin_Hand"))[:,None],
                  [190, 159, 132], [64, 183, 205])
indices = {}
for i,vi in enumerate(ids):
    for b,w in weights[vi]:
        indices.setdefault(lookup[b],[]).append((i,w))
rest = np.linalg.inv(matrices(d["bind"]))
right = np.array([1., .16, 0.])
right /= np.linalg.norm(right)
up = np.array([.04, -.25, 1.])
up -= right*(up@right)
up /= np.linalg.norm(up)
view = np.stack((right,up,np.cross(right,up)))

def pose(path):
    times,rows = load(path)
    i = np.argmin(np.abs(np.asarray(times)-4.70))
    bones = matrices(rows[i]) @ rest
    bones = np.linalg.inv(bones[names.index("WPN_root")]) @ bones
    points = np.zeros((len(ids),3))
    for b,pairs in indices.items():
        idx,weight = np.asarray(pairs).T
        idx = idx.astype(int)
        points[idx] += (v[ids[idx]]@bones[b,:3,:3].T+bones[b,:3,3])*weight[:,None]
    return points @ view.T

@njit
def raster(points, tris, colors, width, height):
    depth = np.full((height,width),-np.inf)
    pix = np.empty((height,width,3),np.uint8)
    pix[:] = np.array([23,30,37],np.uint8)
    for i,t in enumerate(tris):
        a,b,c = points[t[0]],points[t[1]],points[t[2]]
        u,v = b-a,c-a
        normal = np.cross(u,v)
        size = np.linalg.norm(normal)
        det = normal[2]
        if abs(det)<1e-9 or size<1e-9:continue
        normal /= size
        if normal[2]<0:normal *= -1
        light = .57 + .43*max(0.,-.4*normal[0]-.56*normal[1]+.72*normal[2])
        for y in range(max(0,int(np.floor(min(a[1],b[1],c[1])))),min(height,int(np.ceil(max(a[1],b[1],c[1])))+1)):
            for x in range(max(0,int(np.floor(min(a[0],b[0],c[0])))),min(width,int(np.ceil(max(a[0],b[0],c[0])))+1)):
                rx,ry = x+.5-a[0],y+.5-a[1]
                s,h = (rx*v[1]-ry*v[0])/det,(ry*u[0]-rx*u[1])/det
                if min(s,h,1-s-h)<0:continue
                z = a[2]+s*u[2]+h*v[2]
                if z>depth[y,x]:
                    depth[y,x]=z
                    pix[y,x]=colors[i]*light
    return pix

poses = [pose(location/"reload.pkl") for location in (folder/"before",folder)]
all_points = np.concatenate(poses)
low, high = all_points.min(0), all_points.max(0)
w,h = 560,385
scale = min((w-38)/(high[0]-low[0]),(h-36)/(high[1]-low[1]))
image = Image.new("RGB",(w*2+3,h+100),(23,30,37))
draw = ImageDraw.Draw(image)
font = lambda size: ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",size)
draw.text((18,9),"普通换弹  ·  4.70 秒",font=font(25),fill=(242,244,247))
draw.text((18,48),"修正前",font=font(18),fill=(196,203,210))
draw.text((w+21,48),"修正后",font=font(18),fill=(196,203,210))
for index,p in enumerate(poses):
    verts = (p-(low+high)/2)*scale
    verts[:,0] += w/2
    verts[:,1] = -verts[:,1]+h/2
    image.paste(Image.fromarray(raster(verts,tris,colors,w,h)),(index*(w+3),75))
draw.line((w+1,49,w+1,h+63),fill=(63,72,80),width=1)
draw.text((18,h+63),"UE 已保存视模的正交投影，仅显示右手与可见弹链。",font=font(15),fill=(169,180,190))
image.save(folder/"contact_before_after.png")
