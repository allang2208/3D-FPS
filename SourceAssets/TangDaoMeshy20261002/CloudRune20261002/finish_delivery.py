"""Record the completed production import and build outputs; do not run tests."""
from pathlib import Path
import json,re

P=Path(__file__).resolve().parent
assets=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
catalog=json.loads((P/'catalog_receipt.json').read_text(encoding='utf-8'))
builds={}
for target,stem in [('FPSGAMEEditor','editor'),('FPSGAME','game')]:
    log=(P/('build-'+stem+'-console.log')).read_text(encoding='utf-8-sig',errors='replace')
    result=re.findall(r'Result:\s*(\w+)',log)
    if not result or result[-1]!='Succeeded':
        raise RuntimeError('Production build not completed for '+target)
    builds[target]={'result':result[-1],'log':'build-'+stem+'-console.log'}
delivery={'weapon':'ue_tang_dao','slot':'blade_2','id':'auspicious_cloud_rune','name':'祥云符文',
          'assets_saved':assets['assets'],'catalog_installed':catalog,
          'builds':builds,'appearance':'卷云主印、淡金云纹、玉青流光',
          'exclusive_gold_card':True,'native_mode':6,'runtime_tested':False,
          'editor_ui_opened':False,'game_started':False,'asset_authoring':'background Python commandlet',
          'generation_tool':'built-in image_gen','prompt_set':'imagegen_prompts.json',
          'source_images':['Artwork/CloudRune_Alpha.png','Icons/ue_tang_dao_blade_2_auspicious_cloud_rune.png'],
          'geometry_changed':False,'user_save_files_modified':False}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('TANGDAO_CLOUD_RUNE_DELIVERED assets='+str(len(assets['assets']))+'; runtime_tested=False')
