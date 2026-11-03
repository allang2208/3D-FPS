"""Read current saved assets only; never reimport, modify, or save packages."""
from pathlib import Path
import json, hashlib, unreal as u
P=Path(__file__).resolve().parent
R=P.parents[2]
rows=[]
def check(label, ok, **details):
    rows.append(dict(check=label,passed=bool(ok),**details))
    print('THOR_ASSET', 'PASS' if ok else 'FAIL', label, flush=True)
data=json.loads((R/'Content/ColdSteelData/thunder-god-hammer-modules.json').read_text(encoding='utf-8-sig'))
def walk(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k=='mesh' and isinstance(v,str):yield v
            else:yield from walk(v)
    elif isinstance(value,list):
        for v in value:yield from walk(v)
paths=sorted(set(walk(data)))
for path in paths:
    mesh=u.load_asset(path)
    check('load '+path,isinstance(mesh,u.StaticMesh))
    if not mesh:continue
    mats=mesh.get_editor_property('static_materials')
    check('material slots '+mesh.get_name(),bool(mats) and all(m.material_interface for m in mats),materials=[m.material_interface.get_path_name() if m.material_interface else None for m in mats])
    if 'ribbed_light_V8' in path:
        box=mesh.get_bounding_box()
        # FBX import mirrors Blender Y; compare the UE-space envelope.
        check('light seat V8 has no external cutter bar',box.min.y>=-5.87 and box.max.y<=6.01,y_min_cm=box.min.y,y_max_cm=box.max.y)
audio=P.parent/'JiLeiRecordedCurrentV2'
manifest=json.loads((audio/'audio_manifest.json').read_text(encoding='utf-8'))
folder='/Game/Weapons/ThunderGodHammer20261028/JiLeiRecordedCurrentV2'
meta=u.load_asset(folder+'/MS_JiLei_CurrentRandom')
check('recorded current MetaSound saved',meta and meta.get_class().get_name()=='MetaSoundSource')
if meta:
    stored_hash=u.EditorAssetLibrary.get_metadata_tag(meta,'AudioSourceSHA256')
    check('MetaSound selected recording provenance',stored_hash==manifest['source_sha256'],stored_sha256=stored_hash)
registry=u.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous([folder],False)
options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True)
deps={str(x) for x in (registry.get_dependencies(folder+'/MS_JiLei_CurrentRandom',options) or [])}
for clip in manifest['clips']:
    path=folder+'/'+clip['name'];wave=u.load_asset(path)
    check('recording dependency '+clip['name'],path in deps,loaded=bool(wave))
    if wave:
        check('recording duration '+clip['name'],abs(wave.get_editor_property('duration')-clip['seconds'])<.005 and not wave.get_editor_property('looping'),seconds=wave.get_editor_property('duration'))
    check('source cut checksum '+clip['name'],hashlib.sha256((audio/clip['file']).read_bytes()).hexdigest()==clip['sha256'])
mapping=json.loads((P.parent/'GripIcons20261101/mapping.json').read_text(encoding='utf-8'))
for row in mapping['items']:
    path='/Game/ColdSteelData/AttachmentIcons20260913/'+row['key']
    tex=u.load_asset(path)
    check('grip icon '+row['key'],isinstance(tex,u.Texture2D) and (R/'Content/ColdSteelData/AttachmentIcons20260913'/(row['key']+'.png')).exists())
report=dict(passed=all(r['passed'] for r in rows),checks=rows,modified_assets=False,rendered=False)
(P/'assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['passed']:raise RuntimeError('Asset audit failures; see assets.json')
print('THOR_ASSET_AUDIT_COMPLETE',len(rows),flush=True)
