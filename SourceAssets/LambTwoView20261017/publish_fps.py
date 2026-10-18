import json,copy,sys,hashlib
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1];sys.path.insert(0,str(R/'SourceAssets/FoodGrip20261003'))
from lamb_food_motion import apply_lamb_motion
path=R/'Content/ColdSteelData/potion_use_motion.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
before=copy.deepcopy(data['roasted_large_lamb']);next_motion=apply_lamb_motion(copy.deepcopy(before),large=True)
data['roasted_large_lamb']['keys']=next_motion['keys']
note=' LambTwoView20261017: after bite completion, preserve camera depth and lower directly out of view.'
data['roasted_large_lamb']['authoring']+=note
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=R/'SourceAssets/LargeLamb20261014/grip_profile.json';profile=json.loads(path.read_text(encoding='utf-8-sig'));profile['keys']=next_motion['keys'];profile['authoring']+=note
path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'fps_motion.json').write_text(json.dumps(data['roasted_large_lamb'],indent=2))
print('LAMB_FIRST_PERSON_DOWNWARD_EXIT_SAVED')
