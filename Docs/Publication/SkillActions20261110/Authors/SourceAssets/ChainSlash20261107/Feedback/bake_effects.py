"""Build four optical blade ribbons and the impact wave used by ChainSlash."""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Skills/ChainSlash20261107/Feedback'
MATERIAL = '/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift'
material = u.load_asset(MATERIAL)
clip = u.load_asset('/Game/Skills/ChainSlash20261107/Animations/A_ChainSlash_Standard')
if not material or not clip:
    raise RuntimeError('ChainSlash animation and optical material are required')
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.COMPRESSED
markers = {str(m.marker_name):float(m.time) for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
assets = u.EditorAssetLibrary
saved = []

def save_strip(name, rows):
    count, lanes = len(rows)-1, len(rows[0])-1
    verts = [v for row in rows for v in row]
    uv = [u.Vector2D(i/count, j/lanes) for i in range(count+1) for j in range(lanes+1)]
    tris = []
    for i in range(count):
        for j in range(lanes):
            a=i*(lanes+1)+j
            b=a+lanes+1
            tris.extend([u.IntVector(a,b,a+1),u.IntVector(a+1,b,b+1)])
    mesh=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,u.GeometryScriptSimpleMeshBuffers(vertices=verts,uv0=uv,triangles=tris),0,True)
    path = DEST + '/' + name
    asset = u.load_asset(path) if assets.does_asset_exist(path) else None
    if asset:
        if assets.get_metadata_tag(asset,'ChainSlashFeedback')!='1' or any(pkg.get_name()==path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Preserving unowned or unsaved package '+path)
        _,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD(lod_index=0))
    else:
        asset,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True,enable_collision=False))
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not build '+path)
    asset.set_editor_property('static_materials',[u.StaticMaterial(material_interface=material,material_slot_name='Refraction')])
    assets.set_metadata_tag(asset,'ChainSlashFeedback','1')
    if not assets.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+path)
    saved.append(asset.get_path_name())

for cut in range(1,5):
    mark = markers[f'Cut{cut}']
    rows = []
    for i in range(37):
        phase = i/36
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,mark-.125+.23*phase,options)
        root = u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
        root.scale3d=u.Vector(1,1,1)
        rows.append([root.transform_location(u.Vector(0,0,26.+60.*j/4)) for j in range(5)])
    save_strip(f'SM_ChainSlash_Cut{cut}',rows)

# A shallow wavefront faces out of the touched surface; unit outer radius 25 cm.
rows=[]
for i in range(65):
    a=2*math.pi*i/64
    rows.append([u.Vector(2.4*math.sin(math.pi*j/4),(16.+9*j/4)*math.cos(a),(16.+9*j/4)*math.sin(a)) for j in range(5)])
save_strip('SM_ChainSlash_ImpactWave',rows)
(ROOT/'saved-effects.json').write_text(json.dumps(saved,indent=2))
u.log('CHAIN_SLASH_FEEDBACK_SAVED '+str(saved))
