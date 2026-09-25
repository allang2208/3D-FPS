"""Save a bounded batch using the original UE skeleton and inverse bind matrices."""
import json,hashlib
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/NativeSkin')
DEST='/Game/Characters/ModularOutfit20260924/NativeSkin'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play mode before saving hand meshes')
statepath=ROOT/'saved.json';state=json.loads(statepath.read_text()) if statepath.exists() else {}
skin=u.load_asset('/Game/Characters/Mannequins/PlayerBodySkin/MI_PlayerBodySkin')
if not skin:raise RuntimeError('Missing skin material')
count=0
profiles=list(json.loads((ROOT.parent/'inputs.json').read_text()))
priority=['RuneSword','SVD','PKM','M4']
for key in priority+[p for p in profiles if p not in priority]:
    path=ROOT/(key+'_skin.json')
    authored=path.read_bytes();digest=hashlib.sha256(authored).hexdigest()
    d=json.loads(authored);key=d['profile']
    if state.get(key,{}).get('author_sha256')==digest:continue
    source=u.load_asset(d['source'])
    src,result=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy native skeleton '+key)
    _,bones=B.get_all_bones_info(src);indices={str(b.name):b.index for b in bones}
    dm=u.DynamicMesh()
    buffers=u.GeometryScriptSimpleMeshBuffers(
        vertices=[u.Vector(*v) for v in d['vertices']],normals=[u.Vector(*v) for v in d['normals']],
        uv0=[u.Vector2D(*v) for v in d['uv']],triangles=[u.IntVector(*v) for v in d['triangles']])
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buffers,0,True)
    B.copy_bones_from_mesh(src,dm)
    B.mesh_create_bone_weights(dm)
    for i,w in enumerate(d['weights']):
        weights=[u.GeometryScriptBoneWeight(bone_index=indices[n],weight=v) for n,v in w.items()]
        B.set_vertex_bone_weights(dm,i,weights)
    for i,m in enumerate(d['materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,m,True)
    name='SK_'+key+'_NativeBareSkin';asset=u.load_asset(DEST+'/'+name)
    if not asset:asset=A.duplicate_asset(name,DEST,source)
    if not asset:raise RuntimeError('Cannot create native mesh '+key)
    sleeves=next((s.material_interface for s in source.materials if str(s.material_slot_name)=='MI_Manny_01'),skin)
    options=u.GeometryScriptCopyMeshToAssetOptions(
        replace_materials=True,new_materials=[sleeves,skin,skin,skin,skin],
        new_material_slot_names=['DefaultSleeves','SkinArms','SkinHands','SkinTorso','SkinRest'],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,result=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native geometry save failed '+key)
    asset.set_editor_property('physics_asset',None)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):raise RuntimeError('LOD authoring failed '+key)
    if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(asset,3,True,False):
        raise RuntimeError('LOD creation failed '+key)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+key)
    state[key]={'mesh':asset.get_path_name(),'source':source.get_path_name(),'skeleton':source.skeleton.get_path_name(),'author_sha256':digest,
        'vertices':len(d['vertices']),'triangles':len(d['triangles']),
        'shirt_covers':[0,1,3],'glove_covers':[2]}
    statepath.write_text(json.dumps(state,indent=2))
    print('NATIVE_BARE_SKIN_SAVED',key,asset.get_path_name())
    count+=1
    if count>=4:break
