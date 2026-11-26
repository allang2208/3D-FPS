"""Save native-body fitted inner trousers in isolated packages, four per batch."""
import json, hashlib, gc, sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/UnderRobeFit20261020'
DEST='/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/UnderRobeFit20261020'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import hem_materials
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path=R/'saved_assets.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(saved={},underlayers={},runtime_tested=False)

def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')

def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside inner-pants authoring scope')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())

def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('End the current play session before saving inner-pants assets')
    authored=json.loads((R/'authored.json').read_text());receipt['completed']=False;record();E.make_directory(DEST)
    built=0
    for row in authored['rows']:
        raw=Path(row['authored']).read_bytes();sha=hashlib.sha256(raw+hem_materials.REV.encode()).hexdigest()
        name='SK_'+row['key']+'_RobeInnerFit';folder=DEST+'/'+row['profile'];path=folder+'/'+name
        if receipt['saved'].get(row['key'],{}).get('source_sha256')==sha and E.does_asset_exist(path):continue
        if built>=4:break
        source=u.load_asset(row['source']);data=json.loads(raw)
        if not source:raise RuntimeError('Missing original pants '+row['source'])
        dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy native pants '+row['key'])
        if dm.get_vertex_count()!=len(data['positions']):raise RuntimeError('Native vertex IDs changed: recapture '+row['source'])
        # This edits positions in the original mesh. UV overlays, all native
        # bone influences, triangle/material IDs and topology remain intact.
        u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*v) for v in data['positions']]))
        slots=list(source.get_editor_property('materials'))
        materials=[hem_materials.make(slot.material_interface) for slot in slots]
        names=['RobeStairHidden_'+str(i) for i in range(len(slots))]
        asset=u.load_asset(path) or A.duplicate_asset(name,folder,source)
        options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=names,enable_recompute_normals=True,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save fitted geometry '+row['key'])
        slots=list(asset.get_editor_property('materials'))
        for i,slot in enumerate(slots):slot.set_editor_property('material_slot_name',names[i])
        asset.set_editor_property('materials',slots)
        settings=S.get_lod_build_settings(asset,0);settings.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,settings)
        u.FPSModularOutfitComponent.configure_outfit_lods(asset)
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
        policy=u.load_asset(path+'_LODPolicy') or A.create_asset(name+'_LODPolicy',folder,u.SkeletalMeshLODSettings,factory)
        groups=[]
        for ratio,screen in ((1.,1.),(.65,.18),(.35,.075)):
            group=u.SkeletalMeshLODGroupSettings();reduction=group.get_editor_property('reduction_settings')
            for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=True).items():reduction.set_editor_property(key,value)
            group.set_editor_property('reduction_settings',reduction);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
        policy.set_editor_property('lod_groups',groups);save(policy);asset.set_editor_property('lod_settings',policy)
        models=list(asset.get_editor_property('source_models'))
        for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
        asset.set_editor_property('source_models',models)
        if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('Cannot rebuild fitted LODs '+row['key'])
        asset.set_editor_property('physics_asset',None)
        E.set_metadata_tag(asset,'RobeInnerFitSourceSHA',sha)
        E.set_metadata_tag(asset,'SourceContract','Robe-only native-body fitted pants; full legs and original material/UV/binding; fixed cuff with smooth transition; original equipment unchanged')
        save(asset)
        receipt['saved'][row['key']]=dict(asset=asset.get_path_name(),source=row['source'],source_sha256=sha,source_asset_sha256=row['asset_sha256'],lod_count=S.get_lod_count(asset),production=row['production'])
        receipt['underlayers'][row['source']]=asset.get_path_name();built+=1;record()
        print('ROBE_INNER_PANTS_SAVED',row['key'],flush=True)
        del dm,source,asset,data,materials,slots,models,policy;gc.collect();u.SystemLibrary.collect_garbage()
    receipt['completed']=len(receipt['saved'])==len(authored['rows'])
    receipt['revision']=authored['revision'];receipt['shader_revision']=hem_materials.REV;record()
    print('ROBE_INNER_PANTS_BATCH',len(receipt['saved']),len(authored['rows']),receipt['completed'],flush=True)

if __name__=='__main__':main()
