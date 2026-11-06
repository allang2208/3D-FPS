"""Bake both optical ribbons straight from the saved sweep clips, in viewmodel cm."""
from pathlib import Path
import json
import math
import unreal as u

HERE = Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve() != HERE.parents[2]:
    raise RuntimeError("Wrong FPSGAME project")
DEST = "/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104"
MATERIAL = "/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift"
TAG = "HighlandSweepRift"
CONTACT, RELEASE = .30, .47
ROWS, LANES = 48, 4
INNER, TIP = 22., 88.  # actual broadblade cap, in the unscaled WPN_root frame
assets = u.EditorAssetLibrary
material = u.load_asset(MATERIAL)
if not material:
    raise RuntimeError("Missing normal slash refraction material")
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.COMPRESSED
query = u.GeometryScript_MeshQueries

def station(clip, phase):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, CONTACT + (RELEASE-CONTACT)*phase, options)
    root = u.AnimPoseExtensions.get_bone_pose(pose, 'WPN_root', u.AnimPoseSpaces.WORLD)
    root.scale3d = u.Vector(1,1,1)
    return [root.transform_location(u.Vector(0,0,INNER+(TIP-INNER)*j/LANES)) for j in range(LANES+1)]

def distance(a,b):
    return math.sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2)

def xyz(v):
    return [v.x,v.y,v.z]

report = {}
for grip in ('Standard','LongGrip'):
    clip_path = DEST + '/A_Highland_BreakSweep_' + grip
    heavy, ready = [u.load_asset(clip_path+suffix) for suffix in ('','_FromReady')]
    if not heavy or not ready:
        raise RuntimeError('Missing sweep clips for '+grip)
    rows = [station(ready,i/ROWS) for i in range(ROWS+1)]
    vertices = [point for row in rows for point in row]
    uv = [u.Vector2D(i/ROWS,j/LANES) for i in range(ROWS+1) for j in range(LANES+1)]
    triangles=[]
    for i in range(ROWS):
        for j in range(LANES):
            a=i*(LANES+1)+j; b=a+LANES+1
            triangles.extend((u.IntVector(a,b,a+1),u.IntVector(a+1,b,b+1)))
    mesh=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,uv0=uv,triangles=triangles),0,True)
    path=DEST+'/SM_Highland_SweepRift_'+grip
    asset=u.load_asset(path) if assets.does_asset_exist(path) else None
    if asset:
        if assets.get_metadata_tag(asset,TAG)!='1' or any(pkg.get_name()==path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Preserving existing or unsaved asset '+path)
        _,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD(lod_index=0))
    else:
        asset,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True,enable_collision=False))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not create ribbon '+path)
    asset.set_editor_property('static_materials',[u.StaticMaterial(material_interface=material,material_slot_name='Refraction')])
    assets.set_metadata_tag(asset,TAG,'1')
    if not assets.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+path)
    # Check the actual asset against both entry poses, including between mesh rows.
    saved,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not read saved ribbon '+path)
    positions = {}
    for i in range(len(triangles)):
        valid,a,b,c=query.get_triangle_positions(saved,i)
        sa,sb,sc,valid_uv=query.get_triangle_u_vs(saved,0,i)
        if not(valid and valid_uv): raise RuntimeError('Missing triangle or UV')
        for point,tex in zip((a,b,c),(sa,sb,sc)):
            key=(round(tex.x*ROWS),round(tex.y*LANES))
            positions[key]=point
    if len(positions)!=len(vertices): raise RuntimeError('Invalid saved ribbon topology')
    errors={}
    for label,clip in [('heavy',heavy),('ready',ready)]:
        worst=0.
        for k in range(ROWS*4+1):
            left=min(k//4,ROWS-1);frac=k/4-left
            expected=station(clip,k/(ROWS*4))
            for j in range(LANES+1):
                actual=positions[left,j]*(1-frac)+positions[left+1,j]*frac
                worst=max(worst,distance(actual,expected[j]))
        if worst>1.:raise RuntimeError(f'{grip} {label} blade deviation {worst} cm')
        errors[label]=round(worst,4)
    report[grip]=dict(asset=asset.get_path_name(),material=asset.get_material(0).get_path_name(),triangles=len(triangles),max_error_cm=errors,rows=[[xyz(positions[i,j]) for j in (0,LANES)] for i in range(ROWS+1)])
(HERE/'saved-ribbons.json').write_text(json.dumps(report,indent=2))
u.log('HIGHLAND_SWEEP_RIFT_SAVED '+str({k:v['max_error_cm'] for k,v in report.items()}))
