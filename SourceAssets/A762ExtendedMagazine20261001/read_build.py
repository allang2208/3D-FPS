import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
s=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
out={}
for path in ['/Game/Weapons/A762/Accessories05/Meshes/SM_A762_ext_mag','/Game/Weapons/A762/ExtendedMagazine20261001/SM_A762_ext_mag_Continuous07']:
 m=u.load_asset(path);b=s.get_lod_build_settings(m,0);out[path]={}
 for k in ['remove_degenerates','recompute_normals','recompute_tangents','use_mikk_t_space','build_scale3d']:
  out[path][k]=str(b.get_editor_property(k))
print('A762_SURFACE_BUILD_SETTINGS',json.dumps(out),flush=True)
