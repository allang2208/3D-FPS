# 改造台说明整理 · 2026-11-01

按 ue5-weapon-workflow / attachment-detail-presentation.md 与百分比显示规则整理。
本次仅修改显示文案、详情展示和作者脚本的文案输出，不调整玩法数值或资产绑定。

## 完成内容

- 寒晶：本武器近战攻击附加智力×50%＋精神×50%的魔法伤害；说明攻击倍率、目标魔法防御及符文栏兼容性。
- 精神迸发：明确寒晶双手剑的自带侵蚀由50%＋50%变为100%＋100%，其他附伤不翻倍。
- 时砂秘金：正式特效栏补全0.6秒延迟、30%实际伤害、伤害通道、0.5/1秒减冷却和触发边界。
- 火器变倍、热成像、全自动扳机、速装器余弹损失和装填衔接独立进入特效栏。
- 唐刀龙威说明修正为成功弹反，凤舞修正为闪避中实际躲过敌方攻击；未修改触发逻辑。
- 法杖补全杖头专精和移动加速的10%每层、10层上限与累加时长。
- 原厂与普通配件介绍精简；剔除重复属性、开发步骤及尚未接入状态描述。采集工具明确沿用原装外形。
- 详情按机制标题去重；取消旧 effects 的数值回退和脚架特例重复段；相同外观与基本说明只显示一次。
- 星陨天枢补上G飞剑冷却倍率卡；法杖百分比卡显示直接增减；弓拉弓速度和耗时不重复展开，工具不再展开附伤和接触时刻。

## 覆盖与检查边界

读取9份改造目录与6份共享库，共779条源配件记录。按继承、专属、排除和槽位规则展开后，覆盖33把武器、3把工具；含原厂1175个入口，其中943个可选改造入口（共享配件在不同武器上分别计数）。

`copy-audit.json`记录逐把清单；`copy-changes.json`记录1549个显示字段的前后差异。非文案字段逐项相等，包括stats、法杖effects数值对象、ID、品质、适配限制、模型和图标路径。文案规则重复应用不会再次改写。

后台FPSGAMEEditor编译成功：`SourceAssets/WorkbenchCopy20261101/build-editor-20261101-203439.log`。
仅执行本次请求的目录与显示源码核对；未启动编辑器、未运行游戏、未进行视觉或联机验收。

## 作者与重导入口

`SourceAssets/WorkbenchCopy20261101/copy_rules.py`是本轮文案规则。49份相关作者入口已同步或接入序列化时的文案处理，清单见`author-sync.json`。
`apply_for_target(path, catalog)`只处理正式ColdSteelData目录，保留快照和其他资产数据；法杖原有attachment_copy入口继续调用同一规则。

纯文案重新落盘：

```powershell
C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe -X utf8 SourceAssets/WorkbenchCopy20261101/apply_copy.py
```

用户要求核对时可运行同目录`audit_copy.py`；不会启动UE或游戏。

## 逐把清单

| 武器 | ID | 可选改造数（不含原厂） |
| --- | --- | --- |
| M4A1 | `ue_m4a1` | 35 |
| AKM | `ue_akm` | 34 |
| QBZ-191 | `ue_qbz191` | 35 |
| M1911 | `ue_m1911` | 17 |
| Pit Viper 2011 | `ue_pit_viper2011` | 19 |
| G18 | `ue_g18` | 17 |
| Dan-Wesson 715 | `ue_dan_wesson715` | 17 |
| RSH-12 | `ue_rsh12` | 25 |
| ASH-12 | `ue_ash12` | 24 |
| M16A2 | `ue_m16a2` | 35 |
| A762 | `ue_a762` | 34 |
| SVD | `ue_svd` | 31 |
| PKM | `ue_pkm_lowpoly` | 33 |
| 201轻机枪 | `ue_lmg201` | 34 |
| HK416 | `ue_hk416` | 34 |
| M4 Super90 | `ue_super90` | 29 |
| M870 Tactical | `ue_m870` | 23 |
| SVCh | `ue_svch` | 31 |
| Saiga 12K | `ue_saiga12k` | 33 |
| M24 | `ue_m24` | 20 |
| 苍蓝星辉·双手符文剑 | `ue_rune_sword` | 33 |
| 寒晶·双手剑 | `ue_frost_crystal_sword` | 27 |
| 高地·双手剑 | `ue_highland_claymore` | 30 |
| 唐刀 | `ue_tang_dao` | 31 |
| 玄螭镇岳 | `ue_xuanchi_zhenyue` | 30 |
| 斩马刀 | `ue_zhanmadao` | 30 |
| bow_dark | `bow_dark` | 17 |
| bow_woodsteel | `bow_woodsteel` | 21 |
| ue_apprentice_staff | `ue_apprentice_staff` | 20 |
| tool_axe | `tool_axe` | 12 |
| tool_pickaxe | `tool_pickaxe` | 12 |
| tool_shovel | `tool_shovel` | 9 |
| 锻钢战锤 | `ue_steel_warhammer` | 27 |
| 符文战锤 | `ue_runebound_warhammer` | 32 |
| 雷神之锤 | `ue_thunder_god_hammer` | 32 |
| 尼泊尔弯刀 | `ue_kukri` | 20 |
