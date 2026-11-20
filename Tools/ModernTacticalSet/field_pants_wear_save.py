"""Build all selected field trousers with their own body reference pose and distance LODs."""
from collections import Counter
import gc
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
from field_pants_wear import DEST, REV, ROOT, package_path, plan, read, sha, write
from coyote_glove_wear_bind import bones, extract
from coyote_glove_wear_save import io, remap_weights
import lower_seam_uv
import lower_wear_lods


E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
PREFIX = DEST+"/Wear/"
POLICY = PREFIX+"DA_TS01_FieldTrousers_LOD"
RECEIPT = ROOT/"wear-saved.json"


def persist(asset):
    if not asset.get_path_name().startswith(PREFIX):
        raise ValueError(asset.get_path_name())
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError("Unreal could not save "+asset.get_path_name())


def lod_settings():
    if E.does_asset_exist(POLICY):
        policy=u.load_asset(POLICY)
        if E.get_metadata_tag(policy,"TS01Revision")!=REV:
            raise RuntimeError("Occupied LOD settings path "+POLICY)
        if E.get_metadata_tag(policy,"SewnLOD")==lower_wear_lods.REVISION:
            return policy
    else:
        folder,name=POLICY.rsplit("/",1)
        factory=u.DataAssetFactory()
        factory.set_editor_property("data_asset_class",u.SkeletalMeshLODSettings)
        policy=A.create_asset(name,folder,u.SkeletalMeshLODSettings,factory)
    groups=[]
    for lod,screen in enumerate((1.,.28,.105)):
        group=u.SkeletalMeshLODGroupSettings()
        reduction=group.get_editor_property("reduction_settings")
        for key,value in dict(base_lod=lod,num_of_triangles_percentage=1.,num_of_vert_percentage=1.,
                              max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,
                              merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():
            reduction.set_editor_property(key,value)
        group.set_editor_property("reduction_settings",reduction)
        group.set_editor_property("screen_size",u.PerPlatformFloat(default=screen))
        groups.append(group)
    policy.set_editor_property("lod_groups",groups)
    E.set_metadata_tag(policy,"TS01Revision",REV)
    E.set_metadata_tag(policy,"SewnLOD",lower_wear_lods.REVISION)
    persist(policy)
    return policy


def separate_sewn_sheets(data):
    # Fabric, the folded bellows and its sewn return may meet at one edge.
    # Each UE dynamic-mesh edge accepts two faces. Give the extra sheet its
    # own coincident wedges, preserving positions, normals, UV and binding.
    wedges={}
    incidence=Counter()
    seen=set()
    splits=0
    for index,face in enumerate(data["triangles"]):
        keys=[(v,*[round(x,7) for x in (*data["normals"][index][c],*data["uv"][index][c])])
              for c,v in enumerate(face)]
        corners=[wedges.setdefault(key,len(wedges)) for key in keys]
        edges=[tuple(sorted((v,corners[i-1]))) for i,v in enumerate(corners)]
        triangle=tuple(sorted(corners))
        if triangle in seen or any(incidence[edge]>=2 for edge in edges):
            new=[]
            for source in face:
                new.append(len(data["positions"]))
                data["positions"].append(data["positions"][source])
                data["weights"].append(data["weights"][source])
            data["triangles"][index]=new
            splits+=1
        else:
            seen.add(triangle)
            incidence.update(edges)
    return splits


def save_mesh(row,path,source_sha,policy):
    donor=u.load_asset(row["previous"])
    if not donor or sha(package_path(row["previous"]))!=row["donor_sha256"]:
        raise RuntimeError("The installed native trousers changed during tailoring: "+row["previous"])
    native=extract(donor)
    data=read(path)
    walls=lower_seam_uv.unfold_sidewalls(data,"FT_",8.)
    expected=dict(skeleton=donor.skeleton.get_path_name(),bones=bones(native))
    remap_weights(data,expected)
    materials=[u.load_asset(p) for p in data["materials"]]
    slots=data["material_slots"]
    if len(slots)!=len(materials) or not all(materials):
        raise RuntimeError("Missing a cloth or original skin material for "+path.name)
    donor_skin={section.material_interface.get_path_name() for section in donor.materials
                if str(section.material_slot_name).startswith("NATIVE:") and section.material_interface}
    authored_skin={material.get_path_name() for slot,material in zip(slots,materials) if slot.startswith("NATIVE:")}
    if donor_skin and donor_skin!=authored_skin:
        raise ValueError("The native skin insert material differs from the fitted trousers: "+path.name)
    splits=separate_sewn_sheets(data)
    dm=io.dynamic(data,native)
    triangles=len(data["triangles"])
    if dm.get_triangle_count()!=triangles:
        raise ValueError("Source triangles were lost during import: "+path.name)
    package=row["asset"].split(".")[0]
    folder,name=package.rsplit("/",1)
    if E.does_asset_exist(package):
        asset=u.load_asset(package)
        if E.get_metadata_tag(asset,"TS01Revision")!=REV:
            raise RuntimeError("Another revision already occupies "+package)
    else:
        asset=A.duplicate_asset(name,folder,donor)
    if not asset:
        raise RuntimeError("Cannot create "+package)
    E.set_metadata_tag(asset,"TS01Revision",REV)
    asset.set_editor_property("physics_asset",None)
    asset.set_editor_property("lod_settings",None)
    prior=S.get_lod_count(asset)
    if prior>1 and not S.remove_lods(asset,list(range(prior-1,0,-1))):
        raise RuntimeError("Cannot detach the previous distance meshes: "+package)
    build=S.get_lod_build_settings(asset,0)
    build.set_editor_property("use_full_precision_u_vs",True)
    build.set_editor_property("recompute_normals",False)
    S.set_lod_build_settings(asset,0,build)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=slots,
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD(lod_index=0))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot write native trousers: "+package)
    lower_wear_lods.write(asset,lower_wear_lods.meshes(data,native,"FT_"),options)
    asset.set_editor_property("lod_settings",policy)
    provenance=u.new_object(u.AssetImportData,outer=asset)
    provenance.scripted_add_filename(str(path),0,"Field trousers native sewing pattern")
    asset.set_editor_property("asset_import_data",provenance)
    E.set_metadata_tag(asset,"PatternSHA256",source_sha)
    E.set_metadata_tag(asset,"TS01NativeDonor",row["previous"])
    persist(asset)
    lods=[extract(asset,index).get_triangle_count() for index in range(3)]
    if not 0<lods[2]<lods[1]<lods[0] or lods[0]!=triangles:
        raise RuntimeError(f"Distance meshes failed to build for {package}: {lods}")
    return dict(asset=asset.get_path_name(),source_file=row["source"],source_sha256=source_sha,
                seam_uv=lower_seam_uv.REVISION,wear_lod_pattern=lower_wear_lods.REVISION,unfolded_faces=walls,
                package_sha256=sha(package_path(package)),previous=row["previous"],skeleton=expected["skeleton"],
                material_slots=slots,materials=[m.get_path_name() for m in materials],render_lods=lods,
                separated_sheet_triangles=splits)


