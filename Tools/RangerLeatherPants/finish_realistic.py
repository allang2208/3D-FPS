"""Record the successfully saved source revision; does not publish to UE."""
import json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/RangerLeatherPants20261021';R=BASE/'RealisticCutV3'
receipt=json.loads((R/'delivery.json').read_text(encoding='utf-8'))
if not receipt.get('completed'):raise RuntimeError('Model save has not completed')
record=dict(revision='RealisticCutV3',root=str(R),blend=receipt['blend'],exports=receipt['exports'],status='Authored and exported; no new preview render, UE integration or runtime test',previous_revision='AtelierFinishV2',preview_rendered=False,ue_imported=False,runtime_tested=False,concept=str(BASE/'Design/LeatherPants_Concept03_Realistic.png'))
(BASE/'latest_revision.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
concept_path=BASE/'Design/concept03.json';concept=json.loads(concept_path.read_text(encoding='utf-8'))
concept.update(status='Approved and modeled as RealisticCutV3; source and FBX exports saved',model_rebuilt=True,model_revision='RealisticCutV3',model_source=receipt['blend'],ue_assets_changed=False)
concept_path.write_text(json.dumps(concept,ensure_ascii=False,indent=2),encoding='utf-8')
archive=R/'Authoring';archive.mkdir(exist_ok=True)
for name in ('realistic_cut.py','realistic_surfaces.py','fits_realistic.py','export_realistic.py','finish_realistic.py','author.py','refine_geometry.py','fits.py','export.py'):
    shutil.copy2(P/'Tools/RangerLeatherPants'/name,archive/name)
(R/'production.json').write_text(json.dumps(dict(completed=True,revision=record,delivery=receipt,tests_performed=False,source_scripts=str(archive)),ensure_ascii=False,indent=2),encoding='utf-8')
print('REALISTIC_CUT_V3_RECORDED',json.dumps(receipt,ensure_ascii=False),flush=True)
