import json,sys
from pathlib import Path
ROOT=Path(__file__).parent;weapon,variant=sys.argv[sys.argv.index('--')+1:]
source=(ROOT/'check_thumb_gun.py').read_text().replace('O=Path(__file__).parent','O=ROOT').replace('D=O/weapon/variant',"D=ROOT.parent/'CantedGripMigration20260911'/weapon/variant").replace("(D/'thumb_gun.json')","(O/('before_thumb_gun_'+variant+'.json'))")
exec(compile(source,str(ROOT/'thumb_gun_before_generated.py'),'exec'))
new=json.loads((ROOT/weapon/variant/'thumb_gun.json').read_text());old=json.loads((ROOT/('before_thumb_gun_'+variant+'.json')).read_text());new_only={k:{part:count for part,count in hits.items() if part not in old.get(k,{})} for k,hits in new.items()};new_only={k:v for k,v in new_only.items() if v};out={'new_contact_samples':sum(bool(v) for v in new.values()),'before_contact_samples':sum(bool(v) for v in old.values()),'new_only_parts_at_sample':new_only};(ROOT/weapon/variant/'thumb_gun_comparison.json').write_text(json.dumps(out,indent=2));print('THUMB_GUN_COMPARISON',weapon,variant,out,flush=True)
