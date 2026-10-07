# 螳螂-M27：隐身恢复 V1

2026-10-06。用户选择：首次接敌一次，加上受击降至半血一次。沿用正式 `BP_MantisM27`、BindingV2 蒙皮及 ClawV3 挥镰。

## 技能合同

- 每个出生实例有两个独立的一次性触发：首次有效接敌；实际伤害使生命从 50% 以上降至 50% 或以下。
- 隐身期间按实际帧时间恢复 `MaxHealth × 0.05 / 秒`，上限为最大生命。不是免伤，仍可命中、硬直、击倒或击杀。
- 第一次满血接敌也隐身至少 3 秒；此时间是可调的最低持续时间。最低时间结束且生命严格超过 80% 后退出，恢复正常 AI 攻击。
- 首次隐身期间若被打过半血，消耗半血机会并刷新撤离/最低时间，连续保持隐身，不闪回实体。两个机会均不会因回血或脱战重新充能。
- 暂停挥镰并消费当前命中窗口；原有硬直、眩晕、击倒不被技能清除。死亡立即结束恢复并还原实体材质。
- 先向背离目标方向撤离，再以约 7 米为基本半径环绕；隐身移动速度 190 cm/s，步态按原动画源速度同步。目标使用已有感知记忆位置，导航仍使用共享行为树与寻路，避免穿墙和越过出生点牵引范围。
- 目标点计算间隔 0.85 秒；共享导航自身限频。失败时换绕行方向，无额外每帧寻路或扫描全场对象。

## 外观

`/Game/Monsters/MantisM27/CloakV1/Materials/M_M27_JellyCloak`

UE 原生 Substrate 兼容的透明表面：中部不透明度 0.025，Fresnel 轮廓增量 0.16，IOR 1.025，轻微慢速流动法线，0.45 秒淡入/淡出。实体纹理在过渡期间保留，退出后恢复所有原材质槽。无额外场景捕获。

隐身时增加一个只投影的骨骼网格，复用原不透明材质，通过 Leader Pose 跟随现有骨架；隐藏主显示/深度输出，启用隐藏投影。它没有独立动画计算、碰撞或 AI。只在隐身过渡/持续期间投影；正常状态由原网格投影。实际投影仍取决于场景灯光的阴影设置。

## GitHub 调研和来源

- [ektogamat/predator-material](https://github.com/ektogamat/predator-material)：React Three Fiber、WebGPU、TSL 的透明猎杀者效果，适合作为果冻轮廓、流动法线与实体切换的概念参考，不能作为 UE 资产直接导入。
- [DarknessFX/UEMaterials](https://github.com/DarknessFX/UEMaterials)：有 Fresnel Refraction 和 Glass 材质示例；[MIT 许可](https://github.com/DarknessFX/UEMaterials/blob/main/LICENSE)。不是包含此怪物触发、恢复、导航与骨骼投影的完整技能包。

本次自行编写 UE 材质节点与游戏逻辑；没有复制第三方源代码或二进制素材。使用项目中已有的 M27 原始纹理。

## 制作和交付

- 行为实现：`Source/FPSGAME/Monsters/MantisM27Stealth.cpp`，现有 M27 Actor 和共享 AI 的局部分支。
- 材质制作与蓝图接入：`Tools/MantisM27/author_cloak_v1.py`。
- 实际保存回执：`SourceAssets/MantisM27/CloakV1/ue_cloak_receipt.json`。
- 默认只后台制作、必要编译与保存；没有运行游戏、截图、视觉或玩法验收。以回执的 `material_saved`、`blueprint_connected` 区分保存状态；构建结果另记，不能以脚本写好代替接入完成。

### 本次落盘结果

- Game Development 构建已成功（共享构建 `Saved/AzureDragonV10/gameBuild.log` 包含 `MantisM27Stealth.cpp`）；Editor Development 已成功，任务构建日志为 `SourceAssets/MantisM27/CloakV1/build-editor.log`。
- 后台 commandlet 已完成实际 SM6 材质编译和保存，并将材质与技能参数接入、编译和保存原 `BP_MantisM27`。日志为 `SourceAssets/MantisM27/CloakV1/connect_cloak.log`，保存回执两项均为 `true`。
- 没有打开 UE 编辑器界面或启动游戏测试；外观、阴影、寻路和实战表现由用户测试。
