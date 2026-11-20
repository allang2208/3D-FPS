"""Register a single undistorted product view against the supplied photograph."""
import json
from pathlib import Path

import cv2
import numpy as np
from numba import njit
from scipy.optimize import least_squares

P=Path(__file__).resolve().parents[2]
ROOT=P/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4"


@njit
def paint(q,faces,w,h):
    out=np.zeros((h,w),np.uint8)
    for face in faces:
        a,b,c=q[face[0]],q[face[1]],q[face[2]]
        xmin=max(0,int(np.floor(min(a[0],b[0],c[0]))));xmax=min(w-1,int(np.ceil(max(a[0],b[0],c[0]))))
        ymin=max(0,int(np.floor(min(a[1],b[1],c[1]))));ymax=min(h-1,int(np.ceil(max(a[1],b[1],c[1]))))
        area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if abs(area)<1.e-7:
            continue
        for j in range(ymin,ymax+1):
            for i in range(xmin,xmax+1):
                if out[j,i]:
                    continue
                x=i+.5-a[0];y=j+.5-a[1]
                s=(x*(c[1]-a[1])-y*(c[0]-a[0]))/area
                t=((b[0]-a[0])*y-(b[1]-a[1])*x)/area
                if s>=0 and t>=0 and s+t<=1:
                    out[j,i]=1
    return out


def photo_mask():
    rgb=cv2.cvtColor(cv2.imread(str(ROOT/"Reference/user-angle-crop.png")),cv2.COLOR_BGR2RGB).astype(int)
    mask=(rgb[:,:,0]-rgb[:,:,2]>6).astype(np.uint8)
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    n,ids,stats,_=cv2.connectedComponentsWithStats(mask)
    keep=np.flatnonzero(stats[1:,cv2.CC_STAT_AREA]>50)+1
    return np.isin(ids,keep).astype(np.uint8)


def basis(yaw,elev,roll):
    a,b,r=np.radians([yaw,elev,roll])
    eye=np.array([np.sin(a)*np.cos(b),np.cos(a)*np.cos(b),np.sin(b)])
    right=np.array([np.cos(a),-np.sin(a),0])
    up=np.cross(right,eye)
    x=right*np.cos(r)+up*np.sin(r);y=up*np.cos(r)-right*np.sin(r)
    return x,y,eye


# Source-pixel coordinates in the unscaled 354 x 372 user photograph.
# Fasteners and ledges are anchored to the same named objects in the source mesh.
LANDMARKS={
    "EXFIL_Shroud_black_captive_0":(276,48),
    "EXFIL_Shroud_black_captive_1":(239,104),
    "EXFIL_Shroud_black_captive_2":(330,102),
    "EXFIL_Shroud_upper_ledge":(286,61),
    "EXFIL_Shroud_lower_ledge":(301,127),
    "EXFIL_Shroud_insert_rounded_tab":(287,79),
    "EXFIL_Rail2_fastener_R0":(39,143),
    "EXFIL_Rail2_fastener_R1":(71,145),
    "EXFIL_Rail2_fastener_R2":(15,206),
    "EXFIL_Rail2_front_bezel_R":(134,144),
    "EXFIL_EXFIL_BALLISTIC_badge_face_R":(72,80),
}


def main():
    data=json.loads((ROOT/"Authored/helmet_Jason_world.json").read_bytes())
    parts=json.loads((ROOT/"Authored/parts-Jason-GAME.json").read_bytes())["parts"]
    p=np.array(data["positions"]);origin=(p.max(0)+p.min(0))/2;p-=origin
    faces=np.asarray(data["triangles"],np.int32)
    if len(faces)!=sum(parts.values()):
        raise ValueError("The authored triangle and part tables must have matching row counts")
    cursor=0;world={};shell=[]
    for name,count in parts.items():
        if name in LANDMARKS or name in ("Outer_Shell_Continuous_Mould","Crown_Loop_Attachment"):
            points=p[np.unique(faces[cursor:cursor+count])]
            if name in LANDMARKS:
                world[name]=points.mean(0)
            else:
                shell.append(points)
        cursor+=count
    xyz=np.array([world[n] for n in LANDMARKS]);photo=np.array(list(LANDMARKS.values()))
    shell=np.concatenate(shell)
    def project(args,points):
        yaw,elev,roll,scale,tx,ty=args
        x,y,_eye=basis(yaw,elev,roll)
        return points@np.array([x,-y]).T*scale+[tx,ty]
    def residual(args):
        err=project(args,xyz)-photo
        # The four hard-surface silhouette limits stabilize the framing. The chin
        # sling hangs differently in the photograph and does not anchor the pose.
        hull=project(args,shell)
        edges=np.r_[hull[:,0].min()-8,hull[:,0].max()-347,hull[:,1].min()-12]
        return np.r_[err.ravel(),edges*1.25]
    res=least_squares(residual,[-46,-3,1,14.,177,183],
                      bounds=([-72,-25,-12,10.,140,150],[-21,20,12,18.5,225,226]),
                      loss="soft_l1",f_scale=6.)
    yaw,elev,roll,s,tx,ty=res.x
    x,y,eye=basis(yaw,elev,roll)
    ref=photo_mask();h,w=ref.shape
    center=origin+x*((w*.5-tx)/s)-y*((h*.5-ty)/s)
    silhouette=paint(project(res.x,p),faces,w,h)>0
    source=ref>0
    record=dict(parameters=list(map(float,res.x)),center=center.tolist(),right=x.tolist(),up=y.tolist(),eye=eye.tolist(),
        vertical_cm=float(h/s),pixel_size=[w,h],silhouette_iou=float((source&silhouette).sum()/(source|silhouette).sum()),
        landmarks_px={name:dict(photo=value,model=point.round(1).tolist()) for (name,value),point in zip(LANDMARKS.items(),project(res.x,xyz))},
        source="Unwarped orthographic fit to 11 shroud, rail and badge anchors and three external shell limits on the user photograph.")
    (ROOT/"Review").mkdir(exist_ok=True)
    (ROOT/"Review/product-camera.json").write_text(json.dumps(record,indent=2))
    print(record,flush=True)


if __name__=="__main__":
    main()
