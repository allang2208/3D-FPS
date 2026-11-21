"""Partition the finished wall skin by whole stones and pack its interior with fractured rock."""
from collections import defaultdict
from functools import lru_cache
import json
import math
from pathlib import Path
import random
from struct import iter_unpack
from zipfile import ZipFile


def add(p, q):
    return tuple(a+b for a,b in zip(p,q))


def sub(p, q):
    return tuple(a-b for a,b in zip(p,q))


def scale(p, f):
    return tuple(a*f for a in p)


def dot(p, q):
    return sum(a*b for a,b in zip(p,q))


def cross(p, q):
    a,b,c = p
    x,y,z = q
    return (b*z-c*y,c*x-a*z,a*y-b*x)


def unit(p):
    return scale(p, 1./max(1.e-12, math.sqrt(dot(p,p))))


def mix(p, q, t):
    return tuple(a + (b-a)*t for a,b in zip(p,q))


def mean(points):
    return tuple(sum(a)/len(a) for a in zip(*points))


def shard(p):
    x,y,z = p
    bed = 12.*math.sin(x*.024+y*.009) + 7.*math.sin(y*.043)
    row = int(z > 124.+bed) + int(z > 266.-bed*.88)
    jog = 12.*math.sin(z*.049+y*.016) + 6.*math.sin(y*.037-z*.018)
    joints = ((-58.,46.),(-34.,64.),(-56.,43.))[row]
    return row*3 + int(x > joints[0]+jog) + int(x > joints[1]-jog*.85)


class Buffer:
    def __init__(self):
        self.corners = []
        self.indices = []
        self.lookup = {}

    def face(self, a, b, c):
        tri = []
        for corner in (a,b,c):
            i = self.lookup.get(corner)
            if i is None:
                i = len(self.corners)
                self.corners.append(corner)
                self.lookup[corner] = i
            tri.append(i)
        self.indices.append(tri)


def read_wall(file):
    groups = {}
    with ZipFile(file) as archive:
        spec = json.loads(archive.read("mesh.json"))
        for i, slot in enumerate(spec["materials"]):
            def entries(name, fmt):
                return list(iter_unpack("<"+fmt, archive.read(f"{i}/{name}")))
            groups[slot] = (entries("vertices","3f"),entries("normals","3f"),
                            entries("uv","2f"),entries("indices","3i"))
    return spec, groups


def islands(vertices, faces):
    # Buffer indices are split at UV seams and each flat stone facet. Weld positions
    # for connectivity only; all original per-corner attributes survive the bake.
    parent = list(range(len(vertices)))
    def root(i):
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = {}
    for i,pos in enumerate(vertices):
        matched = seen.setdefault(pos,i)
        parent[i] = matched
    for a,b,c in faces:
        k = root(a)
        parent[root(b)] = k
        parent[root(c)] = k
    components = defaultdict(list)
    for face in faces:
        components[root(face[0])].append(face)
    return components.values()


class WallSection:
    """Fitted exterior Y span at each X,Z; the collision box alone is much wider in places."""
    CELL = 20.
    def __init__(self, groups):
        self.tris = defaultdict(list)
        for vertices, _, _, faces in groups.values():
            for ia,ib,ic in faces:
                a,b,c = vertices[ia],vertices[ib],vertices[ic]
                ux,uy,uz = sub(b,a)
                vx,vy,vz = sub(c,a)
                det = ux*vz-vx*uz
                if abs(det)<1.e-6:
                    continue
                record = (a,ux/det,uz/det,vx/det,vz/det,uy,vy)
                xs,zs = [p[0] for p in (a,b,c)],[p[2] for p in (a,b,c)]
                for ix in range(math.floor(min(xs)/self.CELL),math.floor(max(xs)/self.CELL)+1):
                    for iz in range(math.floor(min(zs)/self.CELL),math.floor(max(zs)/self.CELL)+1):
                        self.tris[ix,iz].append(record)

    @lru_cache(maxsize=24576)
    def span(self, x, z):
        hits = []
        for a,ux,uz,vx,vz,uy,vy in self.tris[math.floor(x/self.CELL),math.floor(z/self.CELL)]:
            dx,dz = x-a[0],z-a[2]
            s,t = dx*vz-dz*vx,ux*dz-uz*dx
            if s>=-1.e-6 and t>=-1.e-6 and s+t<=1.000001:
                hits.append(a[1]+s*uy+t*vy)
        return (min(hits),max(hits)) if len(hits)>1 else None


