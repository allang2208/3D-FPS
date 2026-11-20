"""UV1 atlas and CPU ray bake from each authored HIGH master into its GAME counterpart.

Requires Blender 5.1, numpy, Pillow, scipy, numba, xatlas and embreex.
Run this script with a rig and action: extract, atlas, bake, deliver, or all.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import struct
import sys

import numpy as np
import shapely
from numba import njit
from PIL import Image
from scipy.ndimage import distance_transform_edt

sys.path.append(str(Path(os.environ["TEMP"])/"ts01_exfil_bake_deps"))
import xatlas
from embreex.mesh_construction import TriangleMesh
from embreex.rtcore_scene import EmbreeScene

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4"
BAKES=ROOT/"Bakes"
CACHE=Path(os.environ["TEMP"])/"ts01_exfil_reference_bakes"
BLENDER=os.environ.get("BLENDER_EXE",r"E:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
SLOTS=("Composite","Polymer","Rubber","Webbing","LoopPile","PadMesh","Metal","Label","Stitch","DarkPolymer")


def blender(action,rig,*args):
    subprocess.run([BLENDER,"--factory-startup","-b","-t","4","--python-exit-code","1",
                    "--python",str(HERE/"exfil_reference_bake_mesh.py"),"--",action,rig,*args],check=True)


def input_mesh(rig,stage):
    with np.load(CACHE/f"{rig}-{stage}.npz") as source:
        return {key:source[key] for key in source.files}


def unstack(uv,pos,tri,size):
    # xatlas can fold a few thin triangles where heavily bevelled parts meet.
    # Detect positive-area intersections and give the affected triangles their
    # own islands, with a real gutter around each one.
    polys=shapely.polygons(uv.astype(np.float64))
    tree=shapely.STRtree(polys)
    q,r=tree.query(polys);unique=q<r;q=q[unique];r=r[unique]
    hit=shapely.relate_pattern(polys[q],polys[r],"2********")
    bad=set(r[hit].tolist())
    bad.update(np.flatnonzero(shapely.area(polys)<1.e-15).tolist())
    if not bad:return 0,0
    gap=6;x=gap;y=gap;row_h=0;islands={}
    for i in sorted(bad):
        xyz=pos[tri[i]]
        j=int(np.argmax(np.linalg.norm(np.roll(xyz,-1,axis=0)-xyz,axis=1)))
        order=[j,(j+1)%3,(j+2)%3];v=xyz[order]
        along=v[1]-v[0];along=along/max(np.linalg.norm(along),1.e-14)
        len3=max(np.linalg.norm(v[1]-v[0]),1.e-14)
        ratio=np.clip(np.dot(v[2]-v[0],along)/len3,0.,1.)
        height=np.linalg.norm(np.cross(along,v[2]-v[0]))/len3
        scale=max(7.,min(140.,np.linalg.norm(uv[i,order[1]]-uv[i,order[0]])*size))
        h=max(4.,scale*height)
        if x+scale+gap>=size:x=gap;y+=row_h+2*gap;row_h=0
        islands[i]=(order,np.array([[x,y],[x+scale,y],[x+ratio*scale,y+h]])/size)
        x+=math.ceil(scale)+2*gap;row_h=max(row_h,math.ceil(h))
    reserve=int(y+row_h+2*gap)
    if reserve>.35*size:raise RuntimeError(f"Insufficient atlas space for {len(bad)} private triangles")
    uv[:,:,1]=uv[:,:,1]*(1.-reserve/size)+reserve/size
    for i,(order,coords) in islands.items():uv[i,order]=coords
    return len(bad),reserve


def atlas(rig,size):
    mesh=input_mesh(rig,"GAME")
    uv=np.empty((len(mesh["f"]),3,2),np.float32)
    groups=[];a=xatlas.Atlas()
    for group,name in enumerate(mesh["names"]):
        ids=np.flatnonzero(mesh["group"]==group)
        used,inv=np.unique(mesh["f"][ids].reshape(-1),return_inverse=True)
        tri=inv.reshape(-1,3).astype(np.uint32)
        a.add_mesh(np.ascontiguousarray(mesh["p"][used]),tri);groups.append((ids,used))
    pack=xatlas.PackOptions();pack.resolution=size;pack.padding=max(4,size//512)
    chart=xatlas.ChartOptions();chart.max_iterations=1;chart.fix_winding=True
    a.generate(chart,pack)
    if a.atlas_count!=1:raise RuntimeError(f"Expected one atlas, got {a.atlas_count}")
    for i,(ids,used) in enumerate(groups):
        remap,idx,coords=a[i]
        if not np.array_equal(used[remap[idx]],mesh["f"][ids]):
            raise RuntimeError(f"Atlas face correspondence lost on {mesh['names'][i]}")
        uv[ids]=coords[idx]
    relocated,height=unstack(uv,mesh["p"],mesh["f"],size)
    np.save(CACHE/f"{rig}-atlas.npy",uv)
    meta=dict(charts=a.chart_count,pack_size=[a.width,a.height],requested_padding=pack.padding,
              mapped_resolution=size,isolated_triangles=relocated,isolation_strip_pixels=height)
    (CACHE/f"{rig}-atlas.json").write_text(json.dumps(meta),encoding="utf8")
    print("ATLAS",rig,meta,flush=True)
    blender("basis",rig)


@njit(cache=True)
def raster(uv,size):
    identity=np.full((size,size),-1,np.int32)
    g=np.zeros((size,size,2),np.float32)
    overlaps=0
    for i in range(len(uv)):
        x0,x1,x2=uv[i,:,0]*size;y0,y1,y2=(1.-uv[i,:,1])*size
        ax=x1-x0;ay=y1-y0;bx=x2-x0;by=y2-y0
        det=ax*by-bx*ay
        if abs(det)<1.e-8:continue
        for y in range(max(0,int(math.ceil(min(y0,y1,y2)-.5))),min(size,int(math.floor(max(y0,y1,y2)-.5))+1)):
            dy=y+.5-y0
            for x in range(max(0,int(math.ceil(min(x0,x1,x2)-.5))),min(size,int(math.floor(max(x0,x1,x2)-.5))+1)):
                dx=x+.5-x0
                b=(dx*by-bx*dy)/det;c=(ax*dy-dx*ay)/det
                if b>=-1.e-6 and c>=-1.e-6 and b+c<=1.000001:
                    if identity[y,x]>=0 and min(b,c,1.-b-c)>1.e-4:
                        old=g[y,x]
                        if min(old[0],old[1],1.-old[0]-old[1])>1.e-4:overlaps+=1
                    identity[y,x]=i;g[y,x,0]=b;g[y,x,1]=c
    return identity,g,overlaps


def unit(v):
    return v/np.maximum(np.float32(1.e-12),np.linalg.norm(v,axis=-1,keepdims=True))


def dots(a,b):
    return np.einsum("ij,ij->i",a,b)


def interp(arr,weight):
    return np.einsum("ijk,ij->ik",arr,weight)


def frame(t,n,sign):
    t=unit(t-n*dots(n,t)[:,None])
    return t,np.cross(n,t)*np.where(sign>=0,1.,-1.).astype(np.float32)[:,None]


def scene_for(mesh,ids):
    scene=EmbreeScene()
    faces=np.ascontiguousarray(mesh["f"][ids],dtype=np.int32)
    used,inv=np.unique(faces,return_inverse=True)
    triangles=TriangleMesh(scene,np.ascontiguousarray(mesh["p"][used]),inv.reshape(-1,3).astype(np.int32))
    return scene,triangles


def project(high,low_groups,bvh,pos,norm):
    normals=norm.copy();points=pos.copy();ok=np.zeros(len(pos),bool)
    cage=.35
    for gi in np.unique(low_groups):
        local=np.flatnonzero(low_groups==gi)
        scene,_,ids=bvh[gi]
        n=norm[local];p=pos[local];best=np.full(len(local),np.inf,np.float32)
        for direction in (1.,-1.):
            hit=scene.run(np.ascontiguousarray(p+direction*cage*n),np.ascontiguousarray(-direction*n),
                          dists=np.full(len(p),2*cage,np.float32),query="INTERSECT",output=1)
            good=np.flatnonzero(hit["primID"]>=0)
            if not len(good):continue
            u=hit["u"][good];v=hit["v"][good]
            w=np.stack((1.-u-v,u,v),axis=1)
            face=ids[hit["primID"][good]]
            hn=unit(interp(high["cn"][face],w));disp=cage-hit["tfar"][good]
            keep=(dots(hn,n[good])>.25)&(np.abs(disp)<best[good])
            ii=good[keep];dest=local[ii]
            normals[dest]=hn[keep];points[dest]=p[ii]+direction*disp[keep,None]*n[ii]
            best[ii]=np.abs(disp[keep]);ok[dest]=True
    return normals,points,ok


def occlusion(scene,p,n,rays,radius):
    ref=np.zeros_like(n);ref[:,2]=1;ref[abs(n[:,2])>.92]=[0,1,0]
    t=unit(np.cross(n,ref));b=np.cross(n,t);origin=np.ascontiguousarray(p+.022*n)
    limit=np.full(len(p),radius,np.float32);dark=np.zeros(len(p),np.float32)
    for j in range(rays):
        z=math.sqrt(1.-(j+.5)/rays);rr=math.sqrt(1-z*z);phi=j*2.399963229728653
        direction=np.ascontiguousarray(rr*(math.cos(phi)*t+math.sin(phi)*b)+z*n)
        distance=scene.run(origin,direction,dists=limit.copy(),query="DISTANCE")
        dark+=np.maximum(0.,1.-distance/radius)**2
    return np.clip(1.-dark/rays,0.,1.)


def sample(tex,uv,clamp=False):
    h,w=tex.shape[:2]
    x=uv[:,0]*w-.5;y=(1.-uv[:,1])*h-.5
    ix=np.floor(x).astype(np.int32);iy=np.floor(y).astype(np.int32)
    fx=(x-ix).astype(np.float32)[:,None];fy=(y-iy).astype(np.float32)[:,None]
    if clamp:
        a=np.clip(ix,0,w-1);b=np.clip(ix+1,0,w-1)
        c=np.clip(iy,0,h-1);d=np.clip(iy+1,0,h-1)
    else:
        a=ix%w;b=(ix+1)%w;c=iy%h;d=(iy+1)%h
    return ((tex[c,a]*(1.-fx)+tex[c,b]*fx)*(1.-fy)+(tex[d,a]*(1.-fx)+tex[d,b]*fx)*fy)


def byte(arr):
    return np.clip(np.rint(arr),0,255).astype(np.uint8)


def write_geometry(rig,uv):
    dst=BAKES/rig;mapping={}
    ue_uv=uv.copy();ue_uv[:,:,1]=1.-ue_uv[:,:,1]
    for kind in ("wear","world"):
        data=json.loads((ROOT/"Authored"/f"helmet_{rig}_{kind}.json").read_bytes())
        if len(data["triangles"])!=len(ue_uv):raise RuntimeError("Low master does not match published topology")
        data["uv"]=ue_uv.round(7).tolist();data["material_slots"]=["EXFIL_Atlas_"+rig]
        data["triangle_materials"]=[0]*len(ue_uv)
        path=dst/f"helmet_{rig}_{kind}.json"
        with path.open("w",encoding="utf8") as stream:json.dump(data,stream,separators=(",",":"))
        mapping[kind]=str(path.relative_to(BAKES)).replace("\\","/")
        del data
    return mapping


def bake(rig,size,rays):
    dst=BAKES/rig;dst.mkdir(parents=True,exist_ok=True)
    low=input_mesh(rig,"GAME");high=input_mesh(rig,"HIGH")
    uv=np.load(CACHE/f"{rig}-atlas.npy");basis=input_mesh(rig,"basis")
    ids,bc,overlaps=raster(uv,size);valid=ids>=0
    polygon_count=np.bincount(ids[valid],minlength=len(low["f"]))
    print("RASTER",rig,int(valid.sum()),overlaps,flush=True)
    if overlaps:raise RuntimeError(f"Atlas contains {overlaps} double-covered interior samples")
    full,full_tri=scene_for(high,np.arange(len(high["f"])))
    bvh={};aliases={}
    # Stitch object suffixes are spline sampling indices in each LOD.
    for prefix in ("Fore_Yoke_R_BarTack_","Fore_Yoke_L_BarTack_","Chin_Reinforcement_Tack_"):
        def ordered(names):
            return sorted((str(k) for k in names if k.startswith(prefix)),key=lambda k:int(k.rsplit("_",1)[1]))
        a=ordered(low["names"]);b=ordered(high["names"])
        if len(a)!=len(b):raise ValueError(f"Unequal stitch sequence {prefix}")
        aliases.update(dict(zip(a,b)))
    for group,name in enumerate(low["names"]):
        where=np.flatnonzero(high["names"]==aliases.get(str(name),str(name)))
        if len(where)!=1:raise ValueError(f"Missing high cage for {name}")
        faces=np.flatnonzero(high["group"]==where[0])
        bvh[group]=(*scene_for(high,faces),faces)
    textures=[]
    for name in SLOTS:
        triple=[]
        for channel in ("BaseColor","NormalGL","ORM"):
            with Image.open(ROOT/"Textures"/f"H1_{name}_{channel}.png") as src:
                triple.append(np.asarray(src.convert("RGB")))
        textures.append(triple)
    outputs={k:np.zeros((size,size,3),np.uint8) for k in ("BaseColor","NormalGL","ORM")}
    aoimg=np.full((size,size),255,np.uint8);hist=np.zeros(181,np.int64)
    matched=np.zeros(len(low["names"]),np.int64);total=matched.copy()
    for y in range(0,size,64):
        sl=slice(y,min(y+64,size));vy,vx=np.nonzero(valid[sl])
        if not len(vy):continue
        tri=ids[sl][vy,vx];w=bc[sl][vy,vx];w=np.column_stack((1.-w.sum(1),w))
        pos=interp(low["p"][low["f"][tri]],w);n=unit(interp(low["cn"][tri],w))
        groups=low["group"][tri]
        hn,hp,ok=project(high,groups,bvh,pos,n)
        total+=np.bincount(groups,minlength=len(total));matched+=np.bincount(groups[ok],minlength=len(total))
        angles=np.rint(np.degrees(np.arccos(np.clip(dots(n,hn),-1.,1.)))).astype(np.int32)
        hist+=np.bincount(angles[ok],minlength=len(hist))
        ao=occlusion(full,hp,hn,rays,3.5);aoimg[y+vy,vx]=byte(ao*255.)
        olduv=interp(low["uv"][tri],w)
        ot,ob=frame(interp(basis["old_t"][tri],w),hn,np.einsum("ij,ij->i",basis["old_s"][tri],w))
        dt,db=frame(interp(basis["t"][tri],w),n,np.einsum("ij,ij->i",basis["s"][tri],w))
        for mi in np.unique(low["mat"][tri]):
            k=np.flatnonzero(low["mat"][tri]==mi);xy=(vy[k]+y,vx[k]);col,tan,orm=textures[mi]
            clamp=bool(mi==7)
            outputs["BaseColor"][xy]=byte(sample(col,olduv[k],clamp))
            detail=unit(sample(tan,olduv[k],clamp)/127.5-1.)
            wn=unit(ot[k]*detail[:,0,None]+ob[k]*detail[:,1,None]+hn[k]*detail[:,2,None])
            nt=unit(np.column_stack((dots(dt[k],wn),dots(db[k],wn),dots(n[k],wn))))
            outputs["NormalGL"][xy]=byte((nt*.5+.5)*255.)
            packed=sample(orm,olduv[k],clamp);packed[:,0]*=ao[k];outputs["ORM"][xy]=byte(packed)
        if y%512==0:print("TRANSFER",rig,y,size,flush=True)
    nearest=distance_transform_edt(~valid,return_distances=False,return_indices=True)
    target=np.nonzero(~valid);source=tuple(nearest[:,target[0],target[1]])
    outputs["GeometryAO"]=aoimg
    paths={}
    for kind,im in outputs.items():
        im[target]=im[source]
        path=dst/f"T_EXFIL_{rig}_{kind}.png"
        Image.fromarray(im).save(path,compress_level=4)
        paths[kind]=path.relative_to(BAKES).as_posix()
    atlasmeta=json.loads((CACHE/f"{rig}-atlas.json").read_bytes())
    room=write_geometry(rig,uv)
    info=dict(rig=rig,resolution=size,triangles_low=len(low["f"]),triangles_high=len(high["f"]),
              matched_object_pairs=len(bvh),stitch_lod_aliases={a:b for a,b in aliases.items() if a!=b},
              material_slots=["EXFIL_Atlas_"+rig],geometry=room,textures=paths,
              uv=atlasmeta,covered_texels=int(valid.sum()),raster_interior_overlaps=int(overlaps),
              triangles_with_texel_centres=int(np.sum(polygon_count>0)),
              source_surface_hit_texels=int(matched.sum()),source_surface_fallback_texels=int((total-matched).sum()),
              source_normal_deviation_over_2_5_degrees=int(hist[3:].sum()),source_normal_deviation_degrees_histogram=hist.tolist(),
              projection="Two-sided, same-named high object only, 0.35 cm cage; closest normal-compatible ray hit. Misses retain the low surface normal.",
              material_transfer="Per-texel transfer of all ten source UV0 materials into one unique atlas. High geometry normal + source tile normal expressed in MikkTSpace. GL/Y+.",
              ao=dict(source="Combined HIGH scene, cosine-weighted hemisphere, distance-squared falloff. ORM.R = authored red channel times geometry AO.",rays=rays,radius_cm=3.5,
                      min=int(aoimg[valid].min()),median=float(np.median(aoimg[valid])),mean=float(np.mean(aoimg[valid]))),
              per_part={str(name):dict(samples=int(total[i]),ray_matches=int(matched[i])) for i,name in enumerate(low["names"])})
    (dst/"bake.json").write_text(json.dumps(info,indent=2),encoding="utf8")
    print("BAKED",rig,info["source_surface_hit_texels"],info["source_surface_fallback_texels"],flush=True)


def publish_manifest():
    rigs={}
    for rig in ("Jason","Kaitlin"):
        folder=BAKES/rig
        report=json.loads((folder/"bake.json").read_bytes())
        glb=folder/f"SM_EXFIL_{rig}_Atlas.glb";blend=glb.with_suffix(".blend")
        with glb.open("rb") as f:
            import struct
            signature,version,byte_length,chunk,tag=struct.unpack("<4sIII4s",f.read(20))
            if (signature,version,tag)!=(b"glTF",2,b"JSON") or byte_length!=glb.stat().st_size:
                raise ValueError(glb)
            gltf=json.loads(f.read(chunk))
        if not blend.is_file() or len(gltf["materials"])!=1:raise RuntimeError(f"Incomplete {rig} interchange")
        material=gltf["materials"][0];pbr=material["pbrMetallicRoughness"]
        if not all((pbr.get("baseColorTexture"),pbr.get("metallicRoughnessTexture"),material.get("normalTexture"),material.get("occlusionTexture"))):
            raise RuntimeError(f"{rig} portable material lost a packed channel")
        if not all("bufferView" in entry for entry in gltf["images"]):
            raise RuntimeError(f"{rig} portable asset has external textures")
        rigs[rig]=dict(geometry=report["geometry"],textures=report["textures"],
                       blend=blend.relative_to(BAKES).as_posix(),glb=glb.relative_to(BAKES).as_posix(),
                       bake_report=(folder/"bake.json").relative_to(BAKES).as_posix(),material_slots=report["material_slots"],
                       atlas_resolution=report["resolution"],packed_glb_images=len(gltf["images"]),
                       raster_interior_overlaps=report["raster_interior_overlaps"],
                       high_normal_transfer_percent=round(100*report["source_surface_hit_texels"]/report["covered_texels"],4),
                       geometric_ao_rays=report["ao"]["rays"])
    manifest=dict(revision="ExfilReferenceR4",rigs=rigs,
                  geometry_convention="The wear JSON contains UE centimetres in the matching native head attachment frame. World JSON retains the authored world frame. UV uses UE V direction. Blender/GLB carry the head-local frame, MikkTSpace normals and embedded maps.",
                  maps="BaseColor sRGB. NormalGL tangent-space Y+ (flip green channel on Unreal import). ORM linear R=ambient occlusion, G=roughness, B=metalness. GeometryAO is the separate unmultiplied high-mesh occlusion channel.",
                  production="Per-rig meshes use one unique UV set and one atlas material. Each original ten-material tiled master remains in Models. All paths below are relative to Bakes.")
    (BAKES/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf8")


def write_manifest():
    result={"revision":ROOT.name,"rigs":{},
            "geometry_convention":"Wear uses the native UE head-bone frame in centimetres. The GLB uses the same head pivot, MikkTSpace normals and embedded maps.",
            "maps":"BaseColor uses sRGB. NormalGL is tangent-space Y+. ORM stores occlusion, roughness and metallic in the red, green and blue channels. GeometryAO contains the unmultiplied geometry occlusion."}
    def digest(path):
        with path.open("rb") as f:
            return hashlib.file_digest(f,"sha256").hexdigest()
    for rig in ("Jason","Kaitlin"):
        folder=BAKES/rig
        stats=json.loads((folder/"bake.json").read_bytes())
        glb=folder/f"SM_EXFIL_{rig}_Atlas.glb"
        with glb.open("rb") as f:
            signature,version,length,chunk,kind=struct.unpack("<4sIIII",f.read(20))
            if (signature,version,length,kind)!=(b"glTF",2,glb.stat().st_size,0x4e4f534a):
                raise ValueError(f"Invalid GLB header: {glb}")
            scene=json.loads(f.read(chunk))
        images=scene["images"]
        if len(images)!=3 or not all("bufferView" in i for i in images) or len(scene["materials"])!=1:
            raise ValueError(f"Incomplete atlas material: {glb}")
        if stats["raster_interior_overlaps"]:
            raise ValueError(f"Overlapping interior texels: {rig}")
        row=dict(geometry=stats["geometry"],textures=stats["textures"],material_slots=stats["material_slots"],
                 atlas_resolution=stats["resolution"],packed_glb_images=len(images),
                 raster_interior_overlaps=stats["raster_interior_overlaps"],geometric_ao_rays=stats["ao"]["rays"],
                 high_normal_transfer_percent=round(100*stats["source_surface_hit_texels"]/stats["covered_texels"],4),
                 blend=f"{rig}/SM_EXFIL_{rig}_Atlas.blend",glb=glb.relative_to(BAKES).as_posix(),bake_report=f"{rig}/bake.json")
        row["source_sha256"]={key:digest(ROOT/key) for key in ("surfaces.json",*(f"Models/TS01_Helmet_{rig}_{s}.blend" for s in ("GAME","HIGH")))}
        row["output_sha256"]={key:digest(BAKES/key) for key in (*row["geometry"].values(),*row["textures"].values(),row["blend"],row["glb"])}
        result["rigs"][rig]=row
    (BAKES/"manifest.json").write_text(json.dumps(result,indent=2),encoding="utf8")


if __name__=="__main__" and sys.argv[1:]==["manifest"]:
    write_manifest()
elif __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("rig",choices=("Jason","Kaitlin"));ap.add_argument("stage",choices=("all","extract","atlas","bake","deliver","manifest"))
    ap.add_argument("--size",type=int,default=4096);ap.add_argument("--rays",type=int,default=24)
    arg=ap.parse_args();CACHE.mkdir(parents=True,exist_ok=True)
    if arg.stage in ("all","extract"):
        for stage in ("GAME","HIGH"):blender("extract",arg.rig,stage)
    if arg.stage in ("all","atlas"):atlas(arg.rig,arg.size)
    if arg.stage in ("all","bake"):bake(arg.rig,arg.size,arg.rays)
    if arg.stage in ("all","deliver"):blender("deliver",arg.rig)
    if arg.stage=="manifest":publish_manifest()
