from pathlib import Path
import json
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text(encoding='utf-8-sig'))
catalog=read('catalog_report.json');native=read('native_report.json')
report={'fixed':['hammer equipped passives excluded by tool selector','remote equipment lost rune MID and overlay state',
 'missing authoritative stamina and martial cooldown receipts for hammer owners'],
 'catalog_checks':len(catalog['checks']),'catalog_passed':catalog['passed'],
 'native_checks':native['count'],'native_failures':native['failures'],
 'native_authority_executed':native['native_authority_executed'],
 'game_build':read('game-build-receipt.json'),'editor_build':read('editor-build-receipt.json'),
 'native_run':read('native-audit-receipt.json'),'user_profile_modified':False,
 'real_network_transport_tested':False,'latency_loss_reconnect_tested':False,
 'visual_gameplay_acceptance':False,'notes':'Source review, normal builds and isolated native regression completed. Cross-process multiplayer acceptance remains open.'}
(P/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'catalog_checks':report['catalog_checks'],'native_checks':report['native_checks'],'native_failures':report['native_failures'],'game_build_exit':report['game_build']['exit_code'],'editor_build_exit':report['editor_build']['exit_code']}))
