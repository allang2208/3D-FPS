"""Fit the nine original UV-mapped scans in centimetres. Run inside background Blender."""
from pathlib import Path
import json
import math
import os
import struct
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stable_profile import DISTANCES,NORTH,SOUTH

PROJECT=Path(__file__).resolve().parents[3]
ROOT=PROJECT/"SourceAssets/HillsVillageStable"
OUT=ROOT/"AssemblyR1/Exchange"
OUT.mkdir(parents=True,exist_ok=True)
SIZES={"A02":(779,19,517),"A03":(405,22,300),"A04":(146,8,125),"A05":(495,14,165),
       "A06":(240,16,135),"A07":(225,12,140),"A08":(260,30,115),"A09":(205,78,65)}
TARGETS={"A01_Roof":117000,"A01_Bent":58000,"A02":71000,"A03":68000,"A04":44000,
         "A05":38000,"A06":26500,"A07":43000,"A08":42000,"A09":67000}

def arrays(path):
    with path.open("rb") as f:
        f.seek(12)
        size,kind=struct.unpack("<II",f.read(8))
        spec=json.loads(f.read(size))
        f.seek(8,1)
        address=f.tell()
        prim=spec["meshes"][0]["primitives"][0]
        def get(index,n):
            ac=spec["accessors"][index]; view=spec["bufferViews"][ac["bufferView"]]
            typ=np.dtype({5126:"<f4",5123:"<u2",5125:"<u4",5121:"u1"}[ac["componentType"]])
            f.seek(address+view.get("byteOffset",0))
            raw=f.read(view["byteLength"])
            vals=np.ndarray((ac["count"],n),typ,raw,ac.get("byteOffset",0),
                            (view.get("byteStride",n*typ.itemsize),typ.itemsize)).copy()
            return vals.astype("f")/np.iinfo(typ).max if ac.get("normalized") else vals
        return get(prim["attributes"]["POSITION"],3),get(prim["attributes"]["TEXCOORD_0"],2),get(prim["indices"],1).reshape(-1,3)

def write(name,source,xyz,uv,faces):
    # Incoming recipe coordinates are UE-local. UVs remain the original Meshy atlas.
    xyz=xyz.astype("f");xyz[:,1]*=-1
    used,ind=np.unique(faces,return_inverse=True)
    pts,remap=np.unique(xyz[used],axis=0,return_inverse=True)
    idx=remap[ind].reshape(-1,3)
    good=(idx[:,0]!=idx[:,1])&(idx[:,1]!=idx[:,2])&(idx[:,0]!=idx[:,2])
    idx=idx[good];texcoords=uv[faces[good].reshape(-1)].copy();texcoords[:,1]=1-texcoords[:,1]
    mesh=bpy.data.meshes.new(name)
    mesh.vertices.add(len(pts));mesh.vertices.foreach_set("co",pts.ravel())
    mesh.loops.add(idx.size);mesh.loops.foreach_set("vertex_index",idx.astype("i").ravel())
    mesh.polygons.add(len(idx));mesh.polygons.foreach_set("loop_start",np.arange(0,idx.size,3,dtype="i"))
    mesh.update(calc_edges=True)
    mesh.uv_layers.new(name="Atlas").uv.foreach_set("vector",texcoords.ravel())
    mesh.polygons.foreach_set("use_smooth",np.ones(len(idx),bool))
    mesh.materials.append(bpy.data.materials.get(source) or bpy.data.materials.new(source))
    obj=bpy.data.objects.new("SM_Stable_"+name,mesh);bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    mod=obj.modifiers.new("Preserve structural edges and UV islands","DECIMATE")
    mod.ratio=min(1,TARGETS[name]/len(idx));mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.scene.unit_settings.system="METRIC";bpy.context.scene.unit_settings.scale_length=.01
    name_out=obj.name
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name_out+".fbx")),use_selection=True,object_types={"MESH"},
        axis_forward="Y",axis_up="Z",apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
        mesh_smooth_type="FACE",use_tspace=True,bake_anim=False,path_mode="STRIP",embed_textures=False)
    print("STABLE_EXPORTED",name_out,len(obj.data.polygons),flush=True)
    bpy.data.objects.remove(obj,do_unlink=True);bpy.data.orphans_purge(do_recursive=True)

