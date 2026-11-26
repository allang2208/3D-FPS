"""Measure the two head-attached helmets against the skinned, refitted collar and straps.

The neck poses are explicit reference-rig rotations; results are not gameplay captures.
BVH bounds prune triangle pairs. The remaining triangles use segment/face, vertex/face
and edge/edge tests to include contacts between triangle interiors.
"""
import argparse
import hashlib
import heapq
import json
from pathlib import Path

import numpy as np
from numba import njit
from scipy.spatial.transform import Rotation

from helmet_nape_review import REVIEW, REVISIONS, SET, read, torso


@njit
def point_edge(p,a,b):
    v=b-a
    t=min(1.,max(0.,np.dot(p-a,v)/max(np.dot(v,v),1.e-24)))
    diff=p-a-t*v
    return np.dot(diff,diff)


@njit
def in_face(p,a,b,c,n):
    return (np.dot(np.cross(b-a,p-a),n)>=-1.e-12 and
            np.dot(np.cross(c-b,p-b),n)>=-1.e-12 and
            np.dot(np.cross(a-c,p-c),n)>=-1.e-12)


@njit
def point_face(p,tri,n,nn):
    a,b,c=tri
    if nn>1.e-24:
        h=np.dot(p-a,n)
        if in_face(p-(h/nn)*n,a,b,c,n):
            return h*h/nn
    return min(point_edge(p,a,b),point_edge(p,b,c),point_edge(p,c,a))


@njit
def crosses(p,q,tri,n,nn):
    if nn<1.e-24:
        return False
    sp=np.dot(p-tri[0],n)
    sq=np.dot(q-tri[0],n)
    if sp*sq>0. or abs(sp-sq)<1.e-18:
        return False
    return in_face(p+(q-p)*(sp/(sp-sq)),tri[0],tri[1],tri[2],n)


@njit
def segments(p,q,a,b):
    d=q-p
    e=b-a
    w=p-a
    aa=np.dot(d,d)
    bb=np.dot(e,e)
    if aa<1.e-24:
        return point_edge(p,a,b)
    if bb<1.e-24:
        return point_edge(a,p,q)
    de=np.dot(d,e)
    dw=np.dot(d,w)
    ew=np.dot(e,w)
    det=aa*bb-de*de
    s=min(1.,max(0.,(de*ew-bb*dw)/det)) if det>1.e-24 else 0.
    t=(de*s+ew)/bb
    if t<0.:
        t=0.
        s=min(1.,max(0.,-dw/aa))
    elif t>1.:
        t=1.
        s=min(1.,max(0.,(de-dw)/aa))
    diff=w+s*d-t*e
    return np.dot(diff,diff)


@njit
def triangle_distance(a,b):
    na=np.cross(a[1]-a[0],a[2]-a[0])
    nb=np.cross(b[1]-b[0],b[2]-b[0])
    aa=np.dot(na,na)
    bb=np.dot(nb,nb)
    best=1.e10
    for i in range(3):
        j=(i+1)%3
        if crosses(a[i],a[j],b,nb,bb) or crosses(b[i],b[j],a,na,aa):
            return 0.
        best=min(best,point_face(a[i],b,nb,bb),point_face(b[i],a,na,aa))
        for k in range(3):
            best=min(best,segments(a[i],a[j],b[k],b[(k+1)%3]))
    return best


@njit
def lower(a,b):
    total=0.
    for i in range(3):
        d=max(0.,a[i]-b[i+3],b[i]-a[i+3])
        total+=d*d
    return total


class Tree:
    def __init__(self,points,faces):
        centers=points[faces].mean(axis=1)
        nodes=[]
        order=[]
        def split(ids):
            node=len(nodes)
            nodes.append(None)
            if len(ids)<=7:
                start=len(order)
                order.extend(ids)
                nodes[node]=(-1,-1,start,len(order))
            else:
                mid=len(ids)//2
                c=centers[ids]
                axis=np.ptp(c,axis=0).argmax()
                ids=ids[np.argpartition(c[:,axis],mid)]
                nodes[node]=(split(ids[:mid]),split(ids[mid:]),0,0)
            return node
        split(np.arange(len(faces)))
        self.nodes=np.array(nodes)
        self.faces=faces[order]
        self.order=np.asarray(order)


@njit
def bounds(nodes,tris):
    result=np.empty((len(nodes),6))
    for i in range(len(nodes)-1,-1,-1):
        left,right,start,end=nodes[i]
        if left>=0:
            for k in range(3):
                result[i,k]=min(result[left,k],result[right,k])
                result[i,3+k]=max(result[left,3+k],result[right,3+k])
        else:
            for k in range(3):
                result[i,k]=np.min(tris[start:end,:,k])
                result[i,3+k]=np.max(tris[start:end,:,k])
    return result


