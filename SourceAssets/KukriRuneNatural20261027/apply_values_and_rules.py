"""Publish approved rune values and the requested percentage presentation rule."""
import json, re, shutil
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
def save(path,text):
    relative=path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path('PersonalSkills')/path.relative_to(Path('C:/Users/allan/.codex/skills'))
    before=P/'Before'/relative
    if path.exists() and not before.exists():
        before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,before)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8')

values={
    'knife_mark_wing':{'range_mult':1.15,'stamina_mult':1.05},
    'knife_mark_knot':{'martial_damage_mult':1.10,'martial_cooldown_mult':.95},
    'knife_mark_peaks':{'physical_armor_penetration':.10,'toughness_damage_mult':1.15},
}
labels={'range_mult':'攻击距离','stamina_mult':'攻击体力消耗','martial_damage_mult':'武技伤害',
        'martial_cooldown_mult':'武技冷却','physical_armor_penetration':'物理防御穿透','toughness_damage_mult':'削韧'}
for rel in ('Content/ColdSteelData/shared-knife-component-options.json',
            'SourceAssets/KukriComponentVariants20261026/shared-knife-component-options.json'):
    path=ROOT/rel
    raw=path.read_text(encoding='utf-8-sig');data=json.loads(raw)
    for column in data['columns']:
        for option in column['options']:
            if option['id'] in values:
                stats=values[option['id']];option['stats']=stats;option['effects']=[]
                for key,value in stats.items():
                    percent=(value if key=='physical_armor_penetration' else value-1)*100
                    lower=key in ('stamina_mult','martial_cooldown_mult')
                    option['effects'].append({'text':f'{labels[key]}{percent:+.0f}%',
                                              'benefit':1 if (percent<0 if lower else percent>0) else -1})
            for effect in option.get('effects',[]):
                text=effect['text'].replace('改造暴击率','暴击率').replace('暴击伤害加成','暴击伤害')
                effect['text']=re.sub(r'\s+([+-]\d+(?:\.\d+)?%)$',r'\1',text)
    if path.read_text(encoding='utf-8-sig')!=raw:raise RuntimeError('Concurrent catalog change: '+str(path))
    save(path,json.dumps(data,ensure_ascii=False,indent=2)+'\n')

# Keep the previous source publishers from restoring the retired presentation.
for rel in ('SourceAssets/KukriLanyardBalance20261027/apply_catalog.py','SourceAssets/KukriPommelBalance20261027/apply_catalog.py'):
    path=ROOT/rel;text=path.read_text(encoding='utf-8-sig')
    text=text.replace("'改造暴击率'","'暴击率'").replace("{LABELS[key]} {percent:+.0f}%","{LABELS[key]}{percent:+.0f}%")
    save(path,text)
path=ROOT/'SourceAssets/ZhenmoRune20261005/catalog_extension.py'
save(path,path.read_text(encoding='utf-8-sig').replace('暴击率 +25个百分点','暴击率+25%'))

