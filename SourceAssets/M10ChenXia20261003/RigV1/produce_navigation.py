from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parent
result=json.loads(u.M10Mawcrawler.build_map_navigation('/Game/GameMaps/DayNight_Lighting'))
(ROOT/'navigation_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if not result.get('saved'):raise RuntimeError(result.get('error','Navigation production did not save'))
u.log('M10_NAVIGATION_PRODUCTION_COMPLETE')