def fit(part):
    p,uv,f=arrays(ROOT/"MeshyR1"/part/"downloads/model_urls_glb.glb")
    # Find the straight long edge in the horizontal plane independent of the submitted camera.
    x,h,t=p.T
    if part!="A01":
        hz=p[:,[0,2]]
        _,axes=np.linalg.eigh(np.cov(hz.T))
        v=axes[:,-1];v=v if v[0]>0 else -v
        x=hz@v;t=hz@np.array([-v[1],v[0]])
    normalize=lambda v:(v-v.min())/(v.max()-v.min())
    x,h,t=map(normalize,(x,h,t))
    if part=="A01":
        # Source ridge runs along glTF Z. Use the intact middle roof span and only one end bent.
        cross=np.interp(x,[0,.065,.10,.14,.17,.84,.87,.90,.94,1],[-431,-408,-394,-379,-366,365,380,391,405,431])
        z=np.interp(h,[0,.50,.54,.99,1],[0,282,300,528,530])
        roofline=.512+.915*np.minimum(x,1-x)
        slab=(h-roofline)[f].max(axis=1)>-.026
        along=(.5-t)*880.
        roof=slab&(along[f].max(1)>=-220)&(along[f].min(1)<=220)
        write("A01_Roof",part,np.column_stack((np.clip(along,-220,220),cross,z)),uv,f[roof])
        bent=(t[f].mean(1)>.786)&(t[f].mean(1)<.963)&((h-roofline)[f].mean(1)<-.022)
        write("A01_Bent",part,np.column_stack(((.862-t)*220,cross,z)),uv,f[bent])
        return
    w,d,ht=SIZES[part];xx=(.5-x)*w;yy=(.5-t)*d;zz=h*ht
    if part=="A02":
        # Fit the sloping verge beneath the actual slate skin, including the eave ends.
        bins=np.linspace(0,1,129)
        tops=np.array([h[(x>=a)&(x<=b)].max(initial=.05) for a,b in zip(bins,bins[1:])])
        rim=np.interp(x,(bins[:-1]+bins[1:])*.5,tops)
        # Gable local X becomes village Y after rotation. Both ends meet the lower slate skin.
        y=-xx
        top=np.where(y<0,np.interp(abs(y),DISTANCES,NORTH),np.interp(abs(y),DISTANCES,SOUTH))
        zz=h/np.maximum(rim,.2)*(top-11)
    if part=="A03":
        # Find both internal jambs on the scan; preserve a true 150 cm door opening.
        xxmid=np.sort(x[(h>.1)&(h<.76)&(x>.22)&(x<.78)])
        i=np.argmax(np.diff(xxmid));a,b=xxmid[i:i+2]
        if b-a<.1:raise ValueError("Could not isolate stall doorway")
        xx=np.interp(x,[0,a,b,1],[w/2,76,-76,-w/2])
        header=h[(x>a+.035)&(x<b-.035)]
        bottom=np.quantile(header,.002)
        zz=np.interp(h,[0,bottom,1],[0,240,ht])
    if part in ("A04","A07"):
        # The existing ColdSteelDoor hinge rotates about local Z, leaf width along local Y.
        xx=(.5-t)*d;yy=(x-.5)*w
    if part=="A09":
        # The scan bridges part of its cavity with a thin high polygon skin.
        # Recess that skin into the bowl under the new water, preserving the stone rim UVs.
        radial=np.hypot(np.maximum(abs(xx)-51,0)*.81,yy)
        indent=np.clip((26-radial)/8,0,1)
        zz-=18*indent*indent*(3-2*indent)*np.clip((h-.63)/.18,0,1)
    write(part,part,np.column_stack((xx,yy,zz)),uv,f)
bpy.ops.wm.read_factory_settings(use_empty=True)
for id in (sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["A01",*SIZES]):
    fit(id)
