"""Background asset authoring: fitted garments, coverage base, and pickups."""
import json, math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/LowerBodyEquipment20261003'
DEST='/Game/Characters/ModularOutfit20260924/LowerBodyEquipment20261003'
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
def read(k):return json.loads((ROOT/(k+'.json')).read_text())
def copy(asset):
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+asset.get_path_name())
    return dm
target=u.load_asset(read('body')['source']);target_dm=copy(target)
saved={}
for key in ['base','jeans','cargo','sneakers']:
    data=read(key+'_fitted');dm=copy(u.load_asset(data['source']))
    materials=data['materials'] if key=='base' else [data['materials'][0]]
    for ti in range(dm.get_triangle_count()):
        u.GeometryScript_Materials.set_triangle_material_id(dm,ti,data['triangle_materials'][ti] if key=='base' else 0,True)
    if key!='base':
        B.copy_bones_from_mesh(target_dm,dm,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
        u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*v) for v in data['positions']]))
        for vi,weights in enumerate(data['weights']):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=b,weight=w) for b,w in weights])
    path=DEST+'/SK_Jason_'+key.title()
    options=u.GeometryScriptCreateNewSkeletalMeshAssetOptions(use_mesh_bone_proportions=True,enable_recompute_normals=key!='base',enable_recompute_tangents=True)
    options.materials={m['slot']:u.load_asset(m['asset']) for m in materials}
    asset=u.load_asset(path)
    if asset:
        write=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[u.load_asset(m['asset']) for m in materials],new_material_slot_names=[m['slot'] for m in materials],enable_recompute_normals=key!='base',enable_recompute_tangents=True)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,write,u.GeometryScriptMeshWriteLOD())
    else:asset,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,target.skeleton,path,options)
    if status!=u.GeometryScriptOutcomePins.SUCCESS or not asset:raise RuntimeError('Cannot author '+path)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    if not u.SkeletalMeshEditorSubsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('Cannot generate outfit LODs')
    asset.set_editor_property('physics_asset',target.physics_asset)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+path)
    saved[key]=asset.get_path_name()
    if key!='base':
        points=data['positions'];lo=[min(v[i] for v in points) for i in range(3)];hi=[max(v[i] for v in points) for i in range(3)];center=[(a+b)/2 for a,b in zip(lo,hi)]
        positions=[]
        for v in points:
            x,y,z=[a-b for a,b in zip(v,center)]
            positions.append(u.Vector(x,z,-y*.38) if key!='sneakers' else u.Vector(x,y,z))
        u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list(positions))
        opts=u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True,enable_collision=False)
        pickup_path=DEST+'/Pickups/SM_'+key.title();pickup=u.load_asset(pickup_path)
        if pickup:
            _,status=G.copy_mesh_to_static_mesh(dm,pickup,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
        else:pickup,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,pickup_path,opts)
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author pickup '+key)
        pickup.set_material(0,u.load_asset(materials[0]['asset']))
        if not u.EditorAssetLibrary.save_loaded_asset(pickup,False):raise RuntimeError('Cannot save pickup '+key)
        saved[key+'_pickup']=pickup.get_path_name()
    (ROOT/'saved_assets.json').write_text(json.dumps(saved,indent=2))
    print('LOWER_BODY_ASSET_SAVED '+key,flush=True)
print('LOWER_BODY_ASSETS_COMPLETE',flush=True)
