"""Save continuous robe underlayers and material envelopes; retain robe physics."""
import json,hashlib,gc,sys,importlib.util
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/HemContinuity20261019';DEST='/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/HemContinuity20261019'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import save_assets as shared
import hem_materials
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path=R/'saved_assets.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(saved={},underlayers={},runtime_tested=False)
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside stair partition scope')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('Preserve current PIE before saving stair sections')
    receipt['completed']=False;record();E.make_directory(DEST)
    for row in json.loads((R/'authored.json').read_text())['rows']:
        if not row['hidden_source_triangles']:
            receipt['underlayers'][row['original']]=row['source'];record();continue
        file=Path(row['authored']);raw=file.read_bytes();sha=hashlib.sha256(raw+hem_materials.REV.encode()).hexdigest();name='SK_'+row['key']+'_RobeHem';folder=DEST+'/'+row['profile'];path=folder+'/'+name;asset=u.load_asset(path)
        if not asset or E.get_metadata_tag(asset,'RobeHemSourceSHA')!=sha:
            d=json.loads(raw);source=u.load_asset(row['source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Source binding unavailable '+row['key'])
            dm=shared.dynamic(d,native);mats=[u.load_asset(p) if p else None for p in d['materials']]
            for i,name_slot in enumerate(d['material_slots']):
                if name_slot.startswith('RobeStairHidden_'):mats[i]=hem_materials.make(mats[i])
            asset=asset or A.duplicate_asset(name,folder,source)
            options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
            _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not write '+name)
            slots=list(asset.get_editor_property('materials'))
            for i,slot in enumerate(slots):
                slot.set_editor_property('material_slot_name',d['material_slots'][i])
            asset.set_editor_property('materials',slots)
            build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build)
            # The original foot and deformable upper region share the same
            # boundary, binding and UVs in every LOD. No ankle cap is emitted.
            u.FPSModularOutfitComponent.configure_outfit_lods(asset)
            factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
            policy=u.load_asset(path+'_LODPolicy') or A.create_asset(name+'_LODPolicy',folder,u.SkeletalMeshLODSettings,factory);groups=[]
            for ratio,screen in ((1.,1.),(.65,.18),(.35,.075)):
                group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
                for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():settings.set_editor_property(key,value)
                group.set_editor_property('reduction_settings',settings);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
            policy.set_editor_property('lod_groups',groups);save(policy);asset.set_editor_property('lod_settings',policy)
            models=list(asset.get_editor_property('source_models'))
            for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
            asset.set_editor_property('source_models',models)
            if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('Stair LOD generation failed '+name)
            asset.set_editor_property('physics_asset',None);E.set_metadata_tag(asset,'RobeHemSourceSHA',sha);E.set_metadata_tag(asset,'SourceContract',d['contract']);save(asset)
            del d,native,dm,source
        receipt['saved'][row['key']]=dict(asset=asset.get_path_name(),source=row['source'],source_sha256=sha,ankle_boundary_cm=row['cut_cm'],upper_overlap_cm=row['upper_overlap_cm'],lod_count=S.get_lod_count(asset),deformable_triangles=row['hidden_source_triangles'],cap_triangles=0)
        receipt['underlayers'][row['original']]=asset.get_path_name();record();print('ROBE_STAIR_SECTIONS_SAVED',row['key'],flush=True);gc.collect();u.SystemLibrary.collect_garbage()
    receipt['completed']=True;receipt.setdefault('materials',{}).update({k:v.get_path_name() for k,v in hem_materials.cache.items()});receipt['shader_revision']=hem_materials.REV;record();print('ROBE_HEM_LAYERS_COMPLETE',len(receipt['underlayers']),flush=True)
if __name__=='__main__':main()
