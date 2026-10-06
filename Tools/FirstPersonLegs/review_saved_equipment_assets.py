"""Read saved equipment packages in a commandlet; never convert scene components."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/EquipmentReview20261006'
C=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
profile=C['profiles'][body['body_mesh']]
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
paths={body['body_mesh'],profile['native_bare_skin']};hidden={};coverage=[]
for item,recipe in C['items'].items():
    if recipe.get('slot') not in (7,13,15):continue
    path=recipe['rig_meshes'].get('Jason')
    if not path:continue
    paths.add(path);coverage+=recipe.get('rig_world_covers',{}).get('Jason',[])
    for fits in recipe.get('shoe_fit_meshes',{}).values():
        if fits.get('Jason'):paths.add(fits['Jason'])
    owner=recipe.get('owner_body_meshes',{}).get('Jason')
    if owner:
        paths.add(owner);hidden[owner]=recipe['owner_body_hidden_materials']['Jason']
errors=[];rows=[]
base=u.load_asset(profile['native_bare_skin']);base_slots=len(base.materials)
if any(m<0 or m>=base_slots for m in coverage+profile['owner_body_hidden_materials']):errors.append('Coverage references invalid body materials')
# Bone names are read from saved mesh data, not from a posed component.
driver_mesh,status=G.copy_mesh_from_skeletal_mesh(u.load_asset(body['body_mesh']),u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved body')
_,bones=B.get_all_bones_info(driver_mesh);driver_names={str(b.name) for b in bones}
for path in sorted(paths):
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.SkeletalMesh):errors.append('Missing skeletal mesh '+path);continue
    count=S.get_lod_count(mesh);slots=len(mesh.materials)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:errors.append('Missing source '+path);continue
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,vertices,_=Q.get_all_vertex_positions(dm,False);vertices=u.GeometryScript_List.convert_vector_list_to_array(vertices)
    invalid=0;missing_bones=set()
    for index in range(len(vertices)):
        _,weights,valid=B.get_vertex_bone_weights(dm,index)
        if not valid or not weights:invalid+=1;continue
        if abs(sum(w.weight for w in weights)-1.)>.002:invalid+=1
        missing_bones.update(names[w.bone_index] for w in weights if w.weight>0 and names[w.bone_index] not in driver_names)
    if invalid or missing_bones:errors.append(dict(asset=path,invalid_weights=invalid,missing_bones=sorted(missing_bones)))
    visible_lods=[]
    if path in hidden:
        for material in hidden[path]:
            if material>=slots or not str(mesh.materials[material].material_slot_name).startswith('OwnerHiddenArms_'):
                errors.append('Wrong owner hidden material '+path)
        for lod in range(count):
            lod_mesh,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
            if status!=u.GeometryScriptOutcomePins.SUCCESS:errors.append('Unreadable saved LOD '+path);continue
            visible=0;masked=0
            for triangle in range(lod_mesh.get_triangle_count()):
                mat=u.GeometryScript_Materials.get_triangle_material_id(lod_mesh,triangle)[0]
                if mat in hidden[path]:masked+=1
                else:visible+=1
            visible_lods.append(dict(lod=lod,visible_triangles=visible,hidden_triangles=masked))
            if not visible or not masked:errors.append('Empty owner material partition '+path)
    rows.append(dict(asset=path,lods=count,materials=slots,source_vertices=len(vertices),invalid_weights=invalid,owner_lods=visible_lods))
    print('EQUIPMENT_ASSET_REVIEWED '+mesh.get_name(),flush=True)
report=dict(meshes=rows,errors=errors,live_scene_read=False,assets_written=False,runtime_tested=False)
R.mkdir(parents=True,exist_ok=True);(R/'saved-asset-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if errors:raise RuntimeError('Saved equipment review found '+str(len(errors))+' errors')
print('SAVED_EQUIPMENT_REVIEW_PASSED '+str(len(rows)),flush=True)
