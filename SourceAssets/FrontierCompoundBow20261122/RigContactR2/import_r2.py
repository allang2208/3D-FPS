"""Save only the revised wheel assembly, skeleton and arrow rest in the isolated host."""
from pathlib import Path
import unreal as u, os, json
s=Path(__file__).resolve().parent
b=Path(os.environ['FRONTIER_BATCH'])
root='/Game/Weapons/FrontierCompoundBow'
dest=root+'/RigContactR2'
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
out={}
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):
        raise RuntimeError('Unable to save '+str(obj))
    out[obj.get_name()]=obj.get_path_name()
for name in ('SK_Frontier_Assembly','SM_Frontier_Rest'):
    sk=name.startswith('SK')
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if sk else u.FBXImportType.FBXIT_STATIC_MESH
    o.import_as_skeletal=sk;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
    data=o.skeletal_mesh_import_data if sk else o.static_mesh_import_data
    if not sk:data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(s/'Export'/(name+'.fbx'));task.destination_path=dest
    task.destination_name=name;task.automated=True;task.replace_existing=True;task.options=o
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(dest+'/'+name)
    slots=list(mesh.materials if sk else mesh.static_materials)
    for slot in slots:
        matname='M_Frontier_Cord' if 'Cord' in str(slot.material_slot_name) else 'M_Frontier_Surface'
        slot.material_interface=u.load_asset(root+'/'+matname)
        if not slot.material_interface:raise RuntimeError(matname)
    if sk:
        mesh.materials=slots;save(mesh.skeleton)
        pose=mesh.skeleton.get_reference_pose();bones={}
        for n in u.AnimPoseExtensions.get_bone_names(pose):
            t=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
            bones[str(n)]=[[t.translation.x,t.translation.y,t.translation.z],[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]]
        expected={side+k for side in ('upper','lower') for k in ('_01','_02','_cam','_tip','_rim_center','_rim_u','_rim_v','_cable0','_cable1')}
        if expected-bones.keys():raise RuntimeError(str(expected-bones.keys()))
        (b/'ue-reference.json').write_text(json.dumps(bones,indent=2),encoding='utf8')
    else:mesh.static_materials=slots
    save(mesh)
(b/'import.json').write_text(json.dumps(out,indent=2),encoding='utf8')
