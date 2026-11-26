"""Reuse the exact female robe's repaired geometry, retaining player materials."""
import gc, hashlib, json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/KaitlinBackReview20261117'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
source_data=read(R/'Inputs/female_robe.json')
donor_before=read(P/'SourceAssets/ChapelNun20261115/IdleBackReviewR2/Inputs/robe.json')
geometry_fields=['skeleton','positions','triangles','uv','normals','triangle_materials','weights','bones']
matching={key:source_data[key]==donor_before[key] for key in geometry_fields}
if not all(matching.values()):raise RuntimeError('Donor is not the identical female source')
editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor_world and editor_world.get_game_world():raise RuntimeError('End PIE before asset save')
E=u.EditorAssetLibrary;ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
source=u.load_asset(source_data['source'])
donor=u.load_asset('/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe')
target_path='/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/World/BackRepair20261117/SK_Kaitlin_BlueMageRobe_BackR1'
if source.skeleton!=donor.skeleton:raise RuntimeError('Skeleton mismatch')
if source.physics_asset!=donor.physics_asset:raise RuntimeError('Collision asset mismatch')
if ss.get_lod_count(donor)!=3:raise RuntimeError('Incomplete donor LODs')
if len(source.mesh_clothing_assets)!=1 or len(donor.mesh_clothing_assets)!=1:raise RuntimeError('Cloth asset missing')
if [str(m.material_slot_name) for m in source.materials]!=[str(m.material_slot_name) for m in donor.materials]:raise RuntimeError('Material slot mismatch')
if E.does_asset_exist(target_path):raise RuntimeError('Preserve existing target')
target=E.duplicate_asset(donor.get_path_name().split('.')[0],target_path)
if not target:raise RuntimeError('Duplicate failed')
target.set_editor_property('materials',list(source.materials))
E.set_metadata_tag(target,'KaitlinBackRepair','Removed obsolete outer and inner hood only; native blue robe materials and skirt cloth retained')
E.set_metadata_tag(target,'KaitlinBackSource',source.get_path_name())
target.modify()
if not E.save_loaded_asset(target,False):raise RuntimeError('Save failed')
report=dict(asset=target.get_path_name(),source=source.get_path_name(),geometry_donor=donor.get_path_name(),source_matches_donor_before=matching,
            saved=True,lods=ss.get_lod_count(target),skeleton=target.skeleton.get_path_name(),physics_asset=target.physics_asset.get_path_name(),
            cloth_assets=[c.get_path_name() for c in target.mesh_clothing_assets],
            materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name()) for m in target.materials],
            cloth_preservation_receipt=str(P/'SourceAssets/ChapelNun20261115/IdleBackReviewR2/back_repair_saved.json'))
if report['materials']!=source_data['materials']:raise RuntimeError('Player materials differ')
(R/'saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('KAITLIN_BACK_SAVED',report['asset'],report['lods'],len(report['cloth_assets']),flush=True)
del source_data,donor_before;gc.collect()
