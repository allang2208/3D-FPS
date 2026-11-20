"""Install the sewn sleeves in their original viewmodel reference poses."""
import gc
import gzip
import json
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
from coyote_glove_wear_bind import bones, extract
from coyote_glove_wear_save import io, remap_weights
from field_pants_wear_save import separate_sewn_sheets
from patrol_shirt_sleeves import DEST, REV, ROOT, SLOTS, package_path, plan, read, sha, write
from ridge_boots_wear_save import import_lods


E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
POLICY = DEST + "/Sleeves/DA_TS01_PatrolSleeves_LOD"
RECEIPT = ROOT / "sleeves-saved.json"


def save(asset):
    if not asset.get_path_name().startswith(DEST + "/Sleeves/") or not E.save_loaded_asset(asset,False):
        raise RuntimeError("Cannot save " + asset.get_path_name())


def lod_policy():
    if E.does_asset_exist(POLICY):
        settings = u.load_asset(POLICY)
        if E.get_metadata_tag(settings,"TS01Revision") != REV:
            raise RuntimeError("Occupied LOD policy " + POLICY)
        return settings
    folder,name = POLICY.rsplit("/",1)
    factory = u.DataAssetFactory()
    factory.set_editor_property("data_asset_class",u.SkeletalMeshLODSettings)
    settings = A.create_asset(name,folder,u.SkeletalMeshLODSettings,factory)
    groups = []
    for ratio,screen in ((1.,1.),(.42,.23),(.14,.08)):
        group = u.SkeletalMeshLODGroupSettings()
        reduction = group.get_editor_property("reduction_settings")
        for key,value in dict(base_lod=0,num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,
                              max_bones_per_vertex=8,lock_edges=ratio>.2,enforce_bone_boundaries=True,
                              merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():
            reduction.set_editor_property(key,value)
        group.set_editor_property("reduction_settings",reduction)
        group.set_editor_property("screen_size",u.PerPlatformFloat(default=screen))
        groups.append(group)
    settings.set_editor_property("lod_groups",groups)
    E.set_metadata_tag(settings,"TS01Revision",REV)
    save(settings)
    return settings


def install(rig,row,policy,source_hash):
    native = u.load_asset(row["previous"])
    if not native or sha(package_path(row["previous"])) != row["donor_sha256"]:
        raise RuntimeError("Native sleeve changed during tailoring " + rig)
    source = ROOT / row["authored"]
    with gzip.open(source,"rt",encoding="utf8") as stream:
        data = json.load(stream)
    reference = extract(native)
    skeleton = native.skeleton.get_path_name()
    remap_weights(data,dict(skeleton=skeleton,bones=bones(reference)))
    mats = [u.load_asset(m) for m in data["materials"]]
    if data["material_slots"] != SLOTS or not all(mats):
        raise ValueError("Incomplete sleeve material set on " + rig)
    separated = separate_sewn_sheets(data)
    mesh = io.dynamic(data,reference)
    if mesh.get_triangle_count() != len(data["triangles"]):
        raise RuntimeError("Native import omitted sleeve triangles on " + rig)
    target = row["asset"].split(".")[0]
    if E.does_asset_exist(target):
        asset = u.load_asset(target)
        if E.get_metadata_tag(asset,"TS01Revision") != REV:
            raise RuntimeError("Another producer owns " + target)
    else:
        folder,name = target.rsplit("/",1)
        asset = A.duplicate_asset(name,folder,native)
        if not asset:
            raise RuntimeError("Cannot create " + target)
    E.set_metadata_tag(asset,"TS01Revision",REV)
    import_lods(asset,mesh,mats,SLOTS,policy)
    info = u.new_object(u.AssetImportData,outer=asset)
    info.scripted_add_filename(str(source),0,"Patrol shirt native sleeve pattern")
    asset.set_editor_property("asset_import_data",info)
    E.set_metadata_tag(asset,"PatternSHA256",source_hash)
    E.set_metadata_tag(asset,"TS01NativeDonor",row["previous"])
    save(asset)
    return dict(asset=asset.get_path_name(),previous=row["previous"],skeleton=skeleton,
                patterns=list(data["parts"]),source_file=row["authored"],source_sha256=source_hash,
                material_slots=SLOTS,materials=[m.get_path_name() for m in mats],
                package_sha256=sha(package_path(target)),separated_triangles=separated,
                render_lods=[extract(asset,i).get_triangle_count() for i in range(3)])


def main():
    read(ROOT/"saved-surfaces.json")
    policy = lod_policy()
    rigs = plan()["rigs"]
    saved = read(RECEIPT) if RECEIPT.is_file() else dict(assets={})
    saved.update(policy=policy.get_path_name(),complete=False)
    for rig,row in rigs.items():
        source = ROOT / row["authored"]
        source_hash = sha(source)
        package = package_path(row["asset"])
        previous = saved["assets"].get(rig,{})
        if previous.get("source_sha256") == source_hash and package.is_file() and sha(package)==previous.get("package_sha256"):
            continue
        saved["assets"][rig] = install(rig,row,policy,source_hash)
        write(RECEIPT,saved)
        print("SLEEVE_SAVED",rig,saved["assets"][rig]["render_lods"],flush=True)
        gc.collect()
        u.SystemLibrary.collect_garbage()
    saved["complete"] = set(rigs) == set(saved["assets"])
    write(RECEIPT,saved)


if __name__ == "__main__":
    main()
