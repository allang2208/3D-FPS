"""Prepare original skinned hand geometry and a relaxed, photographic glove pose."""
import numpy as np


def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1.e-10)


def aim_vector(source,dest):
    a,b=unit(source),unit(dest)
    cross=np.cross(a,b)
    k=np.array([[0.,-cross[2],cross[1]],[cross[2],0.,-cross[0]],[-cross[1],cross[0],0.]])
    return np.eye(3)+k+k@k/(1.+np.dot(a,b))


def neutral_hand(record,side,*,relax=True,cupped=False,empty_cuff=False):
    bones={b["name"]:b for b in record["bones"]}
    ids={b["index"]:b["name"] for b in record["bones"]}
    joint=lambda n:np.asarray(bones[n+"_"+side]["position"])
    wrist=joint("hand")
    longitudinal=unit(joint("middle_01")-wrist)
    transverse=joint("pinky_01")-joint("index_01")
    transverse=unit(transverse-longitudinal*transverse.dot(longitudinal))
    up=np.cross(transverse,longitudinal)
    sign=1. if side=="l" else -1.
    basis=np.stack((-sign*transverse,longitudinal,sign*up))
    # The source UE frame is left-handed. The result is right-handed, dorsal +Z.
    origin={k:basis@(np.asarray(v['position'])-wrist) for k,v in bones.items()}
    positions=np.asarray(record["positions"])
    frames={k:(np.eye(3),o.copy()) for k,o in origin.items()}
    if relax:
        for family,fan in (("pinky",-14),("ring",-5),("middle",1),("index",8),("thumb",37)):
            parent=None
            for seg in range(1,4):
                k=f"{family}_{seg:02d}_{side}";bo=bones[k]
                start=origin[k]
                if seg<3:
                    direction=origin[f"{family}_{seg+1:02d}_{side}"]-start
                else:
                    previous=start-origin[f"{family}_02_{side}"]
                    axis=unit(basis@np.asarray(bo["axes"][0]))
                    direction=axis if axis@previous>0 else -axis
                if cupped:
                    # The product dorsal view shows lightly flexed, mutually
                    # adjacent fingers and a thumb resting beside the index.
                    fan={"pinky":4,"ring":4,"middle":2,"index":1,"thumb":21}[family]
                    flex=[6,22,38] if family=="thumb" else [14,30,43]
                else:
                    flex=[7,12,19] if family=="thumb" else [4,9,16]
                angle=np.radians(fan*sign)
                bend=np.radians(flex[seg-1])
                line=np.array([np.sin(angle)*np.cos(bend),np.cos(angle)*np.cos(bend),-np.sin(bend)])
                rot=aim_vector(direction,line)
                pivot=start if parent is None else frames[parent][1]+frames[parent][0]@(start-origin[parent])
                frames[k]=(rot,pivot)
                parent=k
    tri=np.asarray(record["triangles"],dtype=np.int32)
    # One source vertex belongs to one hand, including forearm-weighted cuff rows.
    weighted_side=[]
    for weights in record["weights"]:
        valid=sum(w for i,w in weights if ids[i].endswith("_"+side))
        foreign=sum(w for i,w in weights if ids[i].endswith("_"+("r" if side=="l" else "l")))
        weighted_side.append(valid>foreign)
    keep=np.array(weighted_side)
    face_ids=np.flatnonzero(keep[tri].all(axis=1))
    vertices,idx=np.unique(tri[face_ids].reshape(-1),return_inverse=True)
    f=idx.reshape(-1,3)
    p=(positions[vertices]-wrist)@basis.T
    trans=np.zeros((len(p),3,3));shift=np.zeros_like(p)
    groups={}
    for j,source_id in enumerate(vertices):
        pairs=record["weights"][source_id]
        total=sum(w for _,w in pairs)
        for ident,ww in pairs:
            name=ids[ident];weight=ww/total
            rot,pivot=frames[name]
            trans[j]+=rot*weight
            shift[j]+=(pivot-rot@origin[name])*weight
            groups.setdefault(name,[]).append((j,weight))
    p=np.einsum("vij,vj->vi",trans,p)+shift
    ns=np.asarray(record["normals"])[face_ids]@basis.T
    n=unit(np.einsum("fcij,fcj->fci",np.linalg.inv(trans).transpose(0,2,1)[f],ns))
    if empty_cuff:
        # The long elastic section fits *under* equipped sleeves. For the
        # empty product, ease that section back inside the closure. Keep the
        # garment's rolled lip, vertex order and artist weights intact.
        y=p[:,1].copy()
        slots=[name.rsplit("/",1)[-1].split(".")[0].removeprefix("M_") for name in record["material_slots"]]
        materials=np.asarray(record["triangle_materials"])[face_ids]
        # Preserve the closure, which extends several cm toward the elbow.
        # Only the elastic rolled return behind the rubber gets tucked.
        rubber_vertices=np.unique(f[materials==slots.index("CG_Rubber")])
        edge=float(np.min(y[rubber_vertices]))-.08
        depth=np.clip(edge-y,0,None)
        scale=1./(1.+4.5*depth)
        p[:,1]=np.where(y<edge,edge-np.log1p(4.5*depth)/4.5,y)
        taper=1.-.12*(1.-scale)
        slope=.54*scale**2*(y<edge)
        jac=np.tile(np.eye(3),(len(p),1,1))
        jac[:,0,0]=taper;jac[:,2,2]=taper;jac[:,1,1]=scale
        jac[:,0,1]=p[:,0]*slope;jac[:,2,1]=p[:,2]*slope
        p[:,0]*=taper;p[:,2]*=taper
        n=unit(np.einsum("fcij,fcj->fci",np.linalg.inv(jac).transpose(0,2,1)[f],n))
    uv=np.asarray(record["uv"])[face_ids].copy()
    uv[:,:,1]=1-uv[:,:,1]
    material=np.asarray(record["triangle_materials"])[face_ids]
    joint_data={}
    for name in groups:
        bone=bones[name]
        parent=ids.get(bone["parent"])
        while parent and parent not in groups:
            parent=ids.get(bones[parent]["parent"])
        rot,pivot=frames[name]
        axes=np.asarray(bone["axes"])@basis.T@rot.T
        joint_data[name]=(pivot,unit(axes),parent)
    return dict(p=p,f=f,n=n,uv=uv,m=material,groups=groups,joints=joint_data,
                slots=[name.rsplit("/",1)[-1].split(".")[0].removeprefix("M_") for name in record["material_slots"]])
