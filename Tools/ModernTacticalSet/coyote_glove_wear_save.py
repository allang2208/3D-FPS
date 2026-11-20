"""Save the tailored gloves in the original native reference frames, with reduced distance LODs."""
from collections import Counter, defaultdict
import gc
import gzip
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
from coyote_glove_wear import DEST,P,REV,ROOT,SLOTS,WEAR,package_path,plan,read,sha,write
from coyote_glove_wear_bind import bones,extract
import lower_seam_uv

E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
G=u.GeometryScript_AssetUtils
Q=u.GeometryScript_MeshQueries
B=u.GeometryScript_BoneWeights
L=u.GeometryScript_List
PREFIX=DEST+"/Wear"
POLICY=PREFIX+"/DA_TS01_CoyoteGloves_LOD"
OUTPUT=ROOT/"wear-saved.json"
LEVELS=((1.,1.),(.60,.20),(.30,.075))

spec=importlib.util.spec_from_file_location("ts01_glove_native_io",P/"Tools/ChainmailPants/save_assets.py")
io=importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)


def persist(asset):
    if not asset.get_path_name().startswith(PREFIX+"/"):
        raise RuntimeError("Unexpected glove write target "+asset.get_path_name())
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError("Unreal could not save "+asset.get_path_name())


def lod_policy():
    if E.does_asset_exist(POLICY):
        policy=u.load_asset(POLICY)
        if E.get_metadata_tag(policy,"TS01Revision")!=REV:
            raise RuntimeError("Another producer owns "+POLICY)
        return policy
    folder,name=POLICY.rsplit("/",1)
    factory=u.DataAssetFactory()
    factory.set_editor_property("data_asset_class",u.SkeletalMeshLODSettings)
    policy=A.create_asset(name,folder,u.SkeletalMeshLODSettings,factory)
    levels=[]
    for ratio,screen in LEVELS:
        group=u.SkeletalMeshLODGroupSettings()
        settings=group.get_editor_property("reduction_settings")
        for field,value in dict(base_lod=0,num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,
                                max_bones_per_vertex=8,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,
                                welding_threshold=0.,recalc_normals=False,lock_edges=True).items():
            settings.set_editor_property(field,value)
        group.set_editor_property("screen_size",u.PerPlatformFloat(default=screen))
        group.set_editor_property("reduction_settings",settings)
        levels.append(group)
    policy.set_editor_property("lod_groups",levels)
    E.set_metadata_tag(policy,"TS01Revision",REV)
    persist(policy)
    return policy


