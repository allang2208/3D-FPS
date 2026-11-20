"""Save the four native world/owner bases. Tailored fits derive from these assets."""
import gc
import hashlib
import json
from pathlib import Path
import sys
import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
import field_pants_wear_save as native
from coyote_glove_wear_bind import bones,extract
from coyote_glove_wear_save import io,remap_weights

P=Path(__file__).resolve().parents[2]
ROOT=P/'SourceAssets/ModernTacticalSet20261113/PatrolShirtR2'
PREFIX='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/PatrolShirtR2/Wear/'
E=native.E
S=native.S
native.PREFIX=PREFIX
native.POLICY=PREFIX+'DA_TS01_PatrolShirt_LOD'
native.REV='PatrolShirtR2'

def read(path):return json.loads(path.read_bytes())
def package_path(ref):
    return P/'Content'/(ref.removeprefix('/Game/').split('.')[0]+'.uasset')
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def record(path,data):
    tmp=path.with_suffix('.writing')
    tmp.write_text(json.dumps(data,indent=2),encoding='utf8');tmp.replace(path)

def main():
    policy=native.lod_settings()
    path=ROOT/'World/base-saved.json'
    receipt=read(path) if path.is_file() else {}
    for key,row in read(ROOT/'World/routes.json').items():
        if not row['base']:continue
        source=ROOT/row['source'];fingerprint=sha(source)
        prior=receipt.get(key,{})
        if prior.get('source_sha256')==fingerprint and package_path(row['asset']).exists():continue
        print('PATROL_BASE_BEGIN',key,flush=True)
        donor=u.load_asset(row['previous'])
        if not donor or sha(package_path(row['previous']))!=row['donor_sha256']:raise RuntimeError('Worn carrier source changed')
        mesh=extract(donor);data=read(source)
        remap_weights(data,dict(bones=bones(mesh),skeleton=donor.skeleton.get_path_name()))
        materials=[u.load_asset(ref) for ref in data['materials']]
        if not all(materials):raise RuntimeError('Missing patrol material')
        native.separate_sewn_sheets(data)
        dyn=io.dynamic(data,mesh)
        if dyn.get_triangle_count()!=len(data['triangles']):raise RuntimeError('Failed to transfer authored sheets')
        folder,name=row['asset'].rsplit('/',1)
        asset=u.load_asset(row['asset']) if E.does_asset_exist(row['asset']) else native.A.duplicate_asset(name,folder,donor)
        if not asset:raise RuntimeError('Could not create '+row['asset'])
        asset.set_editor_property('physics_asset',None)
        asset.set_editor_property('lod_settings',None)
        count=S.get_lod_count(asset)
        if count>1 and not S.remove_lods(asset,list(range(count-1,0,-1))):raise RuntimeError('Could not reset LODs')
        build=S.get_lod_build_settings(asset,0)
        build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('recompute_normals',False)
        S.set_lod_build_settings(asset,0,build)
        opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=data['material_slots'],
            enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dyn,asset,opts,u.GeometryScriptMeshWriteLOD(lod_index=0))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not transfer '+row['asset'])
        asset.set_editor_property('lod_settings',policy)
        if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('Could not construct distance meshes')
        provenance=u.new_object(u.AssetImportData,outer=asset);provenance.scripted_add_filename(str(source),0,'Patrol shirt with native carrier and skin')
        asset.set_editor_property('asset_import_data',provenance)
        E.set_metadata_tag(asset,'TS01Revision','PatrolShirtR2')
        E.set_metadata_tag(asset,'PatternSHA256',fingerprint)
        E.set_metadata_tag(asset,'TS01NativeDonor',row['previous'])
        native.persist(asset)
        receipt[key]=dict(asset=asset.get_path_name(),previous=row['previous'],source_sha256=fingerprint,triangles=len(data['triangles']),
                          lod_count=S.get_lod_count(asset),package_sha256=sha(package_path(row['asset'])),material_slots=data['material_slots'])
        record(path,receipt)
        print('PATROL_BASE_SAVED',key,flush=True)
        del asset,donor,mesh,data,dyn
        gc.collect();u.SystemLibrary.collect_garbage()

if __name__=='__main__':main()
