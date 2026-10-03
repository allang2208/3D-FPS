"""Record production outputs for the requested kill-stamina change."""
from pathlib import Path
import json,re

P=Path(__file__).resolve().parent
cloud=P.parent
builds={}
for target,stem in [('FPSGAMEEditor','editor'),('FPSGAME','game')]:
    path=P/('build-'+stem+'-console.log')
    result=re.findall(r'Result:\s*(\w+)',path.read_text(encoding='utf-8-sig',errors='replace'))
    if not result or result[-1]!='Succeeded':raise RuntimeError('Production build incomplete: '+target)
    builds[target]={'result':result[-1],'log':path.name}
catalog=json.loads((cloud/'catalog_receipt.json').read_text(encoding='utf-8'))
delivery={'weapon':'ue_tang_dao','slot':'blade_2','id':'auspicious_cloud_rune',
    'effects':catalog['effects'],'builds':builds,
    'trigger':'confirmed attributed death while current equipped weapon has the rune',
    'reward_independent':True,'once_per_victim':True,'uses_current_max_stamina':True,
    'restoration_capped_at_maximum':True,'extra_ticks_or_timers':False,
    'assets_reimported':False,'editor_opened':False,'game_started':False,
    'user_save_files_modified':False,'runtime_tested':False}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
original=json.loads((cloud/'delivery.json').read_text(encoding='utf-8'))
original['catalog_installed']=catalog
original['builds']={target:{'result':row['result'],'log':'KillRecovery20261002/'+row['log']} for target,row in builds.items()}
original['kill_recovery_update']={'record':'KillRecovery20261002/delivery.json','builds':builds,'runtime_tested':False}
(cloud/'delivery.json').write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CLOUD_RUNE_KILL_STAMINA_DELIVERED ratio=0.15; runtime_tested=False')
