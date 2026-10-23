"""Produce inventory art through the same UE assembly and capture as the bag UI."""
import json,os,shutil,struct,subprocess
from pathlib import Path

P=Path(__file__).resolve().parent;ROOT=P.parents[1];R=P/'InventoryIconV2'
ID='ue_runebound_warhammer'

def main():
    R.mkdir(exist_ok=True)
    icon=ROOT/'Content/ColdSteelData/Icons'/f'{ID}.png'
    before=icon.stat().st_mtime_ns if icon.exists() else 0
    env=os.environ.copy();env['UE_SKIP_UBT_SDK_SETUP']='1'
    command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        str(ROOT/'Tools/UI/build_weapon_catalog_icons.ps1'),'-Definitions',ID]
    result=subprocess.run(command,cwd=ROOT,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode or not icon.exists() or icon.stat().st_mtime_ns<=before:
        raise RuntimeError('Native inventory icon authoring did not write a fresh image')
    width,height=struct.unpack('>II',icon.read_bytes()[16:24])
    source=P/'Export'/f'{ID}.png';shutil.copy2(icon,source)
    receipt={'complete':True,'definition':ID,'source':'ColdSteelWeaponIconCatalog -Definition='+ID,
        'assembly':'Existing factory modular melee recipe and native PBR; no desaturation',
        'canvas':[width,height],'orientation':'Upright orthographic side view',
        'framing':'Silhouette centered; dominant axis fills 91 percent',
        'background':'Transparent; capture ShowOnlyComponents excludes arms and studio geometry',
        'runtime_png':str(icon),'author_export':str(source),
        'log':str(ROOT/'SourceAssets/WeaponInventoryIcons20260913'/f'export-{ID}.log'),
        'tests_run':False,'game_started':False,'editor_ui_started':False,'acceptance_rendered':False}
    (R/'production_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('RUNEBOUND_INVENTORY_ICON_AUTHORED '+str(icon))

if __name__=='__main__':main()