def split_skin(groups, parts, backing, owner_at):
    for slot,(vertices,normals,uv,faces) in groups.items():
        corners = list(zip(vertices,normals,uv))
        for component in islands(vertices,faces):
            points = {vertices[i] for face in component for i in face}
            lo,hi = tuple(map(min,zip(*points))),tuple(map(max,zip(*points)))
            if slot=="Mortar" and (lo,hi)==backing:
                # Its six intact faces are rebuilt on the border of the solid partition below.
                continue
            center = mix(lo,hi,.5)
            # Bed stones, individual merlons, ties and paving units release whole.
            single = hi[0]-lo[0] < 111. and hi[2]-lo[2] < 116.
            owner = owner_at(center)
            for face in component:
                tri = tuple(corners[i] for i in face)
                if slot.startswith("HighWallStone") and all(
                        all(low+1.5<p<high-1.5 for low,p,high in zip(backing[0],corner[0],backing[1]))
                        for corner in tri):
                    continue
                if single:
                    parts[owner][slot].face(*tri)
                else:
                    distribute(tri,slot,parts,owner_at)


def distribute(tri, slot, parts, owner_at):
    pos = [c[0] for c in tri]
    center = mean(pos)
    owner = owner_at(center)
    lengths = [dot(sub(pos[i],pos[i-1]),sub(pos[i],pos[i-1])) for i in range(3)]
    # Only refine the few broad backing faces near a joint. Original UVs and normal
    # directions interpolate along the same face and its full visible area survives.
    if max(lengths)>14.**2 and (max(lengths)>65.**2 or any(owner_at(p)!=owner for p in pos)):
        i = lengths.index(max(lengths))
        a,b,c = tri[i-1],tri[i],tri[(i+1)%3]
        m = (mix(a[0],b[0],.5),unit(mix(a[1],b[1],.5)),mix(a[2],b[2],.5))
        distribute((a,m,c),slot,parts,owner_at)
        distribute((m,b,c),slot,parts,owner_at)
    else:
        parts[owner][slot].face(*tri)


def cell_box(lo, hi):
    x,y,z = lo
    X,Y,Z = hi
    a,b,c,d = (x,y,z),(X,y,z),(X,Y,z),(x,Y,z)
    e,f,g,h = (x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)
    return [[d,c,b,a],[e,f,g,h],[a,b,f,e],[b,c,g,f],[c,d,h,g],[d,a,e,h]]


def clip_cell(faces, normal, distance, neighbour):
    """Intersect a convex 3-D cell with a neighbour bisector; all windings point out."""
    result, rim = [], {}
    for tag,face in faces:
        polygon = []
        a = face[-1]
        da = dot(normal,a)-distance
        for b in face:
            db = dot(normal,b)-distance
            if (da<=0) != (db<=0):
                p = mix(a,b,da/(da-db))
                polygon.append(p)
                rim[tuple(round(v,5) for v in p)] = p
            if db<=0:
                polygon.append(b)
            a,da = b,db
        if len(polygon)>2:
            result.append((tag,polygon))
    if len(rim)>2:
        points = list(rim.values())
        center = mean(points)
        n = unit(normal)
        u = unit(cross(n,(0,0,1) if abs(n[2])<.8 else (0,1,0)))
        v = cross(n,u)
        points.sort(key=lambda p:math.atan2(dot(sub(p,center),v),dot(sub(p,center),u)))
        result.append((neighbour,points))
    return result


