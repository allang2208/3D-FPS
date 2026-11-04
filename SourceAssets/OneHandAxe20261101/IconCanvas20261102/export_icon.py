"""Re-author the hatchet catalog PNG with the standard UE inventory studio.

The PNG and live icon keep the same authored 2x3 canvas at display time. This is
an asset export, not a game, profile load, screenshot or gameplay test.
"""
import json,os,shutil,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
PROJECT=P.parents[2]
OUT=P/'Icons';OUT.mkdir(exist_ok=True)
environment=os.environ.copy();environment['UE_SKIP_UBT_SDK_SETUP']='1'
command=[r'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',str(PROJECT/'FPSGAME.uproject'),
    '-run=ColdSteelWeaponIconCatalog','-Definition=ue_tactical_hatchet','-OutputDirectory='+str(OUT),
    '-AllowCommandletRendering','-NoTextureStreaming','-unattended','-nosplash','-RenderOffscreen','-nosound','-nop4',
    '-abslog='+str(P/'export.log')]
with (P/'export-console.log').open('w',encoding='utf-8') as log:
    subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True)
source=OUT/'ue_tactical_hatchet.png'
destinations=[PROJECT/'Content/ColdSteelData/Icons/ue_tactical_hatchet.png',P.parent/'Icons/ue_tactical_hatchet.png']
for target in destinations:shutil.copy2(source,target)
(P/'export_receipt.json').write_text(json.dumps({'saved':True,'pipeline':'ColdSteelWeaponIconCatalog','definition':'ue_tactical_hatchet',
    'source':str(source),'deployed':[str(p) for p in destinations],'canvas':[256,384],'framing':.91,
    'retains_canvas_in_catalog_and_live_brush':True,'gameplay_tested':False},indent=2),encoding='utf-8')
print('HATCHET_ICON_REBUILT_AND_DEPLOYED')