rule='''# 百分比显示规则（用户确定，2026-10-27）

本规则适用于物品浮窗、改造选项／详情／总览、强化预览，以及向用户提供的数值方案和交付说明。与旧的名称或百分比写法冲突时，本规则优先；不改变原有公式、作用范围、叠加方式及真实计算值。

- 保留中文属性名，用阿拉伯数字和 `%` 表示百分比：`暴击率+10%`、`暴击伤害+10%`、`攻击体力消耗-10%`。不写“百分点”“百分之十”等中文百分比单位；不是将界面改成英文。
- 行内说明使用“属性名+带符号数值%”，不插入空格或括号。已有两列布局保留：左列属性名，右列 `+10%`／`-10%`；不为了文字拼接破坏横向布局。
- 统一名称为“暴击率”“暴击伤害”，不再使用“改造暴击率”“暴击率加成”“暴击伤害加成”等同义名称；代码共用 `ColdSteelWeaponText.h`。
- 百分比加成与倍率实值分开：直接改造显示 `+10%`，组合实值可保留 `1.10×`。暴击率的加算规则和暴击伤害的原公式不因显示格式变化而更改，也不能把 `1.10×` 直接写成 `+110%`。
- 能力卡保留“配件直接增减＋当前组合实值＋相对该槽原厂差值”。达到上限后，直接加成仍显示，实际零差值用中性色，并说明当前实际变化为 0。
- 条件触发效果仍放在特效段，数值使用 `%`；只列直接属性、不展开分段与附加伤害派生值的规则继续有效。

开发公式与源码注释可保留区分加算／乘算所需的术语；玩家文案、数值方案和交付说明遵循上面的显示格式。
'''
for skills in (Path('C:/Users/allan/.codex/skills'),ROOT/'skills'):
    ui=skills/'ue5-ui-umg-slate';weapon=skills/'ue5-weapon-workflow'
    save(ui/'references/percentage-display.md',rule)
    path=ui/'references/weapon-tooltip-schema.md';text=path.read_text(encoding='utf-8-sig')
    marker='**2026-10-27 百分比显示优先规则**：使用 `暴击率+10%`、`暴击伤害+10%`，不使用中文百分比单位；名称、行内格式及与实值的区别按[百分比显示规则](percentage-display.md)。本条覆盖旧写法，不更改计算公式。\n\n'
    if marker not in text:text=text.replace('\n\n','\n\n'+marker,1)
    save(path,text)
    path=weapon/'references/attachment-detail-presentation.md';text=path.read_text(encoding='utf-8-sig')
    marker='**2026-10-27 百分比显示优先规则**：统一 `暴击率+10%`、`暴击伤害+10%` 等格式，详见[百分比显示规则](../../ue5-ui-umg-slate/references/percentage-display.md)。与旧的属性名、括号或中文百分比单位写法冲突时，本条优先；原有直接属性范围、实值／差值及特效分工不变。\n\n'
    if marker not in text:text=text.replace('\n\n','\n\n'+marker,1)
    text=text.replace('暴击率统一为“改造暴击率（+25%）”，实值／差值用 `%`，底层百分点相加的公式不变。','暴击率统一为“暴击率+25%”，实值／差值用 `%`，底层加算公式不变。')
    text=text.replace('括号表示该改造项','属性名后的带符号百分比表示该改造项')
    text=text.replace('指标（改造增减）＋当前组合实值','指标±N%＋当前组合实值')
    text=text.replace('物理伤害（+5%）、最大攻击距离（+15%）、体力消耗（+5%）','物理伤害+5%、最大攻击距离+15%、体力消耗+5%')
    text=text.replace('攻击速度（+10%）','攻击速度+10%')
    save(path,text)
    for skill,link in ((ui,'references/percentage-display.md'),(weapon,'../ue5-ui-umg-slate/references/percentage-display.md')):
        path=skill/'SKILL.md';text=path.read_text(encoding='utf-8-sig')
        marker=f'- **2026-10-27 优先规则**：浮窗、改造栏与数值交付统一写 `暴击率+10%`、`暴击伤害+10%`，不用中文百分比单位；按[百分比显示规则]({link})执行，覆盖旧显示写法，保留实际公式。\n\n'
        if marker not in text:
            start=text.index('\n---',text.index('---')+3)+4
            text=text[:start]+'\n\n'+marker+text[start:]
        save(path,text)

path=ROOT/'AGENTS.md';text=path.read_text(encoding='utf-8-sig')
marker='**数值显示规则（用户确定，2026-10-27）：浮窗、改造栏和数值交付统一使用 `暴击率+10%`、`暴击伤害+10%` 等格式，不使用中文百分比单位。** 本条覆盖旧显示写法，保留原计算公式、实际数值和双持归属；具体遵循 [百分比显示规则](skills/ue5-ui-umg-slate/references/percentage-display.md)。\n\n'
if marker not in text:text=marker+text
save(path,text)
print('Saved rune values, source publishers, project rules and both skill copies.')
