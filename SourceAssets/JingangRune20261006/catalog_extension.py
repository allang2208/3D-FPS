"""One legendary rune; existing parts and player saves stay owned by their current transactions."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
UE='/Game/Weapons/XuanChiZhenYue20261004/JingangRune20261006'
OPTION={'id':'jingang_rune','name':'金刚符文','tier':'legendary','weapons':['ue_xuanchi_zhenyue'],
 'description':'镇岳专属传说符文。金刚经行草鎏入剑脊，随生命状态显现无住、如如、破相三境；持剑护体，临危返照。',
 'stats':{'jingang_bonus':.25,'jingang_high_threshold':.7,'jingang_low_threshold':.3,'jingang_leech_seconds':10,'jingang_leech_ratio':.1},
 'special_effects':[
  '高血量 · 生命≥70%｜物理伤害、魔法伤害提高25%。',
  '中血量 · 30%≤生命<70%｜攻击速度提高25%，技能冷却缩减25%。',
  '低血量 · 生命<30%｜双防、双伤、攻速与冷却缩减均变为50%，替代上述加成，不额外叠加。',
  '攻击吸血｜进入低血量获得10秒吸血，实际攻击伤害的10%转化为生命；低血量攻击命中刷新至10秒，回血脱离低血量保留剩余时间。',
  '解除｜切换武器或卸下符文，立即清除全部加成及吸血。'],
 'effects':[
  {'text':'持握时物理防御、魔法防御 +25%','benefit':1},
  {'text':'生命值 ≥70%：物理伤害、魔法伤害 +25%','benefit':1},
  {'text':'生命值 ≥30% 且 <70%：攻击速度 +25%，技能冷却缩减 25%','benefit':1},
  {'text':'生命值 <30%：物理／魔法防御、物理／魔法伤害、攻击速度、技能冷却缩减均为 +50%','benefit':1},
  {'text':'进入低血量获得10秒攻击吸血，实际伤害的10%转化为生命；低血量攻击命中刷新至10秒','benefit':1},
  {'text':'回血离开低血量保留剩余吸血时间；切换武器或卸下符文立即失去全部效果','benefit':0}]}
STATES=[
 ('jingangHigh','金刚·无住','應無所住，而生其心。生命≥70%：物理／魔法防御提高25%，物理／魔法伤害提高25%。'),
 ('jingangMiddle','金刚·如如','不取於相，如如不動。生命≥30%且<70%：物理／魔法防御提高25%，攻击速度提高25%，技能冷却缩减25%。'),
 ('jingangLow','金刚·破相','凡所有相，皆是虛妄。生命<30%：物理／魔法防御、物理／魔法伤害、攻击速度提高50%，技能冷却缩减50%。'),
 ('jingangLeech','金刚·返照','攻击造成的实际伤害有10%转化为生命。进入低血量触发10秒，低血量攻击命中刷新；离开低血量保留剩余时间，切武器立即解除。')]
def update(file,fn):
    raw=file.read_bytes();value=json.loads(raw.decode('utf-8-sig'));fn(value)
    b=P/'Before'/file.relative_to(ROOT);b.parent.mkdir(parents=True,exist_ok=True)
    if not b.exists():b.write_bytes(raw)
    if file.read_bytes()!=raw:raise RuntimeError('Concurrent edit '+str(file))
    file.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def install():
    def options(root):
        slot=next(x for x in root['columns'] if x['key']=='blade_2')
        slot['options']=[x for x in slot['options'] if x['id']!='jingang_rune']+[OPTION]
    update(DATA/'melee-gunsmith.json',options)
    def status(root):
        ids={x[0] for x in STATES}
        root['effects']=[x for x in root['effects'] if x['type'] not in ids]+[
          {'type':key,'icon':'金','name':name,'kind':'buff','group':'weapon','color':'E9BD67','description':description}
          for key,name,description in STATES]
    update(DATA/'status_effects.json',status)
if __name__=='__main__':install()
