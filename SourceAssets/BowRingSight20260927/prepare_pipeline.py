"""Reuse the project's saved-asset import and serialized background build route."""
from pathlib import Path
P=Path(__file__).parent
old=P.parent/'BowWoodSight20260926'
text=(old/'import_assets.py').read_text(encoding='utf8')
for before,after in [
    ('WoodSightV12','RingSightV17'),
    ('SM_Bow_CarvedWoodSight','SM_Bow_FineRingSight'),
    ('CarvedBowWood','FineBowWood'),
    ('WaxedLinen','FineWaxedLinen'),
    ('PaleWoodInlay','EndgrainInlay'),
    ('M_Bow_CarvedWood','M_Bow_FineRingWood'),
    ("(1,1,1),.42","(1,1,1),.50"),
    ("(.105,.068,.038),.84","(.10,.062,.033),.85"),
    ("(.48,.31,.145),.60","(.34,.205,.095),.57"),
    ('scalar(mat,.55)','scalar(mat,.35)'),
    ('BOW_WOOD_SIGHT_SAVED','BOW_FINE_RING_SIGHT_SAVED'),
]:
    text=text.replace(before,after)
text=text.replace('L.recompile_material(mat);save(mat);materials[slot]=mat',
    "errors=L.recompile_material(mat)\n    if errors:raise RuntimeError('Material compilation failed '+str(errors))\n    save(mat);materials[slot]=mat")
text=text.replace('task.automated=True;task.replace_existing=name in r[\'saved\'];task.save=False;',
    "task.automated=True;task.replace_existing=False;task.save=False;")
text=text.replace("fresh(name);opt=u.FbxImportUI();", "fresh(name)\n    if name in r['saved']:\n        raise RuntimeError('Changed FBX requires a fresh candidate asset name; existing saved asset preserved')\n    opt=u.FbxImportUI();")
text=text.replace('opt.static_mesh_import_data.auto_generate_collision=False',
    'opt.static_mesh_import_data.auto_generate_collision=False\n    opt.static_mesh_import_data.build_nanite=False\n    opt.static_mesh_import_data.generate_lightmap_u_vs=False')
(P/'import_assets.py').write_text(text,encoding='utf8')
old=P.parent/'BowNockFlow20260927'
for filename in ('run_import.ps1','run_build.ps1'):
    text=(old/filename).read_text(encoding='utf8')
    text=text.replace('BowNockFlow20260927','BowRingSight20260927')
    text=text.replace('bow-nock-flow-v16','bow-ring-sight-v17').replace('build-editor-v16','build-editor-v17')
    text=text.replace('Bow V16','Bow V17')
    (P/filename).write_text(text,encoding='utf8')
print('V17_PIPELINE_WRITTEN')