def main():
    read(ROOT/"saved-surfaces.json")
    work=plan()
    policy=lod_settings()
    saved=read(RECEIPT) if RECEIPT.is_file() else {"assets":{}}
    saved["policy"]=dict(asset=policy.get_path_name(),sha256=sha(package_path(POLICY)))
    for key,row in work["assets"].items():
        source=ROOT/row["source"]
        if not source.is_file():
            continue
        fingerprint=sha(source)
        old=saved["assets"].get(key,{})
        if old.get("wear_lod_pattern")==lower_wear_lods.REVISION and old.get("seam_uv")==lower_seam_uv.REVISION and old.get("source_sha256")==fingerprint and package_path(row["asset"]).is_file() and sha(package_path(row["asset"]))==old.get("package_sha256"):
            continue
        print("FIELD_TROUSERS_BUILD",key,flush=True)
        saved["assets"][key]=save_mesh(row,source,fingerprint,policy)
        saved["complete"]=False
        write(RECEIPT,saved)
        print("FIELD_TROUSERS_SAVED",key,saved["assets"][key]["render_lods"],flush=True)
        gc.collect()
        u.SystemLibrary.collect_garbage()
    saved["complete"]=all(key in saved["assets"] and (ROOT/row["source"]).is_file() and
                          sha(ROOT/row["source"])==saved["assets"][key]["source_sha256"] for key,row in work["assets"].items())
    write(RECEIPT,saved)


if __name__=="__main__":
    main()
