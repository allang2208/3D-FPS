"""Make a smooth upper, body-facing recess for the nape on confirmed TS01 pack contacts."""
from pathlib import Path
import hashlib
import json
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
SET=ROOT/"SourceAssets/ModernTacticalSet20261113"
OLD=ROOT/"SourceAssets/BackpackFit20261024/ModernTacticalShoulders20261118"
OUT=OLD.with_name("ModernTacticalHelmetPacks20261118")
TILT=np.array([0.,.68,.733212]); TILT/=np.linalg.norm(TILT)
UP=np.array([0.,-TILT[2],TILT[1]])
X=np.array([1.,0.,0.])
ANGLES=[(0,0),(45,0),(-45,0),(0,20),(35,15),(-35,15)]


def read(path):
    return json.loads(path.read_bytes())


def write(name,record):
    (OUT/name).write_text(json.dumps(record,indent=2),encoding="utf8")


def points(path):
    return np.fromfile(path,dtype="<f4").reshape(-1,3).astype(float)


def tree(p,f):
    return BVHTree.FromPolygons(p.tolist(),f.tolist(),all_triangles=True)


def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)


def shells(rig):
    h=read(SET/"HelmetNapeR3/Authored"/f"helmet_{rig}_world.json")
    p=np.asarray(h["positions"])
    f=np.asarray(h["triangles"])[np.asarray(h["triangle_materials"])==h["material_slots"].index("H1_Composite")]
    idx,faces=np.unique(f,return_inverse=True);p=p[idx];faces=faces.reshape(-1,3)
    bones=read(SET/"HelmetHairFitR1/Inputs"/f"{rig}_Body.json")["bones"]
    poses={}
    for yaw,pitch in ANGLES:
        for chain in ("pivot","chain"):
            mat=np.eye(3);offset=np.zeros(3)
            for name,weight in ([("head",1.)] if chain=="pivot" else [("neck_01",.35),("neck_02",.35),("head",.30)]):
                pivot=np.array(bones[name]["position"])
                delta=np.asarray(Matrix.Rotation(np.radians(yaw*weight),3,"Z")@Matrix.Rotation(np.radians(pitch*weight),3,"X"))
                offset+=mat@(pivot-delta@pivot);mat=mat@delta
            live=p@mat.T+offset
            key=f"{chain}_yaw{yaw}_pitch{pitch}"
            poses[key]=(tree(live,faces),live)
    return poses


def dilation(a,r):
    padded=np.pad(a,r,mode="edge")
    return np.maximum.reduce([padded[i:i+a.shape[0],j:j+a.shape[1]] for i in range(2*r+1) for j in range(2*r+1)])


def blur(a,passes):
    for _ in range(passes):
        p=np.pad(a,1,mode="edge")
        a=(p[1:-1,:-2]+p[1:-1,2:]+p[:-2,1:-1]+p[2:,1:-1]+4*a)/8
    return a


def cast(surfaces,start,direction,choose):
    hits=[]
    for surf in surfaces:
        point=surf.ray_cast(Vector(start),Vector(direction),390.)[0]
        if point is not None:
            hits.append(np.dot(point,TILT))
    return choose(hits) if hits else np.nan


def silhouette(poses):
    p=np.vstack([v for _,v in poses.values()])
    xs=np.arange(np.floor(p[:,0].min())-5,np.ceil(p[:,0].max())+5,.5)
    vs=np.arange(np.floor((p@UP).min())-5,np.ceil((p@UP).max())+5,.5)
    heights=np.full((len(xs),len(vs)),np.nan)
    trees=[v[0] for v in poses.values()]
    for i,x in enumerate(xs):
        for j,v in enumerate(vs):
            heights[i,j]=cast(trees,x*X+v*UP-90*TILT,TILT,min)
    return xs,vs,heights


def make_field(envelope,meshes,anchor_height,shell_low):
    xs,vs,shell=envelope
    trees=[tree(p,f) for p,f in meshes]
    amount=np.zeros_like(shell)
    for i,j in zip(*np.where(np.isfinite(shell))):
        high=cast(trees,xs[i]*X+vs[j]*UP+260*TILT,-TILT,max)
        if np.isfinite(high):
            amount[i,j]=max(0.,high-shell[i,j]+.80)
    # Adjacent grid cells ease over detail seams and coarse panel triangles.
    scale=blur(dilation(amount,12),32)
    gate=np.where(np.isfinite(shell),shell,1e3)
    gate=-dilation(-gate,15)
    gate=np.minimum(gate,200)
    def sample(grid,p):
        x=np.clip((p[:,0]-xs[0])/.5,0,len(xs)-1.001)
        v=np.clip((p@UP-vs[0])/.5,0,len(vs)-1.001)
        i,j=x.astype(int),v.astype(int);x-=i;v-=j
        return grid[i,j]*(1-x)*(1-v)+grid[i+1,j]*x*(1-v)+grid[i,j+1]*(1-x)*v+grid[i+1,j+1]*x*v
    def warp(p,gain):
        delta=sample(scale,p)*gain
        start=np.maximum(sample(gate,p)-16.,(anchor_height-(p@UP)*UP[2])/TILT[2])
        room=.78*np.maximum(0.,p@TILT-start)
        # A monotone compression along each oblique ray preserves the layer
        # order, even at the transition into an unchanged shoulder anchor.
        displace=np.maximum(0.,.5*(delta+room-np.sqrt((delta-room)**2+.12)))
        # Restrict the scallop to upper, back-facing cargo. The strap coupling
        # point under the bag is retained along with the chest-facing harness.
        return p-displace[:,None]*TILT
    return warp


