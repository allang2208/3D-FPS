# 魔法书收尾与源码发布

本轮按用户要求完成整条魔法书的检查、废案整理、技能沉淀和 Git 发布。当前实现取代 10 月 10 日暂停状态；历史未认可的 V18/V19 与 V11 收书不再是开发入口。

## 当前功能

- Photo V3 侧握与低位移动保留；V30 开书／正常回收各 1.12 秒，手指错峰、肩肘支撑与回握接触共用非匀速源时钟。
- 被动魔攻为 `round(2 + 0.4L + (0.2 + 0.08L) × (智力 + 精神))`，系数约为学徒法杖的 40%，最高 +15；仅当前有效副手计入。强化、旧实例定义更新、角色总魔攻、单件浮窗／详情同源。
- 法杖配书右键专注；完全展开后施法速度 ×2、魔耗 ×0.75。进入即移动 ×0.67；专注和收书恢复期间不能快速近战。主动关闭无扣魔。
- 有效受击打断专注，扣最大魔法值 25%，低魔法值扣至零。快速翻页、合拢、垂直落下、左手接住后接正常恢复；V3 拇指避让与书页先让位保留。未脱手时从当前姿态回收。
- 七张双面活动页加两面固定内页，共 16 面；四组同风格插图，单页 UV 已旋转 180°。施法翻页 ×2，保持连续相位。
- 持书快速近战使用空手拳击的总长约 0.551667 秒／接触约 0.171667 秒，第一人称、第三人称、诊断、可编辑动作和屏幕反馈统一。
- 客机专注由服务器保存瞬时状态、校验装备、受击打断及结算；累计扣除记录协调回执和档案合并。修复服务器影子档案禁止写盘时误拒绝施法内存提交的问题。未新增旁观者独立悬浮书页复制。

## 恢复与制作

本地源根为 `SourceAssets/SpellbookEvildeer20261009/`，先恢复合法原始书、V7 手臂及下列密集数据和二进制，再执行配方。公开 Git 不包含这些完整资源。

1. 基础书与封皮：`author_spellbook.py`、`import_spellbook_ue.py`；原包、纹理、`Spellbook_Alchemy.blend` 与 `Export/` 保留。闭合书与材质仍供运行使用。
2. 持书／推击：`GripPhotoV3`、其 V2 握点输入、`QuickMelee/author_strike.py` 与 `save_editable.py`；后者读取公开小参数 `playback-clock.json`。完整 grip／strike JSON、当前 Blend 留本机。
3. 开合手臂：`Focus/IntegratedV30/author_motion.py` → `save_editable.py`，参数 `motion-settings.json`；依赖 `PalmUpOpeningV24/candidate.json`、对应 Blend、V23 输入和 `VideoRecovery20261010/landing-baseline-v9.json`，以及 V7 原生骨骼。三个根作者入口均转到 V30。
4. 书页：`PagesV1/author_pages.py`、`import_pages.py`，恢复生成插图及当前导出。重复修正方向用 `OrientationV2/rotate_uvs.py` → `import_mesh.py`，保留 `OrientationV2/Before/Spellbook_16Pages.blend` 作为未旋转母版；不能把已经修正的 Blend 再旋转一遍。当前 Runtime 只加载 PagesV1 的 mesh/open/flip。V30 可编辑手臂场景保留原书作为接触参考，运行页数以 PagesV1 为准。
5. 金光材料仍由 `Focus/GoldOrbit/install_material.py` 和 `gold_orbit.hlsl` 制作。

`Stats20261012/apply_stats.py` 与 `Tooltip20261012/apply_tooltip.py` 是历史精确替换脚本，供追溯，不应对已完成接入的源码再次执行；当前真源是 `Source/` 与 `items.json`。

## 归档与公开边界

627 份旧候选、过渡备份、已完成编辑器命令、预览帧中间产物及无引用的旧回握表，共 1,005,058,714 字节，已移至本机 `trash/spellbook-final-20261012/`。移动前检查源／目标在授权工程范围内，移动后逐文件 SHA-256 相同；[完整元数据](archive-manifest.json) 不包含原文件内容。活动 V2／V9／V23／V24 和未旋转页面母版保留，不能按日期或 Before 名称删除。

公开原创运行代码、姿态参数表、作者配方、小型制作参数、技能参考与恢复说明。原始模型／PBR、完整作者采样、图像、Blend/FBX/uasset、引擎与插件二进制、日志、凭证和 trash 内容不上传。原书来源与 CC BY 4.0 署名见[来源记录](../../../SourceAssets/SpellbookEvildeer20261009/ATTRIBUTION.md)。本次没有新增原始资产公开分发。

## 检查与交付边界

已逐项阅读装备／动作占用、单件及总魔攻、强化、八类法术专注应用、旧存档、联机回执与合并、浮窗布局和当前资源引用。详细证据见[检查记录](checks.md)及[离线结果](checks.json)。19 份作者脚本语法、物品 JSON、源时钟 10,001 点单调性、当前软资产和活动输入、归档散列、技能同步及暂存空白／敏感信息检查完成；原扣魔合并 C++ 函数在最小类型适配环境下通过 9 项断言。

本机 `FPSGAMEEditor`／`FPSGAME` Development 构建均返回 Succeeded／Target is up to date；此前 NetFocus 修复的两目标实际编译成功。独立临时工作树只包含本次候选提交，并补齐本机插件及 Blast 库；构建在 UHT 阶段被已发布基线缺失的 `MonsterArcPathing.h`／`FMonsterArcPathingTuning` 阻断（`NurseZombie.h:20`）。该引用已存在于基线 `0f7d4897`，缺失文件仍属另一条怪物开发线，未夹带发布。因此本次不宣称公共快照可独立全量编译；这不改变本机已完成构建的事实。

没有启动编辑器、PIE、联机游戏、截图或渲染。代码／离线检查、资产已保存和编译成功不替代运行、视觉或打包验收。共享工作区中的其他武器、货币、UI、怪物及场景增量保持原位，发布使用独立临时索引逐块提取，不整文件夹夹带这些功能。
