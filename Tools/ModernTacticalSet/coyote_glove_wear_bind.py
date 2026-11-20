"""Capture original UE bone indices and reference frames for the selected TS01 gloves."""
import gc
from pathlib import Path
import sys
import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
from coyote_glove_wear import WEAR, plan, write


def xyz(v):
    return [v.x,v.y,v.z]


def bones(mesh):
    _,info=u.GeometryScript_BoneWeights.get_all_bones_info(mesh)
    axes=[u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]
    return [dict(name=str(b.name),index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
                 axes=[xyz(b.world_transform.transform_location(axis)-b.world_transform.translation) for axis in axes]) for b in info]


def extract(asset,render_lod=None):
    lod=(u.GeometryScriptMeshReadLOD() if render_lod is None else
         u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=render_lod))
    mesh,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
            asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError(f"Could not read {asset.get_path_name()} at LOD {render_lod}")
    return mesh


def main():
    data={}
    for rig,row in plan()["rigs"].items():
        asset=u.load_asset(row["previous"])
        dm=extract(asset)
        data[rig]=dict(source=asset.get_path_name(),skeleton=asset.skeleton.get_path_name(),bones=bones(dm))
        del dm,asset
        gc.collect()
        u.SystemLibrary.collect_garbage()
    write(WEAR/"native-bindings.json",data)
    print("GLOVE_WEAR_NATIVE_BINDINGS",len(data),flush=True)


if __name__=="__main__":
    main()
