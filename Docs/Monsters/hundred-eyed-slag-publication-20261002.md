# 百目炉渣整理、技能沉淀与源码发布

> 2026-10-02 后续修订：死亡仍下陷的反馈已制作 V17，当前源码改用 `RagdollGroundV17/PA_HundredEyedSlag_Ground_V17`。真实根骨绑定和关节默认配置保存的排查、实际资产保存与构建状态见 [V17 记录](hundred-eyed-slag-ragdoll-ground-v17-20261002.md)。下文 V16 是此前发布快照；后续修订未在本轮提交或推送，未进行游戏验收。

2026-10-02。工作与发布根目录为 `D:/FPS3D/FPSGAME`，授权远端为 `https://github.com/allang2208/3D-FPS.git`，分支 `main`。本次按 WORKFLOW 第 4、5、6、8 节整理。

## 当前运行与质量边界

当前使用 ArticulationV12 网格，V8 横扫和 V9 下劈收势，PolishV2 跑动／死亡、ThreeAttacksV13 待机激光片段、EyeChargeV14 蓄能、RagdollGroundV16 PA，以及 V21 身体浓烟和 V19 目盲材质。F6 稳定入口为 `HundredEyedSlag`，角色类 `/Script/FPSGAME.HundredEyedSlagMonster`。

保留横扫、下劈、眼部激光三种攻击。普通横扫倍率 1.25，下劈倍率 1.4、命中眩晕 2 秒；激光倍率 0.8，默认魔攻 35 对应每跳基础 28，0.65 秒内每 0.13 秒首跳在开始，共 5 跳基础合计 140。实际伤害经过当前防御／状态公式。激光原地待机，眼部蓄能至少 1.5 秒，无提前量。

烟从身体三个位置产生，出生位置在世界空间固定，离体后独立上浮。线性扩散／覆盖 ×1.5，默认 Radius 260 → 390 cm；8 秒保留后渐散 1.5 秒，每秒 8 粒，约最多 76 粒。目盲仅在浓烟核心内生效、离开即解除，覆盖早期离开后残留 2 秒的方案。

用户已认可 V8 横扫／下劈攻击主体；后续 V9 收势、V16 死亡和 V21 烟雾修订没有本轮游戏验收记录。V21 两项资产实际保存，Editor 玩法模块常规构建成功，日志 `Saved/BuildEditor/slag-smoke-visibility-v21-20261002-011055.log`。该构建基于共享工作树，包含其他已落盘源码，不宣称为剥离并行改动后的公开提交独立重编译结果。未启动 UE 交互编辑器、游戏、PIE、渲染或性能测试；本次发布检查仅审阅仓库、归档读回、暂存内容、大小、敏感信息和许可边界。

## 可恢复归档

193 份文件共 1,869,443,580 字节（以清单实际合计为准）移到 `trash/hundred-eyed-slag-20261002`：

- 被用户否决的首版参考图。
- 已取消、当前作者链不读取的 ChargeV10 制作包。
- 被 V21 替代的 V18／V20 烟雾修订制作源与本机回执。
- Before／Backup、`.before` 和有当前 `.blend` 对应的自动 `.blend1`。
- 没有产出粒子缓存数据的 commandlet 尝试及失败桥读。

每文件的原路径、目标路径、大小、SHA-256、原因、保留替代物和移动后读回结果见 `SourceAssets/HundredEyedSlagMeshy20260930/Publication20261002/archive-manifest.json`。trash 保留本机，不删除、不公开上传。历史回执中的原路径通过这份清单定位。

有效作者输入保留：AuthoringV1 原始源和骨架定义，PolishV2／RuntimeV3／HeroHandV4／ClawV6／ApeRecoveryV7 的可编辑中间模型，RampageReferenceIntake 的已授权源，V8／V9／V12／V13 当前动作与网格源，V17 噪声、V19 目盲作者及 V21 独立浓烟作者。V7 的旧攻击虽曾被否决，它的模型仍是 V8 输入；不能因为旧日期或局部失败把整个目录判废。

## 公开内容与恢复依赖

公开原创 C++、相关近战停止距离改动与目盲目录项、作者配方、HLSL、紧凑原创参数、文档、归档清单及 SKILL。精确文件清单见同目录 `published-files.json`，当前资产和合同摘要见 `runtime-handoff.json`。共享文件只提交百目炉渣的改动。

以下只留本机：Meshy 模型和 PBR、参考图、Epic Rampage 供体网格／蒙皮／FBX／逐帧关节数据、MayuOrbs／ElectricMagic／Niagara Examples 原始包、Mantaflow 图集和 Blender／UE 二进制、构建 DLL、日志及传输／资产安装回执。没有把“免费取得”当成原文件公开再分发许可。

恢复内容目录后再运行作者；纯 Git checkout 不包含上述输入，也不承诺单靠脚本重建完整游戏。当前浓烟作者为 `SmokeVisibilityFixV21/author_visible_body_smoke.py`；目盲仍使用 `WorldSmokeV19/author_world_smoke.py` 的 `blind_material()` 与 `blind_view.hlsl`，需要保留 V17 噪声。不要重新执行 trash 中的旧烟雾收尾脚本重置当前版本。

## SKILL 沉淀

个人目录和工程镜像同步维护：

- `ue5-monster-workflow/references/hundred-eyed-slag.md`：真实巨臂动作供体、保留已认可主体后修收势、扭转／体积骨配合、根单位布娃娃、近战触发与停止距离、持续攻击时钟及最新目盲合同。
- `ue5-fluid-vfx-workflow/references/body-smoke-and-visibility.md`：出生跟随与离体世界烟迹、独立 Set Parameters 捕获模块、UE 5.8 插值字段、组件局部包围盒、寿命和材质浓度分离，以及 commandlet 空 SimCache 的证据边界。

V21 配置读回和保存结果不升级成用户已认可效果，不将本例 8 秒或 76 粒写成其他烟雾通用标准。
