"""Fit the TS01 crew neck to each native head and carry the sewn layers together."""
import json
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

P = Path(__file__).resolve().parents[2]
S = P / "SourceAssets/ModernTacticalSet20261113"
R4 = S / "CombatShirtR4"
OUT = S / "ShoulderFit20261118"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(Path(__file__).parent))
from combat3_cloth import normals


def read(path):
    return json.loads(path.read_bytes())


def smooth(t):
    t = np.clip(t, 0, 1)
    return t*t*(3-2*t)


def nearest_tree(points):
    tree = KDTree(len(points))
    for i,point in enumerate(points):
        tree.insert(point,i)
    tree.balance()
    return tree


def body_tree(rig, clav):
    body = read(S / "CombatShirtR3/Inputs" / f"Body_{rig}.json")
    head = read(S / "HelmetHairFitR1/Inputs" / f"{rig}_Head.json")
    points = np.asarray(body["positions"]+head["positions"])
    faces = np.concatenate((body["triangles"],np.asarray(head["triangles"])+len(body["positions"])))
    # The exposed lower neck is part of the separate head mesh.
    z = points[faces,2]
    faces = faces[(z.min(axis=1)<clav+10) & (z.max(axis=1)>clav-18)]
    return BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)


def neck_bib_clearance(surface, faces, rig, clav, center):
    # The head includes a flared bib under the crew neck. Fit both the front
    # and rear of the garment to that visible skin, including the neck insert.
    skin = read(S/"HelmetHairFitR1/Inputs"/f"{rig}_Head.json")
    insert = read(S/"CombatShirtR3/Authored"/f"neck_skin_{rig}.json")
    faces_skin = np.concatenate((skin["triangles"], np.asarray(insert["triangles"])+len(skin["positions"])))
    native = BVHTree.FromPolygons(skin["positions"]+insert["positions"],faces_skin.tolist(),all_triangles=True)
    cloth = BVHTree.FromPolygons(surface.tolist(),faces.tolist(),all_triangles=True)
    xs = np.arange(-14,14.3,.25)
    zs = np.arange(clav-14,clav+8.3,.25)
    for sign in (-1,1):
        gap = np.zeros((len(xs),len(zs)))
        for i,x in enumerate(xs):
            for j,z in enumerate(zs):
                eye = Vector((x,center[1]+sign*25,z))
                ray = Vector((0,-sign,0))
                a = native.ray_cast(eye,ray,25)[0]
                b = cloth.ray_cast(eye,ray,25)[0]
                if a is not None and b is not None:
                    gap[i,j]=max(0,(a.y-b.y)*sign+.32)
        # At the open neckline a ray just above the edge can hit its back
        # half. Restrict this local correction to the under-neck skin surface.
        gap=np.minimum(gap,2.3)
        pad=np.pad(gap,3,mode="edge")
        field=np.max([pad[i:i+len(xs),j:j+len(zs)] for i in range(7) for j in range(7)],axis=0)
        for _ in range(12):
            pad=np.pad(field,1,mode="edge")
            field=(pad[:-2,1:-1]+pad[2:,1:-1]+pad[1:-1,:-2]+pad[1:-1,2:]+4*field)/8
        ix=np.clip((surface[:,0]-xs[0])*4,0,len(xs)-1.001)
        iz=np.clip((surface[:,2]-zs[0])*4,0,len(zs)-1.001)
        a=ix.astype(int)
        b=iz.astype(int)
        tx=ix-a
        tz=iz-b
        change=(field[a,b]*(1-tx)+field[a+1,b]*tx)*(1-tz)+(field[a,b+1]*(1-tx)+field[a+1,b+1]*tx)*tz
        w=smooth((14-abs(surface[:,0]))/3)*smooth(((surface[:,1]-center[1])*sign)/3)
        w*=smooth((surface[:,2]-zs[0])/2)*smooth((zs[-1]-surface[:,2])/2)
        surface[:,1]+=sign*change*w
    return surface


