# 力量符文通用接入检查（2026-10-15）

用户明确要求检查双手锤、双手剑是否均已接入。

结果：**32 项目录／源码合同检查通过，58 项引擎资产读取检查通过，无失败项。** 未发现本次符文需要修复的接入缺项；本轮没有修改生产代码、玩家装备、存档或场景。

| 当前武器 | 改造槽 | 共用选项 |
| --- | --- | --- |
| 苍蓝星辉·双手符文剑 | 剑身Ⅱ `blade_2` | `strength_rune` |
| 寒晶·双手剑 | 剑身Ⅱ `blade_2` | `strength_rune` |
| 高地·双手剑 | 剑身Ⅱ `blade_2` | `strength_rune` |
| 唐刀 | 剑身Ⅱ `blade_2` | `strength_rune` |
| 玄螭镇岳 | 剑身Ⅱ `blade_2` | `strength_rune` |
| 锻钢战锤 | 符文 `rune` | `strength_rune` |

同一选项来自 `melee-gunsmith.json` 的 `blade_2` 列，没有武器限制字段；锤类列直接引用它。当前工程登记的双手锤为锻钢战锤。检查覆盖六把武器共 25 个实际符文承载网格版本及其有效材质覆盖。

数值检查追踪了剑／锤目录解析、共同倍率累积、各自玩法评估器与 `ColdSteelWeaponDamage::Evaluate`。`physical_damage_mult: 1.1` 同时乘基础物理和附加物理；魔法通道不乘此项。此部分为源码合同检查，未运行原生伤害评估或攻击结算。

引擎读取确认两张实际 Texture2D 可加载，共享图标使用 UI/EditorIcon/NeverStream 设置；常规叠加材质、东方剑身原生材质与战锤 ShaftWrapV2 均具有对应遮罩、模式及颜色参数，Custom 着色代码确实消费这些参数。红色赋值、切换后颜色恢复与柄部映射由源码检查覆盖，没有启动额外渲染或记录游戏截图。

存档识别沿既有 `gunsmith_parts` → `Installed` → `Normalize` → `ColdSteelFrostRunes::Upgrade` 路径；力量符文属于公共白名单。检查未写入或重载用户存档，不能替代实际保存／退出／重进测试。

磁盘 Editor 二进制时间晚于本次符文源码修改，当前编辑器启动时间亦晚于前轮构建。检查时已有 PIE 在运行，仅通过桥只读加载资产和写本报告，未切换玩家装备、结束 PIE 或更改其世界。

证据：`source_report.json`、`asset_report.json`、`asset-bridge-01.txt`。本结论为通用目录、代码接入及资产可加载性通过；**尚未进行实机挥击、联机伤害或最终画面验收**。