def contacts(meshes,poses):
    trees=[tree(p,f) for p,f in meshes]
    return {name:sum(len(pack.overlap(shell)) for pack in trees) for name,(shell,_) in poses.items()}


def main():
    out=OUT/"Authored";out.mkdir(parents=True,exist_ok=True)
    old=read(OLD/"authored.json");source=read(OLD/"captured.json")
    statics={row["asset"]:row for row in old["statics"]}
    rows=[];hard=[];routes=[];report={}
    def faces(donor):
        return np.fromfile(Path(source[donor]["folder"])/"triangles.bin",dtype="<i4").reshape(-1,3)
    def save_change(record,new_points):
        asset=record["asset"].replace(OLD.name,OUT.name)
        path=out/(asset.split("/")[-1]+".bin");new_points.astype("<f4").tofile(path)
        return dict(source=record["source"],source_sha256=record["source_sha256"],asset=asset,positions=str(path),vertices=len(new_points))
    for rig in ("Jason","Kaitlin"):
        poses=shells(rig);envelope=silhouette(poses);report[rig]={}
        for row in old["rows"]:
            if row["rig"]!=rig:
                continue
            key=row["item"];mesh=points(row["positions"]);components=[(mesh,faces(row["source"]))]
            rigid=statics.get(row.get("rigid_mesh","").split(".")[0])
            if rigid:
                x,y,z,w=row["rigid_rotation_quat"];rotation=np.asarray(Quaternion((w,x,y,z)).to_matrix())
                origin=np.asarray(row["rigid_location"])
                components.append((points(rigid["positions"])@rotation.T+origin,faces(rigid["source"])))
            elif "rigid_mesh" in row:
                loc=row["rigid_location"];x,y,z,w=row["rigid_rotation_quat"];rot=np.asarray(Quaternion((w,x,y,z)).to_matrix())
                base=Path(source[row["rigid_mesh"]]["folder"])
                components.append((points(base/"positions.bin")@rot.T+loc,faces(row["rigid_mesh"])))
            before=contacts(components,poses)
            state=dict(before=before,after=before.copy(),changes=[])
            report[rig][key]=state
            if not any(before.values()):
                continue
            shell_low=min(live[:,2].min() for _,live in poses.values())
            if rigid:
                anchor_height=float(mesh[:,2].max())+.08
            else:
                weights=np.fromfile(Path(source[row["source"]]["folder"])/"mask.bin",dtype="<f4")
                anchor_height=float(mesh[weights<.02,2].max())+.08
            warp=make_field(envelope,components,anchor_height,shell_low)
            for gain in (1.,1.18,1.4,1.7):
                candidate=[(warp(p,gain),f) for p,f in components]
                after=contacts(candidate,poses)
                if not any(after.values()):break
            if any(after.values()):
                raise RuntimeError(f"Unresolved nape contour on {rig}/{key}: {after}")
            state.update(after=after,envelope_gain=gain)
            route=dict(rig=rig,item=key,shirt=row["shirt"],expected_mesh=row["asset"],expected_rigid=row.get("rigid_mesh"))
            for i,((p,f),(q,_)) in enumerate(zip(components,candidate)):
                dist=np.linalg.norm(q-p,axis=1)
                moved=dist>.002
                if not moved.any():continue
                state["changes"].append(dict(part="harness_or_soft_pack" if i==0 else "rigid_cargo",changed_points=int(moved.sum()),total_points=len(p),peak_cm=float(dist.max()),changed_z_min=float(p[moved,2].min())))
                if i==0:
                    sk=save_change(row,q);rows.append(sk);route["mesh"]=sk["asset"]
                else:
                    if not rigid:raise RuntimeError("Unexpected sling contact")
                    obj=save_change(rigid,(q-origin)@rotation);hard.append(obj);route["rigid"]=obj["asset"]
            route["before_support"]=row.get("support")
            if route["before_support"] and rigid:
                q=candidate[-1][0]; route["after_support"]={**row["support"],"bounds_min":q.min(0).tolist(),"bounds_max":q.max(0).tolist()}
            all_points=np.vstack([p for p,f in candidate])
            route["bounds_min"]=all_points.min(0).tolist();route["bounds_max"]=all_points.max(0).tolist()
            routes.append(route)
            print(rig,key,state["changes"],flush=True)
    write("authored.json",dict(revision=OUT.name,rows=rows,statics=hard))
    write("routes.json",routes);write("nape-contact.json",dict(poses=ANGLES,methods=["head pivot","neck_01/neck_02/head distributed 35/35/30"],rows=report))
    (OUT/"helmet-sha256.json").write_text(json.dumps({rig:hashlib.sha256((SET/"HelmetNapeR3/Authored"/f"helmet_{rig}_world.json").read_bytes()).hexdigest() for rig in report},indent=2))
    print("Authored",len(rows),"skeletal meshes and",len(hard),"static cargo meshes",flush=True)


if __name__=="__main__":
    main()