def corrected_pattern(rig, outer, pattern):
    posed = np.asarray(outer["positions"])
    raw = np.asarray(pattern["positions"])
    bones = {b["name"]:np.array(b["position"]) for b in outer["bones"]}
    center = bones["neck_01"].copy()
    clav = (bones["clavicle_l"][2]+bones["clavicle_r"][2])*.5
    tree = body_tree(rig, clav)
    # Use the unwrinkled sewing pattern under the load-bearing shoulders.
    blend = smooth((posed[:,2]-clav+15)/9)*smooth((24-abs(posed[:,0]))/6)
    q = raw.copy()
    rim = np.asarray(outer["r4_pattern"]["neck_vertices"])
    samples = 192
    angles = np.arange(samples)*2*np.pi/samples
    ring_z = clav+4.8-1.65*np.sin(angles)
    radii = []
    for a,z in zip(angles,ring_z):
        axis = Vector((np.cos(a),np.sin(a),0))
        c = Vector((center[0],center[1],z))
        hit = tree.ray_cast(c+axis*23,-axis,23)[0]
        if hit is None:
            raise RuntimeError(f"Open anatomical neck section on {rig} at {a}")
        radii.append((hit-c).dot(axis))
    # A softly eased band bridges small anatomical grooves. The finished edge
    # has enough clearance for both its lining and the inward-facing seam.
    radii = np.asarray(radii)
    offsets = np.arange(-12,13)
    weights = np.exp(-.5*(offsets/4)**2)
    envelope = sum(w*np.roll(radii,i) for i,w in zip(offsets,weights/weights.sum()))
    envelope += max(.32, np.max(radii-envelope)+.18)
    theta = np.arctan2(raw[rim,1]-center[1],raw[rim,0]-center[0])%(2*np.pi)
    radius = np.interp(theta,angles,envelope,period=2*np.pi)
    lip = np.column_stack((center[0]+np.cos(theta)*radius,center[1]+np.sin(theta)*radius,
                           clav+4.8-1.65*np.sin(theta)))
    width = len(rim)
    first = rim-11*width
    t0 = 1/12
    base = (raw[first]-raw[rim]*t0)/(1-t0)
    base[:,2] -= .65*np.sin(t0*np.pi)/(1-t0)
    # Form a continuous collar yoke, with its lowest front under the throat.
    # Ease the shoulder-side cloth against the actual neck/head section.
    for step in range(1,13):
        t = step/12
        ids = first+(step-1)*width
        q[ids] = base*(1-t)+lip*t
        q[ids,2] += .18*np.sin(t*np.pi)
    for i in np.flatnonzero((blend>.0001) & (np.arange(len(raw))<=rim[-1])):
        if first[0] <= i <= rim[-1]:
            continue
        pt = q[i]
        origin = np.array([pt[0]*.63,center[1]*.6,clav-11])
        axis = pt-origin
        length = np.linalg.norm(axis)
        axis /= max(length,1e-6)
        hit = tree.ray_cast(Vector(pt+axis*6),Vector(-axis),11)[0]
        if hit is not None:
            correction = np.dot(np.asarray(hit)-pt,axis)
            q[i] += axis*(np.clip(correction,-1.15,2.2)+.29)
    # Reattach the yoke to the outer cloth after fitting its shoulder side.
    nearest = nearest_tree(raw[:first[0]])
    base_ids = [nearest.find(point)[1] for point in base]
    for step in range(1,13):
        ids = first+(step-1)*width
        q[ids] += (q[base_ids]-raw[base_ids])*(1-step/12)
    # Raglan cuts add vertices on existing edges. Use the same edge fraction
    # on the reshaped garment so the two panels keep a shared boundary.
    kd = nearest_tree(raw[:rim[-1]+1])
    for i in range(rim[-1]+1,len(raw)):
        ids = np.array([index for _,index,_ in kd.find_n(raw[i],18)])
        a,b=np.triu_indices(len(ids),1)
        edges=raw[ids[b]]-raw[ids[a]]
        weight=np.clip(((raw[i]-raw[ids[a]])*edges).sum(1)/np.maximum(1e-10,(edges*edges).sum(1)),0,1)
        error=np.linalg.norm(raw[ids[a]]+edges*weight[:,None]-raw[i],axis=1)
        k=int(np.argmin(error))
        q[i]=q[ids[a[k]]]*(1-weight[k])+q[ids[b[k]]]*weight[k]
    return neck_bib_clearance(posed+(q-posed)*blend[:,None], np.array(outer["triangles"]),rig,clav,center)


