import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R={}
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for k,path in [('weapon','/Game/Weapons/M870/Tactical20261015/SK_M870_V7'),('arms','/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7')]:
 mesh=u.load_asset(path)
 dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Bind read failed '+path)
 _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
 R[k]={'path':path,'rest':{str(b.name):tr(b.world_transform) for b in bones}}
(O/'runtime_bindings.json').write_text(json.dumps(R,separators=(',',':')))
print('M870_AND_NATIVE_BINDINGS_READ',flush=True)
