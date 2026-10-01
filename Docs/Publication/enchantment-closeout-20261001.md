# 附魔、剑气与 M1911 消音音源整理发布

本轮只整理本对话的附魔迭代、牛仔反馈与 M1911 消音缓存修复。发布目录为 `D:/FPS3D/FPSGAME`，目标为 `allang2208/3D-FPS` 的 `main`；不包含其他会话的魔法、夹层背包、握把动作或材质改动。已有碎裂、感电及裂空基础运行层已在此前提交中，本次提交当前增量与制作配方。

## 当前内容

| 内容 | 当前制作及玩法合同 | 记录 |
|---|---|---|
| 汇聚 | 蓝色 V2，增强轨迹可见度；真实局部网格尺寸计算 | [汇聚 V2](../Weapons/convergence-tracer-v2-20260929.md) |
| 碎裂子弹 | 史诗后缀，实际发射枪独立捕获；5 m 命中随机／击杀全体，只弹射一代，继承本发防御前伤害；紫晶 V1 | [玩法](../Combat/enchant-shatter-bullet-20260929.md)、[视觉](../Weapons/shatter-bullet-vfx-reference-20260930.md) |
| 感电的 | 史诗近战前缀，25% 命中／100% 近战击杀首跳，闪电击杀继续群体连锁；至少 10 级；真实武器挂接、显式样条绑定，V3 断开电弧 | [感电 V3](../Combat/enchant-electrified-melee-20260930.md) |
| 裂空 | 史诗剑类后缀，蓄满重击 100% 伤害、12 m、穿敌遇墙消散；V4 双尖轮廓、厚中心蓝白能量与柔边，命中声音／提示和刃部空间扰动 | [裂空 V4](../Combat/enchant-rift-slash-20260930.md) |
| 牛仔 | 史诗手枪后缀，滑铲 0.25 秒后仅消耗真实对应备弹；单次机械声、无换弹动画；成功后提示「已自动换弹」 | [牛仔](../Combat/enchant-cowboy-20261001.md) |
| M1911 | 装备与消音器挂载时绑定本枪原消音 cue，避免继承上一把枪的缓存 | [音源修复](../Weapons/m1911-suppressed-audio-binding-20261001.md) |

用户选定碎裂视觉设计；牛仔补入备弹后已由用户确认可触发。感电完整圆箍、裂空月牙及暗色空间裂口是被否决的历史方案；当前 V3／V4 是已制作版本，不写作已获视觉验收。M1911 修复保留 `/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed` 的历史共用音色，没有替换音频文件。

## 归档与保留

两份退役文件移入本机 `trash/enchantment-closeout-20261001/Tools/Skills/`，详情见 [精确清单](enchantment-closeout-20261001-manifest.json)。移动前核对授权根与源散列，移动后回读散列；trash 不入库。旧感电单项执行入口由 `apply_electrified_v3.py` 替代；一次性 Live Coding 请求退出作者链。

保留所有活动 UE 资产、可编辑源、生成 OBJ、制作脚本与导入／构建回执。`OrbitV2` 路径保存的是当前 V3，不能因目录名归档。裂空旧主体已经原位重制，不存在需要另移的旧网格副本。备弹排查中的玩家存档及库存报告留在本机 Saved，不公开发布。

## 来源与恢复顺序

1. 使用本机 UE 5.8.2 与既有 Niagara 工具接口，恢复原枪械、剑类、斧镐模型和声音。M1911 共用消音声、左轮开弹巢／手枪插弹匣声、剑类 `hit_sound` 都沿用原项目授权来源；本次不再分发音频或第三方模型。
2. 汇聚先恢复 `/Game/Weapons/GunplayFX/M_BallisticTracerVisibleV13`，再运行 `Tools/AssetPipeline/build_convergence_v2.py`；原创表达式在 `SourceAssets/ConvergenceVFX20260929/ConvergenceBeamV2.hlsl`。工程配置保存蓝色与 0.75 余迹强度。
3. 碎裂运行 `Tools/AssetPipeline/build_shatter_violet_v1.py`，从原创 `ShatterVioletV1.hlsl` 与程序几何重建 `/Game/Weapons/ShatterVFX20260930`。
4. 感电先恢复 `/Game/Skills/Lightning/NS_LightningChain` 与原依赖，再运行 `build_electrified_orbit.py` 和 `build_electrified_melee.py`；后者依赖原生 `RainAssetEditor::BindSplineUserObject`。工具挂点数据已有 `Content/ColdSteelData/electrified-tool-anchors.json`，仅更换对应斧镐模型时用 `build_electrified_tool_anchors.py` 重建。已开编辑器的短批次辅助入口为 `apply_electrified_v3.py`，后台优先直接运行作者脚本。
5. 裂空使用 `Tools/Skills/build_rift_slash.py` 与两份原创 HLSL，依赖同目录已有 `build_fireball_assets.py` 的通用 Niagara API 帮手和引擎自带 SimpleSpriteBurst 模板。全量 `build()` 保存六项专属资产；`build(projectile_only=True)` 只更新剑气主体。源与许可说明见 [裂空作者源](../../SourceAssets/RiftSlash20260930/README.md)。Fab Sword Slash VFX 仅曾用于题材参考，没有下载或复制其资产。

这些脚本在 Unreal Python 环境中执行。没有编辑器占用目标包时可用后台 commandlet；已经打开时沿用现有互斥资产桥，不启动第二个交互编辑器。脚本、原创 HLSL 与少量定位参数入库，生成 OBJ、`.uasset`、模型、贴图、WAV、引擎模板、插件二进制与回执保持本机。公共源码不等于可直接运行的完整内容包。

## SKILL 与交付边界

整理时将碎裂材质重建脚本的节点清理改为列表快照逐个删除，沿用感电 V3 已记录的修正，避免再次制作时残留时域响应输出。本轮只修复作者配方，没有重新执行资产制作或改写已保存材质。

有用经验整理到 [附魔数据与战斗接入](../../skills/ue5-weapon-workflow/references/enchantment-scrolls.md)、[枪械表现](../../skills/ue5-weapon-workflow/references/gunplay-vfx.md) 与 [枪械音源](../../skills/ue5-weapon-workflow/references/weapon-audio.md)，同步个人技能；[发布规则](../../skills/ue5-weapon-workflow/references/publication.md) 补充纯新增 hunk 的行号偏移问题与暂存内容复核方法。历史外观条目标明退出范围，玩法、实例归属、武器绑定及单灯预算保留。

各案例文档保存此前的资产落盘与必要 Editor／Game 构建记录。最近牛仔提示构建为 `20261001-154503`；M1911 常规 Editor／Game 构建记录为 `20261001-160142`，结果成功且 UBT 判定目标已最新。这些记录来自当时完整本机工作区，不代表本次精确暂存的公共源码子集重新构建或运行通过。

本轮按推送规则检查精确暂存内容、差异格式、JSON／Python 语法、大小、敏感信息、来源与新增链接；只进行普通非强制推送并回读远端 SHA。本轮不重新编译，不启动 UE、PIE、游戏、试听、截图或验收；实际功能与观感由用户测试。
