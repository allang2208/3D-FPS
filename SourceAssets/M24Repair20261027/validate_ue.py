"""Focused readback of repaired dimensions, shading settings and attachment registration."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).resolve().parent;R='/Game/Weapons/M24/Repair20261027'
data={'assets':{},'normal_textures':{},'checks':{}}
sk=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
manifest=json.loads((O/'authoring.json').read_text())
mesh=u.load_asset(R+'/SK_M24_RepairedV9')
ref=u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
registration=json.loads((O.parent/'M24Modular20261027/authoring.json').read_text())['registration_ue_cm']
errors={}
for bone,position in registration.items():
    p=u.AnimPoseExtensions.get_bone_pose(ref,bone,u.AnimPoseSpaces.WORLD).translation
    errors[bone]=math.dist([p.x,p.y,p.z],position)
assert max(errors.values())<.02,errors
data['checks']['static_to_skeletal_marker_error_cm']=errors
assets=[mesh]+[u.load_asset(R+'/SM_M24_'+k) for k in manifest['models']]
for ob in assets:
    skeletal=isinstance(ob,u.SkeletalMesh)
    settings=(sk if skeletal else sm).get_lod_build_settings(ob,0)
    assert not settings.recompute_normals and not settings.recompute_tangents
    assert settings.use_full_precision_u_vs and settings.use_high_precision_tangent_basis
    bounds=ob.get_bounds();extent=bounds.box_extent
    assert max(extent.x,extent.y,extent.z)<150,(ob.get_name(),str(bounds))
    slots=ob.materials if skeletal else ob.static_materials
    data['assets'][ob.get_path_name()]={'bounds':str(bounds),'build_settings':str(settings),
        'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in slots]}
for path in u.EditorAssetLibrary.list_assets('/Game/Weapons/M24/CustomScope20261026/Textures'):
    tex=u.load_asset(path)
    if tex.get_editor_property('compression_settings')!=u.TextureCompressionSettings.TC_NORMALMAP:continue
    assert not tex.get_editor_property('srgb')
    assert tex.get_editor_property('flip_green_channel')
    data['normal_textures'][tex.get_path_name()]={'sRGB':False,'compression':'TC_NORMALMAP','flip_green_channel':True}
data['complete']=True
(O/'validation_receipt.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('M24_REPAIR_READBACK',data['checks'],flush=True)
