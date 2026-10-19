"""Publish saved ST6 geometry/materials and synchronize its repeatable entrypoints."""
import json,sys,shutil,hashlib,runpy
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1];OLD=O.parent/'ST6Reset20261017';S90=O.parent/'BenelliM4Super9020261006'
apply=runpy.run_path(str(O/'recipe.py'))['apply']
receipt=json.loads((O/'import_receipt.json').read_text())
if not receipt.get('completed') or receipt.get('material_compile_errors'):raise RuntimeError('ST6 assets are not complete')
for name in ('collar.json','world_shirt.json','pickup.json'):
    if receipt['source_sha256'].get(name)!=hashlib.sha256((O/name).read_bytes()).hexdigest():raise RuntimeError('Unsaved '+name)
icon=json.loads((O/'icon_saved.json').read_text())
if icon['source_sha256']!=hashlib.sha256((O/'ue_st6_sleeves.png').read_bytes()).hexdigest():raise RuntimeError('Unsaved icon')

def backup(path):
    dest=O/'Before'/path.relative_to(R)
    if path.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)

path=R/'Content/ColdSteelData/modular_outfits.json';backup(path)
cfg=json.loads(path.read_text(encoding='utf-8-sig'));apply(cfg)
path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for path in (R/'Content/ColdSteelData/Icons/Super90Source20261006/ue_st6_sleeves.png',S90/'EquipmentIcons/ue_st6_sleeves.png',OLD/'ue_st6_sleeves.png'):
    backup(path);shutil.copy2(O/'ue_st6_sleeves.png',path)
for path in (S90/'Exports/SM_ue_st6_sleeves.fbx',OLD/'SM_ue_st6_sleeves.fbx'):
    backup(path);shutil.copy2(O/'SM_ue_st6_sleeves.fbx',path)

# Preserve the original sleeve restoration recipe, then apply this refinement.
path=OLD/'recipe.py';text=path.read_text();marker='    # ST6Refine20261018: retain the native neck and hem refinement.'
if marker not in text:
    backup(path)
    text=text.replace('    return config',marker+"\n    from pathlib import Path\n    import runpy\n    refinement=runpy.run_path(str(Path(__file__).parent.parent/'ST6Refine20261018/recipe.py'))\n    refinement['apply'](config)\n    return config")
    path.write_text(text,encoding='utf-8')

wrapper='''"""ST6 refinement production entry; original sources stay available for rebuilding."""
from pathlib import Path
O=Path(__file__).parent;TASK=O.parent/'ST6Refine20261018'
for name in NAMES:
    file=TASK/name
    exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file),'__name__':'__main__'})
'''
for filename,names in [('import_pickup_icon.py',('finish_assets.py',)),('render_icon.py',('author_collar.py','render_icon.py'))]:
    path=OLD/filename;backup(path)
    text=wrapper.replace('NAMES',repr(names))
    if filename=='render_icon.py':
        text+='\nimport shutil\nfor name in ("ue_st6_sleeves.png","SM_ue_st6_sleeves.fbx"):\n    shutil.copy2(TASK/name,O/name)\n'
    path.write_text(text,encoding='utf-8')
(O/'published.json').write_text(json.dumps(dict(item='ue_st6_sleeves',saved_assets=receipt['saved'],icon=icon['asset'],profile_count=len(cfg['items']['ue_st6_sleeves']['rig_meshes']),game_tested=False),indent=2))
print('ST6_REFINEMENT_PUBLISHED',flush=True)
