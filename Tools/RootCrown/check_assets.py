"""Read saved UE mesh, motion and F6 Blueprint defaults without changing maps or PIE."""
import unreal as u
import json, math, traceback
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';V=DEST+'/RigV01'
report={'passed':False,'pie_run':False,'assets_saved':False}
def write():(ROOT/'Reports/ue-checks.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def xyz(v):return [v.x,v.y,v.z]
try:
    mesh=u.load_asset(V+'/SK_RootCrown');clip=u.load_asset(V+'/Animations/A_RootCrown_CrownRigDemo')
    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview')
    if not mesh or not clip or not bp:raise RuntimeError('Missing persisted rig asset')
    opts=u.AnimPoseEvaluationOptions();opts.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
    opts.set_editor_property('optional_skeletal_mesh',mesh)
    poses=[u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts) for t in (0.,3.,6.,9.,12.)]
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(poses[0])]
    def location(p,name):return xyz(u.AnimPoseExtensions.get_bone_pose(p,name,u.AnimPoseSpaces.WORLD).translation)
    displacements={}
    for name in ('RootCrownRig','Root','Bone_002','Bone_005','Bone_009','Crown_05_Rim','Crown_08_Rim'):
        first=location(poses[0],name)
        displacements[name]=max(math.dist(first,location(p,name)) for p in poses)
    report['animated_bone_displacement_cm']=displacements
    assert all(displacements[n]<.01 for n in ('RootCrownRig','Root','Bone_002','Bone_005','Bone_009'))
    assert max(displacements[n] for n in ('Crown_05_Rim','Crown_08_Rim'))>1.
    data=u.AssetRegistryHelpers.create_asset_data(mesh)
    report['mesh_tags']={n:str(u.AssetRegistryHelpers.get_tag_value(data,n)) for n in ('Triangles','Vertices','Bones','MaxBoneInfluences')}
    dynamic=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.set_editor_property('lod_type',u.GeometryScriptLODType.RENDER_DATA)
    _,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dynamic,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read the saved skeletal render geometry')
    report['lod0_triangles']=dynamic.get_triangle_count();assert report['lod0_triangles']==197061
    report['bones']=len(names);assert len(names)==50
    physics=u.AssetRegistryHelpers.create_asset_data(mesh.physics_asset)
    report['physics_bodies']=int(u.AssetRegistryHelpers.get_tag_value(physics,'Bodies'))
    report['physics_constraints']=int(u.AssetRegistryHelpers.get_tag_value(physics,'Constraints'))
    assert report['physics_bodies']>0
    # Do not switch or dirty an existing editor's map. Read the saved F6 class
    # and its real asset/navigation defaults; in-game spawning remains a user check.
    defaults=u.get_default_object(bp.generated_class())
    assert defaults.get_editor_property('visual_mesh')==mesh
    assert defaults.get_editor_property('preview_animation')==clip
    nav=defaults.get_editor_property('character_movement').get_editor_property('nav_agent_props')
    report['preview']={'class':defaults.get_class().get_path_name(),
        'nav_radius':nav.get_editor_property('agent_radius'),'nav_height':nav.get_editor_property('agent_height'),
        'animation':clip.get_path_name(),'mesh':mesh.get_path_name()}
    assert report['preview']['nav_radius']==225. and report['preview']['nav_height']==450.
    # Read UE render data directly. Its optional FBX re-export needs a render
    # MeshObject and asserts in NullRHI; author FBX/GLB were round-tripped separately.
    report['geometry_check']='Saved UE render data plus separate author FBX/GLB round-trip'
    report['passed']=True;write();print('ROOT_CROWN_UE_CHECKED '+json.dumps(report),flush=True)
except Exception:report['error']=traceback.format_exc();write();raise
