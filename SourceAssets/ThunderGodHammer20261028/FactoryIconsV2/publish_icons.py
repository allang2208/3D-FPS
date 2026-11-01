"""Publish the four real factory components and new legendary seat icon, exact keys only."""
import json,shutil,hashlib,datetime
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
D=R/'Content/ColdSteelData/AttachmentIcons20260913'
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
archive=R/'trash'/('ThunderHammerIcons-'+stamp);archive.mkdir(parents=True,exist_ok=False)
rows=[]
for slot in ['head_mount','hammer_heads','grip','pommel','guan_lei_seat']:
    keys=['ue_thunder_god_hammer_head_mount_guan_lei_seat'] if slot=='guan_lei_seat' else ['ue_thunder_god_hammer_category_'+slot,'ue_thunder_god_hammer_'+slot+'_false']
    source=P/'Final'/(slot+'.png')
    for key in keys:
        dest=D/(key+'.png');old_hash=None
        if dest.exists():
            old_hash=hashlib.sha256(dest.read_bytes()).hexdigest();shutil.copy2(dest,archive/dest.name)
        shutil.copy2(source,dest)
        rows.append({'key':key,'source':str(source),'destination':str(dest),'old_sha256':old_hash,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
receipt={'complete':True,'weapon':'ue_thunder_god_hammer','unique_new_icons':5,'runtime_png_keys':rows,'archive':str(archive),'retained_empty_rune':'ue_thunder_god_hammer_rune_false','render_sources':'FactoryIconSources.blend and ../GuanLeiRebuildV2/GuanLeiSeatV2_IconSource.blend','frame_reference':'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png','runtime_tested':False}
(P/'deployment_manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
(archive/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('THUNDER_FACTORY_ICONS_PUBLISHED',len(rows))
