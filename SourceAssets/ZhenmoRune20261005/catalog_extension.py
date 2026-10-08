"""Idempotent catalog contribution: one exclusive legendary rune, no save rewrite."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
DATA=ROOT/'Content/ColdSteelData'
UE='/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005'
OPTION={
 'id':'zhenmo_rune','name':'镇魔符文','tier':'legendary',
 'weapons':['ue_xuanchi_zhenyue'],
 'description':'镇岳专属传说符文。八卦镇印与凌厉篆符交织，折锋金线沿剑脊贯通。',
 'special_effects':[
  '暴击触发｜攻击暴击展开镇魔阵，持续15秒；再次暴击刷新时间，效果不叠加。',
  '镇魔阵｜随玩家移动，半径15米。阵内怪物受到的全部伤害提高25%，移动速度降低50%；离阵即解除。'],
 'effects':[
  {'text':'暴击率 +25个百分点','benefit':1},
  {'text':'攻击暴击触发镇魔阵，持续15秒；重复触发刷新，不叠加','benefit':1},
  {'text':'阵法随玩家移动，半径15米','benefit':1},
  {'text':'阵内怪物受到的全部伤害 +25%','benefit':1},
  {'text':'阵内怪物移动速度 -50%；离阵即解除','benefit':1}],
 'stats':{'critical_chance_add':25,'zhenmo_seconds':15,'zhenmo_radius_cm':1500,
          'zhenmo_damage_taken_bonus':.25,'zhenmo_slow':.5}}
def update(file,fn):
    original=file.read_bytes();value=json.loads(original.decode('utf-8-sig'));fn(value)
    before=P/'Before'/file.relative_to(ROOT);before.parent.mkdir(parents=True,exist_ok=True)
    if not before.exists():before.write_bytes(original)
    if file.read_bytes()!=original:raise RuntimeError('Concurrent edit: '+str(file))
    file.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def install():
    def options(root):
        slot=next(x for x in root['columns'] if x['key']=='blade_2')
        for row in slot['options']:
            if row['id'] in ('auspicious_cloud_rune','mountain_rune'):row['tier']='special'
        slot['options']=[x for x in slot['options'] if x['id']!='zhenmo_rune']+[OPTION]
    update(DATA/'melee-gunsmith.json',options)
    def status(root):
        root['effects']=[x for x in root['effects'] if x['type']!='zhenmoField']+[
          {'type':'zhenmoField','icon':'☯','name':'镇魔八卦阵','kind':'buff','group':'weapon',
           'color':'E2B653','description':'暴击展开随身八卦阵，半径15米；阵内怪物承伤提高25%，移动速度降低50%。持续15秒，暴击刷新。'}]
    update(DATA/'status_effects.json',status)
if __name__=='__main__':install()
