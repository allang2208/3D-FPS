"""Save fitted Boots assets and compatible Jason skin/cuff variants."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BootsEquipment20261004'
DEST='/Game/Characters/ModularOutfit20260924/BootsEquipment20261004'
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End play before saving Boots assets')
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;T=u.GeometryScript_MeshTransforms
def read(key):return json.loads((R/(key+'.json')).read_text())
def copy(asset):
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+asset.get_path_name())
    return dm
target=u.load_asset('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body');target_dm=copy(target)
saved={}
for key,name in [('base','Base'),('boots','Boots'),('jeans','Jeans_BootsFit'),('cargo','Cargo_BootsFit')]:
    data=read(key+'_fitted');dm=copy(u.load_asset(data['source']))
    materials=data['materials'] if key=='base' else [data['materials'][0]]
    for ti in range(dm.get_triangle_count()):
        u.GeometryScript_Materials.set_triangle_material_id(dm,ti,data['triangle_materials'][ti] if key=='base' else 0,True)
    if key!='base':
        u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*v) for v in data['positions']]))
    if key=='boots':
        B.copy_bones_from_mesh(target_dm,dm,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
        for vi,weights in enumerate(data['weights']):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=b,weight=w) for b,w in weights])
    path=DEST+'/SK_Jason_'+name
    opts=u.GeometryScriptCreateNewSkeletalMeshAssetOptions(use_mesh_bone_proportions=True,enable_recompute_normals=key!='base',enable_recompute_tangents=True)
    opts.materials={m['slot']:u.load_asset(m['asset']) for m in materials}
    asset=u.load_asset(path)
    if asset:
        write=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[u.load_asset(m['asset']) for m in materials],new_material_slot_names=[m['slot'] for m in materials],enable_recompute_normals=key!='base',enable_recompute_tangents=True)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,write,u.GeometryScriptMeshWriteLOD())
    else:asset,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,target.skeleton,path,opts)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author '+path)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    if not u.SkeletalMeshEditorSubsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('Cannot build LODs: '+path)
    asset.set_editor_property('physics_asset',target.physics_asset)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+path)
    saved[key]=asset.get_path_name()
    print('BOOTS_SKELETAL_SAVED',key,flush=True)

boots=u.load_asset(saved['boots'])
for kind in ['pickup','icon']:
    dm=copy(boots)
    if kind=='icon':
        remove=[]
        for ti in range(dm.get_triangle_count()):
            valid,a,b,c=u.GeometryScript_MeshQueries.get_triangle_positions(dm,ti)
            if valid and a.x+b.x+c.x<0:remove.append(ti)
        u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),False)
        T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=150,roll=0))
        T.rotate_mesh(dm,u.Rotator(pitch=30,yaw=0,roll=0))
    else:
        points=read('boots_fitted')['positions']
        center=[(min(p[i] for p in points)+max(p[i] for p in points))*.5 for i in range(3)]
        T.translate_mesh(dm,u.Vector(*[-v for v in center]))
    path=DEST+('/Icons/SM_Boots_Display' if kind=='icon' else '/Pickups/SM_Boots')
    asset=u.load_asset(path)
    if asset:_,status=G.copy_mesh_to_static_mesh(dm,asset,u.GeometryScriptCopyMeshToAssetOptions(),u.GeometryScriptMeshWriteLOD())
    else:asset,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author '+path)
    asset.set_material(0,boots.materials[0].material_interface)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+path)
    saved[kind]=asset.get_path_name()
    print('BOOTS_STATIC_SAVED',kind,flush=True)
(R/'saved_assets.json').write_text(json.dumps(saved,indent=2))
print('BOOTS_ASSETS_SAVED',flush=True)
