"""Produce the RSH inventory icon from its current UE assembly and materials."""
import json
import struct
import subprocess
from pathlib import Path

O=Path(__file__).resolve().parent
P=O.parents[1]
recipe=P/'SourceAssets/RSH12InventoryIcon20261006/export_icon.ps1'
subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(recipe)],check=True,cwd=P)
target=P/'Content/ColdSteelData/Icons/ue_rsh12.png'
size=struct.unpack('>II',target.read_bytes()[16:24])
(O/'icon_receipt.json').write_text(json.dumps({
    'file':str(target),'source':'Current RSH-12 UE factory assembly and materials',
    'mesh':'/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny',
    'recipe':str(recipe),'size':list(size),'purpose':'Inventory icon production',
    'acceptance_render':False
},ensure_ascii=False,indent=2),encoding='utf-8')
print('RSH12_CATALOG_ICON_SAVED')