@njit
def nearest(na,ba,ta,nb,bb,tb):
    queue=[(0.,0,0)]
    best=1.e10
    hit_a=hit_b=-1
    while queue:
        estimate,i,j=heapq.heappop(queue)
        if estimate>=best:
            break
        al,ar,astart,aend=na[i]
        bl,br,bstart,bend=nb[j]
        if al<0 and bl<0:
            for ia in range(astart,aend):
                for ib in range(bstart,bend):
                    d=triangle_distance(ta[ia],tb[ib])
                    if d<best:
                        best=d
                        hit_a,hit_b=ia,ib
                        if d<=1.e-18:
                            return 0.,hit_a,hit_b
            continue
        expand_a=bl<0 or (al>=0 and np.sum(ba[i,3:]-ba[i,:3])>=np.sum(bb[j,3:]-bb[j,:3]))
        for k in range(2):
            ai=(al if k==0 else ar) if expand_a else i
            bj=j if expand_a else (bl if k==0 else br)
            d=lower(ba[ai],bb[bj])
            if d<best:
                heapq.heappush(queue,(d,ai,bj))
    return np.sqrt(best),hit_a,hit_b


def pose_chain(garment,pitch,yaw):
    initial=np.eye(3)
    offset=np.zeros(3)
    transforms=[]
    bones={b["name"]:b for b in garment["bones"]}
    for name,share in (("neck_01",.35),("neck_02",.35),("head",.30)):
        point=np.array(bones[name]["position"])
        turn=Rotation.from_euler("z",yaw*share,degrees=True).as_matrix()
        lift=Rotation.from_euler("x",pitch*share,degrees=True).as_matrix()
        delta=turn@lift
        offset=initial@(point-delta@point)+offset
        initial=initial@delta
        transforms.append((initial,offset))
    return transforms


def neck_weights(garment):
    classes={}
    for bone in garment["bones"]:
        classes[bone["index"]]={"neck_01":0,"neck_02":1,"head":2}.get(bone["name"],classes.get(bone["parent"],-1))
    w=np.zeros((len(garment["positions"]),3))
    for i,row in enumerate(garment["weights"]):
        for bone,weight in row:
            group=classes[bone]
            if group>=0:
                w[i,group]+=weight
    return w


def audit(rig,rev):
    garment=torso(rig)
    hp_file=SET/REVISIONS[rev]/"Authored"/f"helmet_{rig}_world.json"
    helmet=read(hp_file)
    hp=np.array(helmet["positions"])
    gp=garment["positions"].astype(float)
    gf=np.asarray(garment["triangles"])
    gm=np.asarray(garment["triangle_materials"])
    keep=np.array([not name.startswith("NATIVE:") for name in garment["material_slots"]])[gm]
    gf,gm=gf[keep],gm[keep]
    hf=np.asarray(helmet["triangles"])
    hm=np.asarray(helmet["triangle_materials"])
    trees={}
    for label,mask in (("shell",hm==helmet["material_slots"].index("H1_Composite")),("complete",np.ones(len(hm),bool))):
        trees[label]=(Tree(hp,hf[mask]),hm[mask])
    gt=Tree(gp,gf)
    weights=neck_weights(garment)
    records=[]
    for pitch,yaw in [(0,0),(0,-45),(0,45),(0,-60),(0,60),(15,0),(30,0),(40,0),(25,-45),(25,45)]:
        transforms=pose_chain(garment,pitch,yaw)
        cloth=gp.copy()
        for index,(rot,offset) in enumerate(transforms):
            ids=np.flatnonzero(weights[:,index]>0)
            cloth[ids]+=weights[ids,index,None]*(gp[ids]@rot.T+offset-gp[ids])
        cranial_rot,cranial_offset=transforms[-1]
        gear=hp@cranial_rot.T+cranial_offset
        body_tris=cloth[gt.faces]
        body_box=bounds(gt.nodes,body_tris)
        row=dict(pitch_deg=pitch,yaw_deg=yaw)
        for key,(ht,mats) in trees.items():
            tris=gear[ht.faces]
            box=bounds(ht.nodes,tris)
            clearance,ia,ib=nearest(ht.nodes,box,tris,gt.nodes,body_box,body_tris)
            row[key]=dict(clearance_cm=round(float(clearance),4),touching=clearance<1.e-8,
                          helmet_material=helmet["material_slots"][mats[ht.order[ia]]],
                          garment_material=garment["material_slots"][gm[gt.order[ib]]])
        print(rig,rev,pitch,yaw,row["shell"]["clearance_cm"],row["complete"]["clearance_cm"],flush=True)
        records.append(row)
    REVIEW.mkdir(parents=True,exist_ok=True)
    (REVIEW/f"{rig}-{rev}-motion.json").write_text(json.dumps(dict(
        rig=rig,rev=rev,helmet_source_sha256=hashlib.sha256(hp_file.read_bytes()).hexdigest(),
        measurement="minimum triangle-to-triangle Euclidean surface distance in cm; 0 includes touching or overlap",
        geometry="authored helmet in native head/body coordinates and refitted TS01 shirt/carrier with real skin weights, including thread, excluding skin sections",
        simulation="synthetic extension about body X and yaw about body Z distributed in proportions 35/35/30 across neck_01, neck_02 and head; helmet moves with head; torso stationary; no dynamic cloth or in-game animation",
        samples=records),indent=2),encoding="utf8")


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("rev",choices=REVISIONS)
    args.add_argument("rig",nargs="*",default=["Jason","Kaitlin"])
    args=args.parse_args()
    for rig in args.rig:
        audit(rig,args.rev)
