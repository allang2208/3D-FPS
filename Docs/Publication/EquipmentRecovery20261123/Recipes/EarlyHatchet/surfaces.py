"""Reconstruct archived R2 surface inputs from the retained Blender scene and published curve."""
from pathlib import Path
import ast, hashlib, json, shutil, sys
import bpy
import numpy as np
from mathutils import Vector
work = Path(__file__).resolve().parent
prod = Path("D:/FPS3D/FPSGAME")
src = prod/"SourceAssets/OneHandAxe20261101/BladeVariants20261102"
replay = Path("F:/FPSGAME-Recovery-Work-20261120/NovemberFurtherRecovery/BladeR2")
archive = json.loads((prod/"Docs/Publication/Hatchet20261104/cleanup-manifest.json").read_bytes())["files"]
def old(kind, name):
    return next(x for x in archive if x["source"].endswith("OtherBladesFactoryFinish20261104/"+kind+"/"+name))
names = ("HeavyCleaver", "FoldedArc")
for kind in names:
    body_name="SM_TacticalHatchet_Head_"+kind+"_R2"
    directory=work/"R2Surface"/kind
    (directory/"Textures").mkdir(parents=True,exist_ok=True)
    (directory/"Before/Textures").mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(replay/(kind+"_Editable.blend")))
    mesh=bpy.data.objects[body_name].data
    mesh.calc_loop_triangles()
    mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
    tri=list(mesh.loop_triangles)
    np.savez_compressed(directory/"target_surface.npz",
        points=np.array([[mesh.vertices[i].co[:] for i in t.vertices] for t in tri]),
        uv=np.array([[mesh.uv_layers[0].data[i].uv[:] for i in t.loops] for t in tri]),
        normals=np.array([[mesh.corner_normals[i].vector[:] for i in t.loops] for t in tri]),
        tangents=np.array([[mesh.loops[i].tangent[:] for i in t.loops] for t in tri]),
        signs=np.array([[mesh.loops[i].bitangent_sign for i in t.loops] for t in tri]))
    tree=ast.parse((src/"RebuildV2/author.py").read_text(encoding="utf-8-sig"))
    namespace=dict(KIND=kind, Vector=Vector)
    parts=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {"cubic","contour"}]
    exec(compile(ast.Module(body=parts,type_ignores=[]),"<published R2 contour>","exec"),namespace)
    pts,start,end=namespace["contour"]()
    latest=src/"ContinuousBladesR5_20261104"/kind
    data=(latest/"surface_source.json").read_bytes().replace(b"_R5",b"_R2")
    if hashlib.sha256(data).hexdigest()!=old(kind,"surface_source.json")["sha256"]: raise ValueError(kind)
    (directory/"surface_source.json").write_bytes(data)
    prefix=body_name.replace("SM_","T_",1)
    shutil.copyfile(replay/"Textures"/(prefix+"_BaseColor.png"),directory/"Before/Textures"/(prefix+"_BaseColor.png"))
    config=json.loads((latest/"transfer_config.json").read_bytes())
    config.update(texture_prefix=prefix,edge_points_xz_m=pts[start:end+1])
    target=old(kind,"transfer_config.json")["sha256"]
    exact=False
    for limits in [None,[.52,.6],[.42,.58],[.5,.6],[.42,.60],[.45,.55]]:
        attempt=dict(config)
        if limits is None: attempt.pop("edge_mask_thresholds",None)
        else: attempt["edge_mask_thresholds"]=limits
        for indent in (2,1):
            for line in ("\r\n","\n"):
                buf=(json.dumps(attempt,indent=indent)+"\n").replace("\n",line).encode()
                if hashlib.sha256(buf).hexdigest()==target:
                    (directory/"transfer_config.json").write_bytes(buf)
                    exact=True
                    break
            if exact: break
        if exact: break
    if not exact:
        (directory/"transfer_config.json").write_text(json.dumps(config,indent=2))
    print("R2 surface",kind,"exact transfer config",exact, "surface data equals archive",hashlib.sha256((directory/"target_surface.npz").read_bytes()).hexdigest()==old(kind,"target_surface.npz")["sha256"],flush=True)
