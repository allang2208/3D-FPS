"""Publish the already saved new world to the original entry after recoverable archival."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pipeline_common as c
import container_bridge as containers
import unreal as u
c.execution_guard(u)
plan=c.read(c.ROOT/'Config/local-publication-plan.json')
audit=c.read(c.ROOT/'Receipts/publication-reference-audit.json')
imported=c.read(c.ROOT/'Receipts/import.json')
old_receipt=c.read(c.ROOT/'Receipts/subject-map.json')
scene,manifest,roles=c.load_inputs()
assert audit['stage']=='reference_audit_saved' and old_receipt['stage']=='map_saved'
assert c.file_digest(plan['staging_map_file'])==audit['staging_map_sha256']
assert not Path(plan['old_map']['path']).exists(),'Old map has not been archived; refusing overwrite'
archive=c.read(c.ROOT/'Receipts/publication-archive.json')
old_backup=Path(archive['old_map_archive'])
assert old_backup.is_file() and c.file_digest(old_backup)==plan['old_map']['sha256']
world=u.EditorLoadingAndSavingUtils.load_map(plan['staging_map'])
if not world:raise RuntimeError('Saved RefineV2 map could not be loaded')
E=u.EditorAssetLibrary
assert E.get_metadata_tag(world,c.OWNER+'.Owner')==c.OWNER
assert E.get_metadata_tag(world,c.OWNER+'.Fingerprint')==old_receipt['fingerprint']
final_scene=dict(scene,sample_map=plan['canonical_map'])
native,outline=containers.specifications(final_scene)
fingerprint=c.digest(dict(scene=final_scene,manifest=manifest,material_roles=roles,containers=[s for _,_,s in native],outline=outline,meshes=imported['meshes'],map_pipeline=2))
for key,val in [('Owner',c.OWNER),('Revision',scene['revision']),('Fingerprint',fingerprint)]:E.set_metadata_tag(world,c.OWNER+'.'+key,val)
if not u.EditorLoadingAndSavingUtils.save_map(world,plan['canonical_map']):raise RuntimeError('Canonical map save failed')
mapfile=Path(plan['old_map']['path']);assert mapfile.is_file()
# Future rebuilds target the published entry and retain the same ownership guards.
c.write(c.ROOT/'Config/scene.json',final_scene)
canonical=plan['canonical_map'];staging=plan['staging_map']
for root in (c.ROOT/'Scripts',c.ROOT/'Docs',c.ROOT/'Config'):
    for file in root.rglob('*'):
        if file.suffix not in ('.py','.md','.json','.svg','.txt'):continue
        if file.name in ('local-publication-plan.json','audit_publication.py','publish_current_map.py'):continue
        text=file.read_text('utf-8-sig')
        if staging in text:file.write_text(text.replace(staging,canonical),encoding='utf8')
c.write(c.ROOT/'Receipts/subject-map-staging.json',old_receipt)
receipt=dict(old_receipt,map=canonical,fingerprint=fingerprint,console_command='open '+canonical,published_from=staging,publication='Original entry replaced after reference audit and recoverable archival',map_sha256=c.file_digest(mapfile))
c.write(c.ROOT/'Receipts/subject-map.json',receipt)
c.write(c.ROOT/'Receipts/publication.json',dict(stage='canonical_map_saved',revision=scene['revision'],canonical_map=canonical,map_sha256=c.file_digest(mapfile),map_bytes=mapfile.stat().st_size,original_recovery_archive=str(old_backup),tests_run=False,rendered=False,game_run=False))
u.log('POWER_THEME_CANONICAL_MAP_SAVED '+canonical)
