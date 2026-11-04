"""Keep three masters; deploy category/factory keys; reuse six shared option icons."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
D=P.parents[2]/'Content/ColdSteelData/AttachmentIcons20260913'
G=Path(r'C:/Users/allan/.codex/generated_images/01a195a9-36a2-73c3-b35d-e1ea19859acf')
sources={'blade_1':'exec-1b7aaf3a-57cc-4097-bc12-aa1740727ddf.png','grip':'exec-125350b1-20a1-4e4b-a1b4-e63fb2377105.png','pommel':'exec-ce9e5dfc-2a82-4886-8f83-1673ae55e7c5.png'}
jobs=[]
for slot,name in sources.items():
    master=P/'Icons'/(slot+'.png');shutil.copy2(G/name,master)
    for key in ('ue_tactical_hatchet_category_'+slot,'ue_tactical_hatchet_'+slot+'_false'):
        dest=D/(key+'.png')
        if dest.exists() and not (P/'Before'/dest.name).exists():shutil.copy2(dest,P/'Before'/dest.name)
        shutil.copy2(master,dest);jobs.append({'key':key,'source':str(master),'runtime_png':str(dest)})
(P/'icon_deployments.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
(P/'icon_provenance.json').write_text(json.dumps({'tool':'built-in image_gen','source_files':sources,'prompt_file':'icon_prompts.json',
    'frame_reference':'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png','part_inputs':'IconInputs',
    'shared_options_reused':['grip_knife_grip_checkered','grip_knife_grip_leather','grip_knife_grip_laminate','pommel_knife_pommel_steel','pommel_knife_pommel_faceted','pommel_knife_pommel_ringed'],
    'runtime_tested':False},indent=2),encoding='utf-8')
print('HATCHET_FACTORY_ICONS_DEPLOYED 3 masters 6 keys')
