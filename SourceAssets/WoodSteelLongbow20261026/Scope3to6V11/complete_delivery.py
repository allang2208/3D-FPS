"""Record production receipts; does not launch a test or reload any asset."""
from pathlib import Path
from datetime import datetime
import json

P=Path(__file__).parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assets=read(P/'import-receipt.json')
catalog_path=sorted(P.glob('catalog-receipt-*.json'))[-1]
catalog=read(catalog_path)
editor=read(P/'build-FPSGAMEEditor.json')
game=read(P/'HeaderRefresh/build-FPSGAME.json')
commandlet=read(P/'import_assets-commandlet.json')
result={
 'weapon':'bow_woodsteel','option':'highland_peakwatch_3_6x','name':'观峰变倍镜','tier':'Special',
 'model_authored':True,'asset_packages_saved':assets['complete'],'saved_package_count':len(assets['saved']),
 'catalog_installed_at':catalog['saved_at'],'catalog_receipt':str(catalog_path),
 'editor_build':editor,'game_build':game,'asset_commandlet':commandlet,
 'asset_commandlet_note':'All ten packages and the completion receipt were saved before an exit-time access violation in UColdSteelSkillPage::ReleaseSlateResources. No UI source was changed for this task.',
 'asset_directory':'/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V11',
 'icon':'/Game/ColdSteelData/AttachmentIcons20260913/FramedBows/bow_woodsteel_sight_highland_peakwatch_3_6x',
 'magnification':{'minimum':3,'maximum':6,'wheel_step':.5,'ads_only':True,'reset_on_reequip':True},
 'stats':{'ads_mult':1.25},
 'interactive_editor_started':False,'game_started':False,'gameplay_tested':False,
 'additional_acceptance_checks_run':False,'finished':datetime.now().isoformat()
}
(P/'completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PEAKWATCH_DELIVERY_RECORDED: assets='+str(len(assets['saved']))+', Editor='+str(editor['exit_code'])+', Game='+str(game['exit_code'])+', import shutdown='+str(commandlet['exit_code']))