def layer_positions(rig, outer, revised):
    transfer = np.load(R4/"Simulation"/f"CollarTransfer_{rig}.npz")
    source = transfer["outer_before"]
    before = transfer["before"]
    live = transfer["after"]
    count = len(source)
    faces = np.asarray(outer["triangles"])
    original = np.asarray(outer["positions"])
    moved = np.linalg.norm(original-revised,axis=1)>.0001
    result = live.copy()
    result[:count] = revised
    nn = normals(revised,faces)
    thickness = np.full(count,.10)
    thickness[np.unique(faces[np.asarray(outer["triangle_materials"])==2])] = .12
    result[count:2*count][moved] = (revised-nn*thickness[:,None])[moved]
    bvh = BVHTree.FromPolygons(source.tolist(),faces.tolist(),all_triangles=True)
    upper = np.flatnonzero((np.arange(len(live))>=2*count)&(abs(live[:,0])<25)&
                           (live[:,2]>min(original[moved,2])-.5))
    for i in upper:
        hit,_,fi,_ = bvh.find_nearest(Vector(before[i]))
        ids = faces[fi]
        if not moved[ids].any():
            continue
        tri = source[ids]
        ab,ac = tri[1]-tri[0],tri[2]-tri[0]
        uv = np.linalg.lstsq(np.stack((ab,ac),axis=1),np.asarray(hit)-tri[0],rcond=None)[0]
        bary = np.array([1-uv.sum(),*uv])
        old_n = -np.cross(ab,ac)
        old_n /= max(1e-8,np.linalg.norm(old_n))
        new_n = bary@nn[ids]
        new_n /= max(1e-8,np.linalg.norm(new_n))
        result[i] = bary@revised[ids] + new_n*np.dot(before[i]-np.asarray(hit),old_n)
    return live, result


