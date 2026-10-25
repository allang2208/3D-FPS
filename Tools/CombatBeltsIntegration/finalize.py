"""Record completed saves, catalog publication and necessary builds."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from combat_belts_common import *

builds={target:read(R/'Build'/('build-'+target+'.json')) for target in ('FPSGAMEEditor','FPSGAME')}
if any(v['exit_code']!=0 for v in builds.values()):raise RuntimeError('Finish the necessary builds before delivery')
records=[]
for which,row in BELTS.items():
    out=R/which;saved=read(out/'saved_assets.json');published=read(out/'published.json')
    if not saved['completed'] or not published['completed']:raise RuntimeError('Finish asset and catalog publication '+which)
    receipt=source(row)/'delivery.json';original=read(receipt)
    original.update(stage='native_models_and_unreal_assets_saved_and_published',unreal_assets_imported=True,item_catalog_published=True,
        integration_receipt=str(out/'published.json'),saved_assets_receipt=str(out/'saved_assets.json'),runtime_tested=False,multiplayer_tested=False)
    write(receipt,original)
    readme=P/'Tools'/row['stem']/'README.md';text=readme.read_text(encoding='utf-8-sig')
    marker='\n## 游戏接入状态（2026-10-25）\n'
    if marker in text:text=text.split(marker,1)[0]
    text+=marker+'\n本页上方记录 ModelR1 的制作阶段。后续游戏接入已由 `Tools/CombatBeltsIntegration` 完成：男女穿戴、三级 LOD、PBR、正面物品图标、掉落网格、物品目录和 +15 强化属性已保存发布。Editor/Game 已后台构建。运行、服装动作组合及联机未测试；接入回执位于 `SourceAssets/CombatBeltsIntegration20261025/'+which+'`。\n'
    readme.write_text(text,encoding='utf-8')
    records.append(dict(item=row['key'],name=row['name'],assets=saved,published=str(out/'published.json')))
write(R/'delivery.json',dict(completed=True,records=records,builds=builds,asset_execution=read(R/'asset-execution.json'),
    runtime_tested=False,multiplayer_tested=False,interactive_editor_started=False,
    inventory_icons_generated=True,acceptance_renders_generated=False,
    fit_scope='Jason and Kaitlin native ST6 waist reference; no all-garment or animation acceptance claim'))
for filename,old,new in (
    ('melee-stamina-cost-20261025.md','腰带物品本身仍处于制作阶段，尚未写入游戏物品目录。','腰带物品已通过 CombatBeltsIntegration20261025 接入游戏物品目录，实际游戏与联机由用户测试。'),
    ('spell-mana-cost-20261025.md','腰带仍处于模型与物品配方制作阶段，未发布至游戏物品目录。本次修改的是全局施法费用算法。','腰带已通过 CombatBeltsIntegration20261025 完成 UE 资产与游戏物品目录接入。本页记录全局施法费用算法，实际游戏与联机由用户测试。')):
    path=P/'Docs/Combat'/filename;text=path.read_text(encoding='utf-8-sig')
    if old in text:path.write_text(text.replace(old,new),encoding='utf-8')
doc=P/'Docs/Items/combat-belts-integration-20261025.md';doc.parent.mkdir(parents=True,exist_ok=True)
doc.write_text('''# 破阵与星律腰带游戏接入（2026-10-25）

两款腰带的制作源、UE 资产和游戏目录均已落盘。不是只保存导入脚本。最终记录为 `SourceAssets/CombatBeltsIntegration20261025/delivery.json`。

| 物品 | 基础属性 | 每级强化 | +15 属性 |
| --- | --- | --- | --- |
| 破阵近战腰带 | 近战攻速 +5%，近战体力消耗 -10% | 攻速 +0.5 个百分点，减耗 +1 个百分点 | 攻速 +12.5%，减耗 25% |
| 星律导能腰带 | 魔法冷却 -2.5%，法力消耗 -10% | 冷却缩减 +0.5 个百分点，减耗 +1 个百分点 | 冷却 -10%，减耗 25% |

两者使用腰带槽 10，占 3×2 格，零防御，单件强化上限 +15。侧挂刀鞘支架、磨刀石袋、符片匣和卷轴筒为外观附件，不新增库存或额外物品格。

## 资产与接入

- 目录 ID：`ue_melee_combat_belt`、`ue_arcane_conduit_belt`。
- 资产分别位于 `/Game/Characters/ModularOutfit20260924/MeleeCombatBelt20261025/IntegrationR1` 与 `ArcaneConduitBelt20261025/IntegrationR1`。
- 每款都有 Jason/Kaitlin 原生蒙皮、三级 LOD、独立静态掉落与展示网格、完整 PBR 和正面扣具图标。LOD0 保留源模型完整可见细节；远景派生为 55% 与 22% 面数比例。
- 导入阶段报告的退化倒角/缝线 UV 与远景重复三角形已在导出管线修复；有效 UV、位置、法线和权重保留，只清除零面积面及完全重复面。正式图标同步从修复后的几何生成。
- 男女本人低头与世界身体均由 `modular_outfits.json` 的 `rig_meshes`、`owner_body_meshes` 接入；使用现有异步加载和 Leader Pose。
- 掉落继续使用现有物理根与服务端拾取事务。属性和 +15 强化走既有装备、浮窗、摘要及强化预览入口。
- `RefreshBeltTuning` 加入两个 ID，保留实例身份、位置和强化等级；沿现有客机影子档案、网络镜像与持久化入口同步目录数值。没有新增逐帧 RPC、另一份库存或自定义存档字段。
- 父级 `/Game/Characters/ModularOutfit20260924` 已在现有打包目录中，物品 PNG 沿既有 `ColdSteelData` 路径发布。

## 使用与范围

下一次启动游戏后，可在“基本调参 → 生成物品 → 装备 → 腰带”找到两款腰带。

体力与法力均按单件内部相加、不同装备相乘处理；单件减耗最多 50%，最终至少保留基础费用 20%。具体乘区见 `Docs/Combat/melee-stamina-cost-20261025.md` 与 `Docs/Combat/spell-mana-cost-20261025.md`。

模型依据已保存的男女 ST6 裤腰制作；未进行其他衣物组合、动画、游戏或联机验收。不能把原生绑定和资产落盘视为任意服装无穿模保证。紫晶采用实时薄透射近似，源 Blend/GLB 保留离线石英材质。

Editor 与 Game 目标后台构建成功；日志见本次 `Build/`。本轮只制作正式物品图标，未启动交互编辑器、游戏或测试。
''',encoding='utf-8')
print('COMBAT_BELTS_INTEGRATED',','.join(v['item'] for v in records),flush=True)
