"""Restore existing PBR materials to the Nanite/ISM paths; keep all material graphs and textures."""
import json,re,shutil,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Asset save needs editor mode')
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage
catalog=json.loads((PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').read_text())
paths=set()
for module in catalog['modules']:
    for owner in [module]+module.get('side_sockets',[]):
        for part in owner.get('parts',[]):
            paths.add(part['mesh'].split('.')[0]);paths.update(part.get('surface_mesh_variants',[]))
registry=u.AssetRegistryHelpers.get_asset_registry()
options=u.AssetRegistryDependencyOptions(include_soft_package_references=False,include_hard_package_references=True)
materials=set()
for path in paths:
    for dependency in registry.get_dependencies(path,options) or []:
        dep=str(dependency)
        if '/Materials/' in dep and dep.startswith('/Game/Dungeons/'):materials.add(dep)
# Include the reported fixed-start bindings, which are not generated catalog nodes.
log=(PROJECT/'Saved/Logs/FPSGAME.log').read_text(encoding='utf-8',errors='replace')
materials.update(m.split('.')[0] for m in re.findall(r'Material (/Game/Dungeons/\S+) missing usage flag',log))
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def backup(asset):
    path=asset.get_path_name().split('.')[0]
    if path in dirty:raise RuntimeError('Preserve unsaved target '+path)
    relative=Path(path.removeprefix('/Game/')+'.uasset')
    src=PROJECT/'Content'/relative;dest=ROOT/'Sources/Before/Content'/relative
    if src.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
report=dict(stage='saving',materials={},runtime_tested=False)
receipt=ROOT/'Receipts/materials.json'
for path in sorted(materials):
    mat=u.load_asset(path)
    if not isinstance(mat,u.MaterialInterface):raise RuntimeError('Missing material '+path)
    report['materials'][path]=ensure_material_usage(mat,backup)
    receipt.write_text(json.dumps(report,indent=2))
report['stage']='materials_saved'
receipt.write_text(json.dumps(report,indent=2))
print('DUNGEON_RENDER_USAGES_SAVED',len(materials),sum(r['changed'] for r in report['materials'].values()),flush=True)
