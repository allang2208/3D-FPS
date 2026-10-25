"""Switch only Storm Drive model references and its model-derived inventory icon."""
import json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved.get('complete'):raise RuntimeError('Assets not yet saved')
written=[]
for variant,runtime,author in [('Steel','warhammer-modules.json','SteelWarhammer20261014'),('Runebound','runebound-warhammer-modules.json','RuneboundWarhammer20261022')]:
    for relative in ('Content/ColdSteelData/'+runtime,'SourceAssets/'+author+'/ModulesV1/catalog_base.json'):
        path=ROOT/relative;before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
        entry=data['slots']['head_mount']['storm_drive_seat'];entry.update(saved['parts'][variant],model_revision='StormDriveRuneV3')
        backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_bytes(before)
        tmp=path.with_suffix('.storm-drive-rune-v3.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog change '+relative)
        os.replace(tmp,path);written.append(relative)
icon='head_mount_storm_drive_seat.png';target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/icon
backup=P/'Before'/icon
if not backup.exists():shutil.copy2(target,backup)
shutil.copy2(P/icon,target)
(P/'published.json').write_text(json.dumps({'complete':True,'catalogs':written,'model_revision':'StormDriveRuneV3','saved_assets':saved['assets'],'gameplay_values_changed':False,'native_code_changed':False,'blender_crown_inspected':True,'blender_fine_rune_inspected':True,'game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('STORM_DRIVE_FINE_RUNE_V3_PUBLISHED')
