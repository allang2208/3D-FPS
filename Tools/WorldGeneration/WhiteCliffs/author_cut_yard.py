"""Build the bedrock extraction scar and an unfinished split blank at metre scale."""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree

root = Path(__file__).resolve().parents[3]
out = root / "SourceAssets/HillsQuarryCutYard"
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
mats = [bpy.data.materials.new(s) for s in ("WeatheredBed", "FreshBreak")]
manifest = []


def export(name, vertices, faces, slots):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    for material in mats:
        mesh.materials.append(material)
    mesh.update()
    uv = mesh.uv_layers.new(name="SurfaceMetres")
    for poly, slot in zip(mesh.polygons, slots):
        poly.material_index = slot
        axis = max(range(3), key=lambda i: abs(poly.normal[i]))
        for index in poly.loop_indices:
            x,y,z = mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv = ((y,z),(x,z),(x,y))[axis]
    bm=bmesh.new()
    bm.from_mesh(mesh)
    if name=="SM_QuarryBenchScar":
        # The crown and both end returns can be seen from the upper footpath.
        # Give them depthwise topology instead of stretching one strip across the cap.
        across=[e for e in bm.edges if abs(e.verts[0].co.y-e.verts[1].co.y)>3.1
                and abs(e.verts[0].co.x-e.verts[1].co.x)<.001]
        bmesh.ops.subdivide_edges(bm,edges=across,cuts=13,use_grid_fill=True)
        for v in bm.verts:
            x,y,z=v.co
            cap=ease(8.3,10.4,z)
            end=ease(9.7,11.35,abs(x))
            cross=ease(-2.55,-1.3,y)*(1-ease(1.35,2.55,y))
            field=noise.noise_vector(Vector((x*.7,y*.85,z*.17)))
            v.co.z+=cross*cap*(.48*field.z+.19*math.sin(x*1.31+y*1.16))
            v.co.x-=math.copysign(1,x)*end*cross*(.56+.32*field.x+.16*math.sin(z*1.4+y))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    if name=="SM_QuarryBenchScar":
        bm.normal_update()
        for f in bm.faces:
            f.smooth=(f.material_index==0)
        for e in bm.edges:
            e.smooth=(e.is_manifold and e.calc_face_angle()<math.radians(52)
                      and e.link_faces[0].material_index==e.link_faces[1].material_index)
    if any(not e.is_manifold for e in bm.edges):
        raise RuntimeError(name+" has an open seam")
    bm.to_mesh(mesh)
    bm.free()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.context.view_layer.update()
    bpy.ops.export_scene.fbx(filepath=str(out/(name+".fbx")),use_selection=True,object_types={"MESH"},
                             axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",use_tspace=True,bake_anim=False)
    manifest.append({"name":name,"size_cm":[round(100*s,2) for s in obj.dimensions],"triangles":len(mesh.polygons)})


def ease(lo, hi, x):
    t=min(1,max(0,(x-lo)/(hi-lo)))
    return t*t*(3-2*t)


def scanned_relief():
    # Project the closed Quixel scan onto its front plane, removing its overall
    # convex shape so only real intermediate-scale stone relief is transferred.
    source=root/"SourceAssets/HillsLandscapeRepair20261117/SolidScansR9/CliffA.blend"
    with bpy.data.libraries.load(str(source)) as (available, loaded):
        loaded.objects=[next(n for n in available.objects if n.startswith("SM_WhiteCliffA"))]
    obj=loaded.objects[0]
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    tree=BVHTree.FromPolygons(vertices,[list(f.vertices) for f in obj.data.polygons])
    low=np.min(vertices,axis=0)
    high=np.max(vertices,axis=0)
    side=72
    heights=np.zeros((side,side))
    for j in range(side):
        for i in range(side):
            sx=(.18+.64*i/(side-1))*(high[0]-low[0])+low[0]
            sz=(.17+.65*j/(side-1))*(high[2]-low[2])+low[2]
            hit=tree.ray_cast(Vector((sx,low[1]-1,sz)),Vector((0,1,0)))[0]
            heights[j,i]=hit.y if hit else np.nan
    heights=np.nan_to_num(heights,nan=np.nanmedian(heights))
    padded=np.pad(heights,7,mode="reflect")
    broad=sum(padded[j:j+side,i:i+side] for i in range(15) for j in range(15))/225.
    detail=np.clip((heights-broad)/max(.035,np.std(heights-broad)), -2.6,2.6)
    def sample(x,z):
        # Reflect the field at tile edges to avoid discontinuities.
        u=(1-abs((x/3.21+.19*z)%2-1))*(side-1)
        v=(1-abs((z/2.47+.07*x)%2-1))*(side-1)
        ix,iy=min(side-2,int(u)),min(side-2,int(v))
        tx,ty=u-ix,v-iy
        return ((1-tx)*detail[iy,ix]+tx*detail[iy,ix+1])*(1-ty)+((1-tx)*detail[iy+1,ix]+tx*detail[iy+1,ix+1])*ty
    return sample


def scar():
    # Interleaved tight layers form recessed bedding joints. The upper and
    # lower lips are continuous across the much deeper hand-worked bay.
    courses=[(0,0),(.80,.18),(2.05,.25),(2.16,-.28),(2.32,-.06),(3.08,.12),
             (3.20,.10),(3.36,.03),(4.64,.04),(4.78,-.15),(4.89,-.02),
             (6.14,.02),(6.34,-.16),(7.48,-.07),(7.65,.05),(7.85,.05),
             (8.52,.18),(8.67,-.37),(8.86,-.16),(10.12,-.06),(10.30,-.41),(11.10,-.64)]
    scan=scanned_relief()
    levels=dict(courses)
    for h in np.arange(.16,11.10,.16):
        if min(abs(h-level) for level in levels)>.055:
            levels[round(h,3)]=float(np.interp(h,*zip(*courses)))
    courses=sorted(levels.items())
    stations=sorted({round(-11.4+i*.12,4) for i in range(191)} |
                    {round(x+d,4) for x in (-3.8,-3.29,-2.74,-2.12,-1.59,-1.05,-.49,.08)
                     for d in (-.055,0,.055)})
    vs=[]; fs=[]; ms=[]
    def face(a,b,c,d,mat=0):
        fs.append((a,b,c,d));ms.append(mat)
    n=len(stations)
    row=2*n
    for j,(z,lip) in enumerate(courses):
        for side in (1,-1):
            for i,x in enumerate(stations):
                # The end returns taper into the surrounding living rock.
                end=ease(7.1,11.4,abs(x+.3))
                # Bedding has a common dip but splits, steps and dies out between
                # joints. Two unrelated joints should not trace parallel outlines.
                joint=0.
                offset=0.
                for k,(start,lean,bottom,upper) in enumerate(((-9,.25,.1,6.9),(-6.4,-.19,1.1,10.8),
                        (-3.5,.36,5.4,12),(.44,-.32,.4,3.5),(3.5,.22,6.3,12),(7.7,-.14,.7,9.7))):
                    dx=x-(start+lean*z+.11*math.sin(z*1.2+k))
                    active=ease(bottom-.4,bottom+.3,z)*(1-ease(upper-.3,upper+.25,z))
                    joint+=active*max(0.,1-abs(dx)/(.15+.065*(k%3)))
                    offset+=active*(.23 if k%2 else -.19)*ease(-.15,.13,dx)
                coarse=noise.noise_vector(Vector((x*.43,z*.52,1.3))).x
                ledge=noise.noise_vector(Vector((x*.30,z*.19,4.3))).y
                wave=.17*math.sin(x*.53)+.22*coarse+.18*ledge+.055*scan(x,z)
                left=-4.65+(.8 if z>6.34 else 0)
                right=4.83-(1.28 if z<4.78 else 0)
                # Two successive lifts leave a shallow stepped working face.
                # Leave a battered lower sill beneath the newer tool cuts.
                sill=2.52+.49*ease(-.8,1.6,x)+.12*math.sin(x*1.45)
                soffit=7.05+.41*ease(-1.7,-.8,x)
                bay=ease(left-.34,left+.16,x)*(1-ease(right-.18,right+.31,x))*ease(sill,sill+.38,z)*(1-ease(soffit,soffit+.55,z))
                kerf=sum(max(0,1-abs(x-k)/.055) for k in (-3.8,-3.29,-2.74,-2.12,-1.59,-1.05,-.49,.08))
                # Outer abutments shelter a short dark parting; it pinches out
                # across the mouth of the excavated area.
                joint_scale=.38+1.0*ease(-.47,.27,coarse+.25*math.sin(x*.64+z*.51))
                recess=.61+.32*ease(-.35,.35,x)+.12*(z-4.)/4.
                relief=(lip*joint_scale+wave-.29*joint)*(1-bay)+bay*(.25*wave-recess-.09*kerf*ease(3.5,4.12,z)*(1-ease(5.2,5.7,z)))
                depth=(2.55+relief)*(1-.32*end) if side>0 else -2.65+.25*math.sin(x*.43)
                crown=ease(8.7,11.1,z)
                profile=.58*noise.noise_vector(Vector((x*.58,1.1,2.3))).x+.28*noise.noise_vector(Vector((x*1.94,3.6,1.5))).y
                top=z*(1-.23*end)+min(1,z)*(.17*math.sin(x*.43+.6)+.047*x+offset*(1-bay))+crown*(profile-.4*joint)
                vs.append((x,depth,top))
        if j:
            for i in range(n-1):
                a=(j-1)*row+i
                q=(stations[i]+stations[i+1])/2
                mid=(z+courses[j-1][0])*.5
                fresh=int(2.70+.49*ease(-.8,1.6,q)+.12*math.sin(q*1.45)<mid<7.25+.41*ease(-1.7,-.8,q)
                          and (-4.65+(.8 if mid>6.34 else 0))<q<(4.83-(1.28 if mid<4.78 else 0)))
                face(a,a+1,a+row+1,a+row,fresh)
                a+=n
                face(a,a+row,a+row+1,a+1)
            a=(j-1)*row
            for i in (0,n-1):
                face(a+i,a+n+i,a+n+row+i,a+row+i)
    for a in (0,(len(courses)-1)*row):
        for i in range(n-1):
            face(a+i,a+n+i,a+n+i+1,a+i+1)
    export("SM_QuarryBenchScar",vs,fs,ms)


def blank():
    # A missing corner and an incomplete diagonal split are visible above ground.
    ring=[(-1.28,-.70),(.67,-.74),(1.23,-.36),(1.26,.51),(.98,.69),(-.86,.72),(-1.3,.42)]
    vs=[];fs=[];ms=[]
    for j,(scale,z) in enumerate(((.94,0),(1,.09),(.99,.84),(.92,.97))):
        for i,(x,y) in enumerate(ring):
            vs.append((x*scale,y*scale,z+(.04*math.sin(i*1.76)-.08*max(0,x) if j>=2 else 0)))
            if j:
                a=(j-1)*len(ring)+i; b=(j-1)*len(ring)+(i+1)%len(ring)
                fs.append((a,b,b+len(ring),a+len(ring)));ms.append(int(i in (0,1,2,6)))
    n=len(ring)
    fs.extend((tuple(reversed(range(n))),tuple(range(3*n,4*n))));ms.extend((0,1))
    export("SM_QuarrySplitBlank",vs,fs,ms)


scar()
blank()
(out/"mesh-manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf8")