def carrier_positions(rig, cloth_points, cloth_faces):
    # The previous ray-by-ray offset field left pointed crests on the straps
    # and folded the front panel on Kaitlin. Fair the displacement on the
    # original, continuous carrier surface, including webbing and pocket seams.
    donor = read(S/"Integration/Delivery"/f"vest_{rig}_Wear.json")
    source = np.array(donor["positions"])
    current = np.array(read(R4/"Authored"/f"vest_{rig}.json")["positions"])
    origin = np.floor(source.min(0))-1
    cells = np.rint(source-origin).astype(int)
    shape = tuple(cells.max(0)+2)
    grid = np.zeros((*shape,4))
    idx = tuple(cells.T)
    np.add.at(grid[...,3],idx,1)
    for axis in range(3):
        np.add.at(grid[...,axis],idx,(current-source)[:,axis])
    occupied = grid[...,3]>0
    grid[occupied,:3] /= grid[occupied,3:4]
    grid[...,3]=occupied
    kernel = np.exp(-.5*(np.arange(-9,10)/3)**2)
    for axis in range(3):
        grid = np.apply_along_axis(lambda x:np.convolve(x,kernel,mode="same"),axis,grid)
    grid[...,:3] /= np.maximum(grid[...,3:4],1e-12)
    where=source-origin
    base=np.floor(where).astype(int)
    frac=where-base
    offset=np.zeros_like(source)
    for corner in np.ndindex(2,2,2):
        at=base+corner
        offset+=grid[tuple(at.T)][:,:3]*np.prod(np.where(corner,frac,1-frac),axis=1)[:,None]
    result=source+offset
    bones={b["name"]:np.array(b["position"]) for b in donor["bones"]}
    clav=bones["clavicle_l"][2]
    # Blend back onto the original pack-bearing back panel below the straps.
    blend=np.maximum(smooth((source[:,1]+2)/5),smooth((source[:,2]-clav+9)/8))
    result=current+(result-current)*blend[:,None]
    # Seat the strap on the fitted shoulder. Use a smooth radial section of
    # the strap's inner surface so the webbing and its edging travel together.
    carrier=BVHTree.FromPolygons(result.tolist(),donor["triangles"],all_triangles=True)
    cloth=BVHTree.FromPolygons(cloth_points.tolist(),cloth_faces.tolist(),all_triangles=True)
    y0=bones["upperarm_l"][1]
    z0=clav-5.
    xs=np.arange(-18.,18.51,.5)
    angles=np.arange(128)*2*np.pi/128
    sums=np.zeros((len(xs),len(angles)))
    count=np.zeros_like(sums)
    for i,x in enumerate(xs):
        if abs(x)<5:
            continue
        origin=Vector((x,y0,z0))
        for j,angle in enumerate(angles):
            axis=Vector((0,np.cos(angle),np.sin(angle)))
            a=carrier.ray_cast(origin,axis,24)[0]
            b=cloth.ray_cast(origin,axis,24)[0]
            if a is not None and b is not None and a.z>clav-7:
                sums[i,j]=np.clip((b-a).dot(axis)+.24,-2.5,1.8)
                count[i,j]=1
    for _ in range(6):
        for field in (sums,count):
            pad=np.pad(field,((1,1),(0,0)),mode="edge")
            field[:]=(4*field+np.roll(field,-1,1)+np.roll(field,1,1)+pad[:-2]+pad[2:])/8
    field=sums/np.maximum(count,.001)
    dr=result[:,1:]-[y0,z0]
    angle=np.arctan2(dr[:,1],dr[:,0])%(2*np.pi)
    t=angle*128/(2*np.pi)
    j=t.astype(int)%128
    tj=t-np.floor(t)
    x=np.clip((result[:,0]-xs[0])*2,0,len(xs)-1.001)
    i=x.astype(int)
    tx=x-i
    shift=(field[i,j]*(1-tj)+field[i,(j+1)%128]*tj)*(1-tx)+(field[i+1,j]*(1-tj)+field[i+1,(j+1)%128]*tj)*tx
    fade=smooth((result[:,2]-clav+7)/5)*smooth((abs(result[:,0])-4)/2)
    result[:,1:]+=dr/np.maximum(np.linalg.norm(dr,axis=1)[:,None],1e-8)*(shift*fade)[:,None]
    hardware=np.unique(np.asarray(donor["triangles"])[np.asarray(donor["triangle_materials"])==
                                                      donor["material_slots"].index("TS01_MattePolymer")])
    for sign in (-1,1):
        ids=hardware[source[hardware,0]*sign>0]
        a,b=source[ids],result[ids]
        u,_,v=np.linalg.svd((a-a.mean(0)).T@(b-b.mean(0)))
        result[ids]=(a-a.mean(0))@(u@v)+b.mean(0)
    moved=np.linalg.norm(result-current,axis=1)>.0001
    return current[moved],result[moved]


def main(rig):
    outer = read(R4/"Authored"/f"shirt_outer_{rig}.json")
    pattern = read(R4/"Authored"/f"shirt_pattern_{rig}.json")
    revised = corrected_pattern(rig,outer,pattern)
    current, result = layer_positions(rig,outer,revised)
    changed = np.linalg.norm(current-result,axis=1)>.0001
    np.savez_compressed(OUT/f"{rig}-cloth.npz",before=current[changed],after=result[changed])
    before,after=carrier_positions(rig,revised,np.asarray(outer["triangles"]))
    np.savez_compressed(OUT/f"{rig}-carrier.npz",before=before,after=after)
    print(rig, "sewn vertices refitted", changed.sum(),flush=True)


if __name__ == "__main__":
    for name in ("Jason","Kaitlin"):
        main(name)
