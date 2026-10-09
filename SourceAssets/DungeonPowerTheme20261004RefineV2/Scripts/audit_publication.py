"""Read saved package references and ownership before an authorized publication."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pipeline_common as c
import unreal as u
c.execution_guard(u)
plan=c.read(c.ROOT/'Config/local-publication-plan.json')
saved=c.read(c.ROOT/'Receipts/subject-map.json')
assert saved['stage']=='map_saved' and saved['map']==plan['staging_map']
old_root='/Game/Dungeons/PowerTheme20261004/'
reg=u.AssetRegistryHelpers.get_asset_registry();reg.search_all_assets(True);reg.wait_for_completion()
opt=u.AssetRegistryDependencyOptions()
for field in ('include_soft_package_references','include_hard_package_references','include_searchable_names','include_soft_management_references','include_hard_management_references'):
    opt.set_editor_property(field,True)
def deps(path):return [str(x) for x in (reg.get_dependencies(path,opt) or [])]
todo=[plan['staging_map']];seen=set()
while todo:
    path=todo.pop()
    if path in seen:continue
    seen.add(path)
    if path.startswith('/Game/'):todo.extend(p for p in deps(path) if p not in seen)
oldset={f['package'] for f in plan['old_assets']}
records=[];keep=set(oldset&seen)
for item in plan['old_assets']:
    path=item['package'];file=Path(item['path'])
    assert file.is_file() and c.file_digest(file)==item['sha256'], 'Old asset changed: '+path
    assert path.startswith(old_root) and not path.startswith(c.OWNED_BASE+'/')
    obj=u.load_asset(path)
    if not obj or u.EditorAssetLibrary.get_metadata_tag(obj,'DungeonPowerTheme20261004.Owner')!='DungeonPowerTheme20261004':
        raise RuntimeError('Unowned old asset must be preserved: '+path)
    referencers=[str(x) for x in (reg.get_referencers(path,opt) or [])]
    outside=[p for p in referencers if p not in oldset and p!=plan['canonical_map']]
    if outside:keep.add(path)
    records.append(dict(**item,referencers=referencers,outside_referencers=outside))
# Retain dependencies of every old asset that is still needed.
todo=list(keep)
while todo:
    for p in deps(todo.pop()):
        if p in oldset and p not in keep:keep.add(p);todo.append(p)
retire=[r for r in records if r['package'] not in keep]
mapfile=Path(plan['old_map']['path'])
assert mapfile.is_file() and c.file_digest(mapfile)==plan['old_map']['sha256'],'Old map changed before publication'
stage=Path(plan['staging_map_file']);assert stage.is_file()
report=dict(stage='reference_audit_saved',revision=saved['revision'],canonical_map=plan['canonical_map'],staging_map=plan['staging_map'],staging_map_sha256=c.file_digest(stage),old_map=plan['old_map'],retire_assets=retire,retained_assets=[r for r in records if r['package'] in keep],new_map_reachable_packages=sorted(seen),tests_run=False,rendered=False,game_run=False)
c.write(c.ROOT/'Receipts/publication-reference-audit.json',report)
u.log('POWER_THEME_PUBLICATION_REFERENCES_SAVED retire=%d retain=%d'%(len(retire),len(keep)))