def inspect_binding(asset,data,expected,rig):
    source=extract(asset)
    if bones(source)!=expected["bones"]:
        raise RuntimeError("Saved mesh reference hierarchy or bind transforms differ from the installed donor")
    source_rows=sorted({i for tri in data["triangles"] for i in tri})
    sample=[source_rows[i] for i in range(0,len(source_rows),max(1,len(source_rows)//160))]
    indices=defaultdict(list)
    cell=lambda p:tuple(math.floor(value*100) for value in p)
    for s in sample:
        indices[cell(data["positions"][s])].append(s)
    hits={s:[] for s in sample}
    _,vs,_=Q.get_all_vertex_positions(source,False)
    points=L.convert_vector_list_to_array(vs)
    for vertex,v in enumerate(points):
        p=(v.x,v.y,v.z)
        ix,iy,iz=cell(p)
        candidates=indices.get((ix,iy,iz),[])
        # Only search near a rounding boundary in the uncommon miss case.
        if not candidates and any(abs(x*100-round(x*100))<.002 for x in p):
            candidates=itertools.chain.from_iterable(indices.get((ix+dx,iy+dy,iz+dz),[]) for dx,dy,dz in itertools.product((-1,0,1),repeat=3))
        matching=[s for s in candidates if math.dist(p,data["positions"][s])<.003]
        if not matching:
            continue
        _,weights,valid=B.get_vertex_bone_weights(source,vertex)
        if not valid:
            raise RuntimeError("No weights on saved authored surface")
        observed={w.bone_index:w.weight for w in weights if w.weight>0}
        for s in matching:
            desired=dict(data["weights"][s])
            error=max(abs(observed.get(b,0.)-desired.get(b,0.)) for b in observed.keys()|desired.keys())
            hits[s].append(error)
    missing=sum(not h for h in hits.values())
    worst=max((min(h) for h in hits.values() if h),default=1.)
    if missing or worst>.012:
        raise RuntimeError(f"Glove weight readback: {missing} missing samples, {worst:.6f} maximum influence delta")
    if rig in ("M16","Super90"):
        _,fs,_=Q.get_all_triangle_indices(source,False)
        _,mi,_=u.GeometryScript_Materials.get_all_triangle_material_i_ds(source)
        surface={i for i,name in enumerate(data["material_slots"]) if name in ("CG_Knit","CG_Suede","CG_Stretch")}
        ids=set()
        for face,mat in zip(L.convert_triangle_list_to_array(fs),L.convert_index_list_to_array(mi)):
            if mat in surface:
                ids.update((face.x,face.y,face.z))
        positions=[]
        weights=[]
        observed_points=set()
        for vertex in sorted(ids):
            v=points[vertex]
            coords=(v.x,v.y,v.z)
            key=tuple(round(x,5) for x in coords)
            if key in observed_points:
                continue
            observed_points.add(key)
            _,row,valid=B.get_vertex_bone_weights(source,vertex)
            if not valid:
                raise RuntimeError("Missing saved glove skin weights")
            positions.append(coords)
            weights.append([(w.bone_index,w.weight) for w in row if w.weight>0.])
        with gzip.open(WEAR/f"{rig}-saved-hand.json.gz","wt",encoding="utf8") as stream:
            json.dump(dict(positions=positions,weights=weights,bones=expected["bones"],triangles=[],triangle_materials=[]),stream,separators=(",",":"))
    return dict(samples=len(sample),max_influence_delta=round(worst,6),reference_bones=len(expected["bones"]))


def remap_weights(data,expected):
    if data.get("skeleton") and data["skeleton"]!=expected["skeleton"]:
        raise RuntimeError(f"Authored skeleton {data['skeleton']} differs from native {expected['skeleton']}")
    if "bones" in data:
        new={b["name"]:b["index"] for b in expected["bones"]}
        mapping={b["index"]:new[b["name"]] for b in data["bones"] if b["name"] in new}
        used={idx for row in data["weights"] for idx,_ in row}
        if not used<=mapping.keys():
            raise RuntimeError("Authored influence lacks a matching native bone")
        if any(idx!=mapping[idx] for idx in used):
            data["weights"]=[[[mapping[i],w] for i,w in row] for row in data["weights"]]


def save_rig(rig,row,expected,source_file,signature,policy):
    base=u.load_asset(row["previous"])
    if base.skeleton.get_path_name()!=expected["skeleton"] or sha(package_path(row["previous"]))!=row["donor_package_sha256"]:
        raise RuntimeError("The native glove donor changed during production: "+rig)
    data=read(source_file)
    seam_faces=lower_seam_uv.unfold_sidewalls(data,"CG_",4.)
    remap_weights(data,expected)
    names=data["material_slots"]
    if not names or set(names)-set(SLOTS) or len(names)!=len(set(names)):
        raise ValueError(f"Unexpected glove material slots for {rig}: {names}")
    mats=[u.load_asset(DEST+"/Materials/M_"+name) for name in names]
    if not all(mats):
        raise RuntimeError("Missing CoyoteGlovesR2 PBR material")
    native=extract(base)
    mesh=io.dynamic(data,native)
    if mesh.get_triangle_count()!=len(data["triangles"]):
        raise RuntimeError("Lost source triangles when building "+rig)
    path=row["asset"].split(".")[0]
    folder,name=path.rsplit("/",1)
    if E.does_asset_exist(path):
        asset=u.load_asset(path)
        if E.get_metadata_tag(asset,"TS01Revision")!=REV:
            raise RuntimeError("Another asset occupies "+path)
    else:
        asset=A.duplicate_asset(name,folder,base)
    if not asset:
        raise RuntimeError("Could not duplicate native glove for "+rig)
    E.set_metadata_tag(asset,"TS01Revision",REV)
    asset.set_editor_property("physics_asset",None)
    asset.set_editor_property("lod_settings",None)
    old_levels=S.get_lod_count(asset)
    if old_levels>1 and not S.remove_lods(asset,list(range(old_levels-1,0,-1))):
        raise RuntimeError("Could not clear old authored glove distance meshes for "+rig)
    settings=S.get_lod_build_settings(asset,0)
    settings.set_editor_property("use_full_precision_u_vs",True)
    S.set_lod_build_settings(asset,0,settings)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=names,
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(mesh,asset,options,u.GeometryScriptMeshWriteLOD(lod_index=0))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot write authored glove "+rig)
    asset.set_editor_property("lod_settings",policy)
    if not S.regenerate_lod(asset,3,True,False):
        raise RuntimeError("Cannot build the authored glove distance LODs")
    imported=u.new_object(u.AssetImportData,outer=asset)
    imported.scripted_add_filename(str(source_file),0,"Coyote glove, native skinned geometry")
    asset.set_editor_property("asset_import_data",imported)
    E.set_metadata_tag(asset,"GloveSourceSHA256",signature)
    E.set_metadata_tag(asset,"NativeGloveDonor",row["previous"])
    persist(asset)
    if asset.skeleton.get_path_name()!=expected["skeleton"]:
        raise RuntimeError("Unexpected skeleton after native glove save")
    assigned=[section.material_interface.get_path_name() for section in asset.materials]
    if assigned!=[mat.get_path_name() for mat in mats]:
        raise RuntimeError(f"Incorrect saved material order on {rig}: {assigned}")
    levels=[]
    for level in range(3):
        rendered=extract(asset,level)
        _,indices,ok=u.GeometryScript_Materials.get_all_triangle_material_i_ds(rendered)
        if not ok:
            raise RuntimeError("Cannot read native glove section IDs")
        counts=Counter(L.convert_index_list_to_array(indices))
        levels.append(dict(triangles=rendered.get_triangle_count(),sections={names[i]:n for i,n in sorted(counts.items())}))
    counts=[l["triangles"] for l in levels]
    if not (0<counts[2]<counts[1]<counts[0]) or counts[0]!=len(data["triangles"]):
        raise RuntimeError(f"Invalid glove render geometry counts on {rig}: {counts}")
    binding=inspect_binding(asset,data,expected,rig)
    return dict(asset=asset.get_path_name(),source_file=source_file.relative_to(ROOT).as_posix(),source_sha256=signature,
                package_sha256=sha(package_path(path)),donor_sha256=row["donor_package_sha256"],skeleton=expected["skeleton"],
                binding=binding,render_lods=levels,materials=assigned,seam_uv=lower_seam_uv.REVISION,unfolded_faces=seam_faces)


def main():
    capture=read(WEAR/"native-bindings.json")
    read(ROOT/"saved-surfaces.json")
    data=plan()["rigs"]
    receipt=read(OUTPUT) if OUTPUT.is_file() else {"rigs":{}}
    policy=lod_policy()
    receipt["policy"]=dict(asset=policy.get_path_name(),sha256=sha(package_path(policy.get_path_name())))
    selected=os.environ.get("TS01_COYOTE_WEAR_RIGS","").split(",")
    for rig,row in data.items():
        if selected[0] and rig not in selected:
            continue
        path=ROOT/"Authored"/f"gloves_{rig}.json"
        if not path.exists():
            continue
        signature=sha(path)
        old=receipt["rigs"].get(rig,{})
        if old.get("seam_uv")==lower_seam_uv.REVISION and old.get("source_sha256")==signature and package_path(row["asset"]).is_file() and sha(package_path(row["asset"]))==old.get("package_sha256"):
            continue
        print("COYOTE_GLOVE_SAVING",rig,flush=True)
        receipt["rigs"][rig]=save_rig(rig,row,capture[rig],path,signature,policy)
        receipt["complete"]=False
        write(OUTPUT,receipt)
        print("COYOTE_GLOVE_SAVED",rig,[r["triangles"] for r in receipt["rigs"][rig]["render_lods"]],flush=True)
        gc.collect()
        u.SystemLibrary.collect_garbage()
    receipt["complete"]=all(r in receipt["rigs"] and (ROOT/"Authored"/f"gloves_{r}.json").is_file() and
        receipt["rigs"][r].get("seam_uv")==lower_seam_uv.REVISION and
        receipt["rigs"][r]["source_sha256"]==sha(ROOT/"Authored"/f"gloves_{r}.json") for r in data)
    write(OUTPUT,receipt)


if __name__=="__main__":
    main()
