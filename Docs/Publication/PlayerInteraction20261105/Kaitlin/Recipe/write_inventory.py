import json
from pathlib import Path
import os
P=Path(os.environ['FPSGAME_PROJECT']).resolve();W=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
items=read(P/'Content/ColdSteelData/items.json')
rows=[]
def add(key,name,group,route,action):
    rows.append(dict(id=key,name=name,group=group,route=route,action=action,visual_acceptance=False))
for gun in read(P/'Content/ColdSteelData/gunsmith.json')['weapons']:
    key=gun['id'];pistol=items[key].get('weaponType')=='pistol'
    add(key,items[key].get('name',gun['name']),'枪械',
        'FPSPlayerBodyEquipment → FFPSBodyGripRig → SinglePistolContact / 双持独立手链' if pistol else
        'FPSPlayerBodyEquipment → FFPSBodyGripRig → FPSBodyRifleHold / FitHandPair',
        '已逐项核对当前目录和共用消费者；主手挂点、扶握及活动接触按当前身体重新映射，保留现有路径。')
for item in read(P/'Content/ColdSteelData/melee-gunsmith.json')['weapons']:
    key=item['id']
    add(key,items[key]['name'],'双手剑／长刀','FPSBodySwordMotion → NativeSwordGrip / 共用双手求解',
        '修复原生双手动作的女性掌心关系；普通待机和通用攻击继续使用已有实时握点。唐刀旋风、斩马刀赤霄专用段分别保留。')
for key in ('ue_steel_warhammer','ue_runebound_warhammer'):
    add(key,items[key]['name'],'双手锤','Warhammer.Idle / Walk / Jog / FullBody → 原生动作',
        '修复女性待机、移动与全部当前原生战斗段的双手关系；保留沿锤柄滑动、转握和男性动作时钟。符文锤另含终焉双段映射。')
add('ue_kukri',items['ue_kukri']['name'],'单手近战','BuildKukriGrip → FFPSBodyGripRig',
    '已核对独立挂点及当前女性动作映射；按女性手掌重算刀柄和手指，保留当前单手路径。')
for key,value in read(P/'Content/ColdSteelData/bows.json').items():
    add(key,value['name'],'弓','Bow.Sparrow.* → UpdateNativeBowContacts',
        '修复五段女性动作中沿用男性手骨坐标的握弓／弦接触曲线；使用女性掌心坐标转换。')
for key,value in read(P/'Content/ColdSteelData/staffs.json').items():
    add(key,value['name'],'法杖','FPSBodyStaffGrip → 当前身体 Mount / StaffHandRotation',
        '已核对四种握柄变体的同一入口；男性专用手指厚度补偿已有 HasJasonFit 限定，保留女性独立掌心映射。')
add('ue_alchemy_spellbook',items['ue_alchemy_spellbook']['name'],'副手书','SpellbookAuthoredGrip → FFPSBodyGripRig',
    '已核对持书挂点和指骨使用当前身体；保留手枪／法杖配书及阅读所有权。')
for key,value in read(P/'Content/ColdSteelData/production_tools.json').items():
    add(key,value['name'],'采集工具','BuildShovelGrip / FFPSBodyGripRig → CaptureMotionHand',
        '已核对斧、镐、铲各自模型入口；双手接触来自实际装备与当前身体映射，未套用战锤的原生待机跳过分支。')
(W/'weapon_inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
lines=['# 女性角色第三人称武器握持排查与修复','',
 '2026-10-24。范围为用户确认的第三人称全身视角。逐项读取当前武器目录、男女动作引用和实际消费者；未启动游戏、PIE 或截图／渲染。',
 '', '## 定位与修复','',
 '- 女性全身重定向改变了左右手的相对距离；带 `NativeWarhammerSourceCarry` / `NativeWarhammerGrip` / `NativeSwordGrip` 的原生分支保留作者双臂，跳过通用握点求解。原先男性接触关系因此没有在女性骨长上保留。',
 '- 双手锤待机在五个初始样本中的相对握点偏差约 5.69–6.03 cm。作者修订按每个原始采样帧恢复男性武器局部接触，转换为女性原生掌心坐标，再解算女性肩肘腕。两臂需要额外可达空间时共同移动目标；不改变骨段长度或武器缩放。',
 '- 原生剑的过顶、上挑、旋风、唐刀旋风和赤霄段按各自源片段处理，保留接触变化及剑柄转动曲线。',
 '- 弓的五个女性片段原样复制了男性 `SparrowBowGrip*` / `SparrowBowNock*` 局部接触曲线；已将这些标记转换到女性掌心坐标。',
 '- 38 个独立动画资产对应 56 个女性映射。男性配置、第一人称 V9、伤害／命中／换弹时钟、装备缩放保持不变。','',
 '## 逐武器清单','',
 '下表的“保留”表示读取当前路径后未发现同类原生动作跳过问题，不表示已完成游戏画面验收。挂点／指骨骨架适配与最终皮肤贴合是不同层次。','',
 '| ID | 名称 | 类别 | 处理 |','| --- | --- | --- | --- |']
for row in rows:lines.append(f"| `{row['id']}` | {row['name']} | {row['group']} | {row['action']} |")
lines += ['', '## 保存与使用','',
 '- 新资产：`/Game/Characters/KaitlinPlayer20261023/WeaponContacts20261024/Animations/`。复制女性旧片段后仅修改所需手臂轨道或接触曲线，其余轨道、时长和语义同步标记保留。',
 '- 接入：`Content/ColdSteelData/player_body.json.body_variants.kaitlin.clips` 的 56 个明确角色键，使用 `Tools/PlayerBody/config_transaction.py`；保留旧资产供恢复。现有 Kaitlin Cook 根目录已覆盖新资产。',
 '- 作者源、逐帧修订、保存与配置回执：`SourceAssets/KaitlinWeaponContacts20261024/ContactFitV1/`。逐武器机器清单为 `weapon_inventory.json`。',
 '- 此次没有改 C++，无需重建 Editor/Game 二进制；已完成动画资产压缩与保存。下一次创建／重新加载女性身体时读取新动作映射。',
 '- 尚未运行游戏、真实联机或画面验收。请在第三人称确认女性双手锤待机／走跑、挥击／格挡、双手剑专用动作、弓的握把和勾弦；男性与其他装备的观感由用户测试。','']
(W/'report.md').write_text('\n'.join(lines),encoding='utf-8')
print('WEAPON_INVENTORY',len(rows),'definitions')