class Rockfill:
    def __init__(self, lo, hi, seed, fitted=lambda p:p):
        self.lo,self.hi,self.rng,self.fitted = lo,hi,random.Random(seed),fitted
        self.counts = tuple(max(1,round((b-a)/d)) for a,b,d in zip(lo,hi,(39.,34.,32.)))
        self.steps = tuple((b-a)/count for a,b,count in zip(lo,hi,self.counts))
        self.sites = []
        self.owners = []
        for ix in range(self.counts[0]):
            for iy in range(self.counts[1]):
                for iz in range(self.counts[2]):
                    point = tuple(a+(i+.5+self.rng.uniform(-.29,.29))*d
                                  for a,i,d in zip(lo,(ix,iy,iz),self.steps))
                    self.sites.append(point)
                    self.owners.append(shard(fitted(point)))

    @lru_cache(maxsize=32768)
    def owner_at(self,x,y,z):
        # A surface course belongs to its underlying rock cell. The bounded jitter
        # guarantees that two neighbouring grid rings contain the nearest site.
        pos = (x,y,z)
        nx,ny,nz = self.counts
        grid = [min(n-1,max(0,math.floor((v-a)/d))) for v,a,d,n in
                zip(pos,self.lo,self.steps,self.counts)]
        near = ((ix*ny+iy)*nz+iz for ix in range(max(0,grid[0]-2),min(nx,grid[0]+3))
                for iy in range(max(0,grid[1]-2),min(ny,grid[1]+3))
                for iz in range(max(0,grid[2]-2),min(nz,grid[2]+3)))
        def distance(i):
            a,b,c = self.sites[i]
            return (a-x)**2+(b-y)**2+(c-z)**2
        return self.owners[min(near,key=distance)]

    def build(self,parts):
        for index,site in enumerate(self.sites):
            neighbours = sorted((dot(sub(q,site),sub(q,site)),j)
                                for j,q in enumerate(self.sites) if j!=index)
            faces = [(None,f) for f in cell_box(self.lo,self.hi)]
            reach = float("inf")
            for d2,j in neighbours:
                if d2>4.*reach+1.e-6:
                    break
                q = self.sites[j]
                faces = clip_cell(faces,sub(q,site),.5*(dot(q,q)-dot(site,site)),j)
                reach = max(dot(sub(p,site),sub(p,site)) for tag,face in faces for p in face)
            center = self.fitted(site)
            owner = self.owners[index]
            part = parts[owner]
            stone = "YardSlate" if self.rng.random()<.17 else "YardField"
            offset = (self.rng.random()*4,self.rng.random()*4)
            for neighbour,face in faces:
                if neighbour is not None and self.owners[neighbour]==owner:
                    continue
                mapped = [self.fitted(p) for p in face]
                face_center = mean(mapped)
                if neighbour is None:
                    # Exactly the same mortar envelope and world-scale UV as the intact wall.
                    for i,p in enumerate(mapped):
                        rock_face(part,"Mortar",face_center,p,mapped[(i+1)%len(face)],(0.,0.))
                    continue
                # Complementary rock faces leave a narrow recessed mortar bed at the
                # chipped edge. Original polygon borders meet on every edge of this solid.
                bevel = [mix(mix(p,face_center,.055),center,.07) for p in mapped]
                lip = [mix(mix(p,face_center,.14),center,.012) for p in mapped]
                crown = mix(face_center,center,.019)
                for i,p in enumerate(lip):
                    j = (i+1)%len(lip)
                    rock_face(part,stone,crown,p,lip[j],offset)
                    rock_face(part,stone,p,bevel[i],bevel[j],offset)
                    rock_face(part,stone,p,bevel[j],lip[j],offset)
                    rock_face(part,"Mortar",bevel[i],mapped[i],mapped[j],offset)
                    rock_face(part,"Mortar",bevel[i],mapped[j],bevel[j],offset)


def rock_face(part,slot,a,b,c,offset):
    n = cross(sub(b,a),sub(c,a))
    if dot(n,n)<1.e-10:
        return
    n = unit(n)
    axes = ((1,2),(0,2),(0,1))[max(range(3),key=lambda k:abs(n[k]))]
    def corner(p):
        return (p,n,(p[axes[0]]/100.+offset[0],p[axes[1]]/100.+offset[1]))
    # UE static mesh buffers use the opposite winding to the outward normal.
    part[slot].face(corner(a),corner(c),corner(b))


def partition(file):
    spec, groups = read_wall(file)
    parts = [defaultdict(Buffer) for _ in range(9)]
    # Use the real closed mortar backing, not the gameplay blocker. Preserve the
    # narrow end tongue, deck and separate surface stones via their source triangles.
    verts,_,_,faces = groups["Mortar"]
    bounds = []
    for component in islands(verts,faces):
        pts = {verts[i] for f in component for i in f}
        bounds.append((tuple(map(min,zip(*pts))),tuple(map(max,zip(*pts)))))
    backing = max(bounds,key=lambda b: math.prod(sub(b[1],b[0])))
    if min(sub(backing[1],backing[0]))<90.:
        raise ValueError("The new high wall needs its closed masonry backing before fracturing.")
    body = Rockfill(*backing,73291)
    body.build(parts)

    # The narrow parapet is a Meshy shell. Fit one solid rockfill to its real
    # two faces. Individual merlons ride on the top row with their original UVs.
    sill = spec["boxes"][1]
    c,size = sill["center"],sill["size"]
    lo = (c[0]-size[0]*.5+2.,c[1]-size[1]*.5,backing[1][2])
    hi = (c[0]+size[0]*.5-2.,c[1]+size[1]*.5,c[2]+size[2]*.5-2.)
    skin = WallSection({k:g for k,g in groups.items() if k.startswith("HighWallStone")})
    @lru_cache(maxsize=8192)
    def fitted(p):
        x,y,z = p
        span = skin.span(round(x),round(z))
        if span and span[1]-span[0]>7.:
            ymin,ymax = span[0]+2.5,span[1]-2.5
        else:
            ymin,ymax = c[1]-2.,c[1]+2.
        return (x,ymin+(y-lo[1])/(hi[1]-lo[1])*(ymax-ymin),z)
    parapet = Rockfill(lo,hi,34907,fitted)
    parapet.build(parts)
    def owner_at(p):
        x,y,z = [round(v) for v in p]
        if z>backing[1][2] and y<lo[1]+size[1]+3.:
            return parapet.owner_at(x,max(lo[1],min(hi[1],y)),min(hi[2],z))
        return body.owner_at(x,y,z)
    split_skin(groups,parts,backing,owner_at)
    return parts
