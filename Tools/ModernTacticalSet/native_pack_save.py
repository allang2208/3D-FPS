"""Save original-volume pack fits and capture their actual source/render geometry before exit."""
from array import array
import gc
import hashlib
import json
import os
from pathlib import Path
import runpy

import unreal as ue

P=Path(__file__).resolve().parents[2]
R=P/"SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118"
os.environ["BACKPACK_FIT_RUN_DIR"]=str(R)
os.environ["BACKPACK_FIT_BATCH_SIZE"]="24"
runpy.run_path(str(P/"Tools/BackpackFit/save_assets.py"),run_name="__main__")
receipt=json.loads((R/"saved_assets.json").read_bytes())
if not receipt["completed"]:raise RuntimeError("Not all native backpack fits were saved")
editor=ue.EditorAssetLibrary
S=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
K=ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem) or ue.new_object(ue.SkeletalMeshEditorSubsystem)
G=ue.GeometryScript_AssetUtils;Q=ue.GeometryScript_MeshQueries;L=ue.GeometryScript_List
def bindings(asset,skeletal):
    slots=asset.get_editor_property("materials" if skeletal else "static_materials")
    return [m.material_interface.get_path_name() if m.material_interface else None for m in slots]


report={}
active=json.loads((R/"authored.json").read_bytes())
previous=json.loads((R/"lod-read.json").read_bytes()) if (R/"lod-read.json").exists() else {}
for kind in ("meshes","statics"):
    selected={row["asset"] for row in active["rows" if kind=="meshes" else "statics"]}
    for path,entry in receipt[kind].items():
        if path not in selected:continue
        disk=P/"Content"/(path.removeprefix("/Game/")+".uasset")
        verified=previous.get(path)
        if verified and verified["package_sha256"]==hashlib.sha256(disk.read_bytes()).hexdigest() and all(
            (Path(level["folder"])/name).is_file() for level in verified["levels"].values() for name in ("positions.bin","faces.bin")):
            report[path]=verified
            continue
        asset=ue.load_asset(path);sk=kind=="meshes"
        copy=G.copy_mesh_from_skeletal_mesh if sk else G.copy_mesh_from_static_mesh
        count=(K if sk else S).get_lod_count(asset)
        levels=[("source0",ue.GeometryScriptMeshReadLOD())]+[("render"+str(i),ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.RENDER_DATA,lod_index=i)) for i in range(count)]
        donor=ue.load_asset(entry["source"])
        materials=bindings(asset,sk)
        if materials!=bindings(donor,sk):raise RuntimeError("Material bindings changed: "+path)
        skeleton=asset.get_editor_property("skeleton").get_path_name() if sk else None
        if sk and skeleton!=donor.get_editor_property("skeleton").get_path_name():raise RuntimeError("Rig changed: "+path)
        donor_dm,outcome=copy(donor,ue.DynamicMesh(),ue.GeometryScriptCopyMeshFromAssetOptions(),ue.GeometryScriptMeshReadLOD())
        if outcome!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Cannot inspect donor "+entry["source"])
        donor_uv=Q.get_num_uv_sets(donor_dm)
        record=dict(package_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),materials=materials,skeleton=skeleton,source_uv_channels=donor_uv,levels={})
        del donor,donor_dm
        for key,lod in levels:
            dm,status=copy(asset,ue.DynamicMesh(),ue.GeometryScriptCopyMeshFromAssetOptions(),lod)
            if status!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path+"/"+key)
            _,ps,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(ps)
            _,fs,_=Q.get_all_triangle_indices(dm,False);faces=L.convert_triangle_list_to_array(fs)
            folder=R/"SavedLods"/path.rsplit("/",1)[-1]/key;folder.mkdir(parents=True,exist_ok=True)
            (folder/"positions.bin").write_bytes(array("f",(c for p in points for c in (p.x,p.y,p.z))).tobytes())
            (folder/"faces.bin").write_bytes(array("i",(c for t in faces for c in (t.x,t.y,t.z))).tobytes())
            channels=Q.get_num_uv_sets(dm)
            if key=="source0" and channels!=donor_uv:raise RuntimeError("UV channels changed: "+path)
            record["levels"][key]=dict(vertices=len(points),triangles=len(faces),folder=str(folder),uv_channels=channels)
            if sk and key=="source0":
                _,colors,valid,_=ue.GeometryScript_VertexColors.get_mesh_per_vertex_colors(dm,False)
                if not valid:raise RuntimeError("Missing backpack displacement mask: "+path)
                reds=ue.GeometryScript_List.convert_color_list_to_array(colors)
                record["levels"][key]["mask_sha256"]=hashlib.sha256(array("f",(c.r for c in reds)).tobytes()).hexdigest()
                del colors,reds
            del points,faces,ps,fs,dm;gc.collect();ue.SystemLibrary.collect_garbage()
        report[path]=record
        (R/"lod-read.json").write_text(json.dumps(report,indent=2))
        del asset;gc.collect();ue.SystemLibrary.collect_garbage()
        print("NATIVE_TS01_BACKPACK_READ",path,count,flush=True)
(R/"lod-read.json").write_text(json.dumps(report,indent=2))
