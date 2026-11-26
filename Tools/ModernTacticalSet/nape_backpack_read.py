"""Capture the saved geometry selected by UE for each authored level of detail."""
from array import array
import gc
import hashlib
import json
from pathlib import Path
import unreal as ue

P=Path("D:/FPS3D/FPSGAME")
R=P/"SourceAssets/BackpackFit20261024/ModernTacticalHelmetPacks20261118"
out=R/"SavedLods";out.mkdir(exist_ok=True)
assets=json.loads((R/"published.json").read_bytes())["packages_sha256"]
report={}
G=ue.GeometryScript_AssetUtils;Q=ue.GeometryScript_MeshQueries;L=ue.GeometryScript_List
static=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
skeletal=ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem) or ue.new_object(ue.SkeletalMeshEditorSubsystem)
for path,digest in assets.items():
    file=P/"Content"/(path.removeprefix("/Game/")+".uasset")
    if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError("Saved package changed: "+path)
    asset=ue.load_asset(path);sk=isinstance(asset,ue.SkeletalMesh);editor=skeletal if sk else static
    copy=G.copy_mesh_from_skeletal_mesh if sk else G.copy_mesh_from_static_mesh
    n=editor.get_lod_count(asset)
    lods=[("source0",ue.GeometryScriptMeshReadLOD())]+[("render"+str(i),ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.RENDER_DATA,lod_index=i)) for i in range(n)]
    record={}
    for name,lod in lods:
        mesh,status=copy(asset,ue.DynamicMesh(),ue.GeometryScriptCopyMeshFromAssetOptions(),lod)
        if status!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Cannot read "+path+"/"+name)
        _,p,_=Q.get_all_vertex_positions(mesh,False);points=L.convert_vector_list_to_array(p)
        _,f,_=Q.get_all_triangle_indices(mesh,False);faces=L.convert_triangle_list_to_array(f)
        dest=out/path.rsplit("/",1)[1]/name;dest.mkdir(exist_ok=True,parents=True)
        (dest/"points.bin").write_bytes(array("f",(float(c) for v in points for c in (v.x,v.y,v.z))).tobytes())
        (dest/"faces.bin").write_bytes(array("i",(int(c) for t in faces for c in (t.x,t.y,t.z))).tobytes())
        record[name]=dict(vertices=len(points),triangles=len(faces),directory=str(dest))
        del mesh,points,faces,p,f;gc.collect();ue.SystemLibrary.collect_garbage()
    report[path]=record
    del asset;gc.collect();ue.SystemLibrary.collect_garbage()
    (R/"lod-read.json").write_text(json.dumps(report,indent=2))
    print("NAPE_PACK_READ",path,list(record),flush=True)
