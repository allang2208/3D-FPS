# 锁子甲袖口局部摆动：复用巫婆 Chaos 衣物流程

> 2026-09-29 整理：本页为历史制作记录。旧产物与停用入口已归入 `trash/gloves-chainmail-20260929`；共享建模辅助函数及仍被最终版使用的源保留。恢复清单见 `Docs/Publication/gloves-chainmail-retired-manifest-20260929.json`。

> 此第一人称方案已因用户反馈内衬穿插与卡顿而退役。替换流程见 [内外层同步运动](chainmail-shared-sway-20260929.md)。以下保存原制作记录，不再作为当前接入标准。

## 需求与复用边界

锁子甲沿用原武器手臂动作，在袖口及相邻前臂表面增加小幅滞后和回摆。
用户要求参考已有巫婆衣物摆动；本次直接复用实际项目代码，不制作新动画。

可复用部分：

- `WitchRebuiltAuthoring.cpp` 的低密度代理提取、MaxDistance 固定区、原骨架碰撞体、Chaos 参数写入和 LOD0 绑定。
- `UWitchRebuiltClothingAsset::BindToSkeletalMesh` 的持久映射修复。每次重新绑定/DDC 构建都通过相同的插值法线反解和越界退回蒙皮逻辑，避免只修改一次中间映射数据。
- 巫婆的模拟暂停、恢复后重置、短时间混合进入的生命周期思路。

不能直接套用巫婆的身体坐标、袍摆代理、厘米级大行程、腰部/地面约束和远距离阈值。第一人称袖口使用自己的曲面与权重、毫米级行程及可见性调度。

## 制作与资产

- 基线：`SourceAssets/ChainmailInterlace20260929`，保留其显示几何、锁环 PBR 和各武器原生骨架权重。
- 新来源：`SourceAssets/ChainmailCloth20260929`。
- 新 UE 包：`/Game/Characters/ModularOutfit20260924/ChainmailCloth20260929/`。
- 主代理根据 M4 已有袖子外表面取样；每袖 32 个圆周样本 × 10 排，共 320 顶点。双臂 640 顶点/1152 三角形，单臂 320 顶点/576 三角形。
- 前 3 排固定，后 7 排逐步放开。活动区接近袖口，最外缘比上方松弛区域更收紧；最大位移 0.28 cm。
- 代理经原生 bind 矩阵迁移到现有 21 个第一人称显示配置。Body 继续使用原 V2 静态蒙皮资产。
- `M4_CuffSimulationProxy.blend` 保存可编辑代理，`Proxy/*.json` 保存各原生骨架位置、权重和颜色行程掩码。
- 不对每个锁环创建物理体。模拟只运行低密度代理，显示模型通过 cloth 映射跟随。

UE 一个 clothing asset 的同一个模拟 LOD 不能重复绑定多个显示 section。因此原锁环面与实体袖口环合并为一个 section，UV1.x 标记原材质区域：0 为锁环 PBR，1 为实心金属。暗色内衬/包边作为独立固定 section，继续普通骨骼蒙皮。

## 初始参数

这些值是制作初值，未进行游戏内调参或性能测量。

| 参数 | 值 |
|---|---:|
| 最大行程 | 2.8 mm |
| Edge / Area stiffness | 1 / 1 |
| Bending stiffness | 0.16 |
| Anim drive stiffness / damping | 0.12 / 0.30 |
| 全局 / 局部阻尼 | 0.12 / 0.35 |
| 碰撞厚度 | 1.5 mm |
| 碰撞代理 | 每臂 1 个前臂胶囊 |
| 自碰撞 / CCD | 关闭 |
| 迭代 / 最大迭代 / 子步 | 4 / 6 / 1 |
| 显示混合进入 | 0.2 s |

行程和身体胶囊限制运动范围，但不等于已经证明所有武器与手套组合完全无穿插；具体效果留给用户游戏内测试。

## 运行时接入

`FFPSOutfitSecondaryMotion` 由模块化服装 presentation 持有。继续使用原 Leader Pose 获取手臂骨骼，同时启用服装组件自己的 tick 和独立衣物模拟；不将服装模拟绑定到裸手 leader 的模拟器。

- 活跃、可见的第一人称手臂：服装 tick 开启，强制 LOD0，恢复模拟并重置。
- 隐藏/预加载/OwnerNoSee 或强度设为 0：混合归零，暂停 cloth，关闭服装 tick，恢复自动 LOD。
- 显隐切换、较大时间步、手部位置/旋转跳变：重置 cloth，重新渐入。
- 换装备时销毁该 presentation 的服装组件和运动状态。
- `fps.Outfit.ChainmailSway`：默认 1；范围 0–1 为模拟混合强度；0 暂停模拟。
- 只在锁子甲 recipe 的 `secondary_motion = chainmail_cloth_v1` 时启用。

## 生产入口与交付状态

1. Blender 后台运行 `Tools/ModularOutfit/build_chainmail_cloth.py` 生成原生代理。
2. `Tools/Build/Build-Editor.ps1` 普通 Editor 模块构建，禁止在已打开项目编辑器时覆盖 DLL。
3. 使用现有互斥批次运行 `Tools/ModularOutfit/import_chainmail_cloth.py`。构建材质、显示/代理网格、3 个显示 LOD、绑定 cloth，并实际保存 UE 包。
4. `Tools/ModularOutfit/publish_chainmail_cloth.py` 读取完整保存回执后更新锁子甲 recipe。只更换第一人称网格及运动标记；不改数值、装备图标和世界身体。

实际保存回执见 `SourceAssets/ChainmailCloth20260929/Saved/*.json`；正式发布状态以 `published.json` 为准。代理和脚本的存在本身不代表已完成 UE 导入。

本次已完成代理制作、普通 Editor DLL 构建、21 个第一人称配置的 UE 网格/材质/cloth 保存，以及装备 recipe 更新。构建日志：`Saved/BuildEditor/build-20260929-110514.log`。资产保存使用了当时已打开编辑器的现有互斥 Python 桥；本会话未打开或重启编辑器。重新进入游戏读取新 recipe 后生效。

遵循用户规则，不启动游戏、PIE、预览渲染或额外验收；构建/制作日志属于必要生产输出。游戏内表现、不同装备组合和帧耗由用户测试。
