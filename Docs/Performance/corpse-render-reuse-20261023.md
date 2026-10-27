# 冻结尸体与重复身体渲染更新（④）

本轮按现有源码修复重复提交，保持画质、怪物数量、战斗规则、尸体物理预算、冻结时机与自动 LOD 策略不变。⑤毛发优化未开展。没有启动 UE、游戏、commandlet 或测试，没有新增运行采样，不能据此给出 FPS 提升比例。

## 路径与处理

| 路径 | 原有行为与本次处理 |
| --- | --- |
| 通用人形、螳螂及其他已有呼吸网格的冻结尸体 | 已经停止动画、移动与物理 Tick，保留这一行为。原阴影缓存逻辑提取为 `UMonsterCorpseMeshComponent` 基类，不引入新的动作或受击表现。 |
| M09、M10、M14、M66 普通骨骼尸体 | 原组件不继承已有的冻结阴影缓存实现；改为使用上述纯渲染策略基类。现有死亡流程通过 `RetireCorpseTicks` 启用缓存，共享 LOD 定时器在必要刷新后重新启用。 |
| 共享软体尸体显示组件 | 使用 `UMonsterCorpsePoseableMeshComponent`，只在原求解器确认静止或原预算冻结入口生效后启用阴影缓存。LOD 切换仍刷新完整骨骼，随后缓存新轮廓。 |
| 软体姿势未变化 | 未执行固定物理子步时不重写显示姿势；执行了子步但最终骨骼变换完全相同时，也不调用 `RefreshBoneTransforms`。比较容差为零，不按位移阈值吞掉小动作。复用两份骨骼数组，避免每帧额外分配。 |
| M66 客户端尸体 | 原有网格自动 Tick 与同步组件手动求值重叠；改为由同步组件单独求值。每个网络样本的原有 0.1 秒插值到达终点后停止重复提交，下个 `OnRep_Packet` 恢复插值。服务器发布、音效与物理逻辑不变。 |
| 第一人称 `FirstPersonSharedBody` | 该组件全部材质区段原本就隐藏，仅承担装备配方与挂接锚点；换为不创建 RenderState 的专用锚点组件。真实皮肤、裤子、鞋和服装仍直接跟随世界身体的骨骼。保留世界身体的阴影/反射及第三人称用途。 |

## 渲染语义

本机 UE 5.8 源码中，`UPoseableMeshComponent::RefreshBoneTransforms` 会更新骨骼版本、子组件、包围盒并标记动态渲染数据；这会把原本相同的姿势再次送入蒙皮及动态光追几何路径。本次在明确持有姿势的提交入口去重，不修改引擎、不降低渲染频率、不跳过活体动画。

隐藏所有材质区段不等于不创建骨骼渲染对象。专用 `UFPSBodyPoseAnchorComponent::ShouldCreateRenderState` 返回 false，去掉纯锚点的 GPU 渲染资源；保留它的网格资产、挂接关系、可见性状态和 LeaderPose 信息，供现有换装逻辑使用。

冻结阴影使用 `Rigid` 策略，仍允许灯光、组件变换和可见性等正常失效。仅处理不透明且不使用 WPO、Displacement、PixelDepthOffset、Overlay、活动布料或 Mesh Deformer 的组件；具有这些动态表现的材质继续原策略。新姿势和 LOD 刷新会使旧阴影失效，材质重建代理时再次判断是否适用。

## 构建与交付边界

构建入口和逐目标回执保存在 `Saved/CorpseRenderReuse20261023/`：`build.ps1`、`build-FPSGAME-receipt.json`、`build-FPSGAMEEditor-receipt.json`。最终结果以回执中的退出码与 `completion.json` 为准。构建仅生成 Game / Editor 二进制，不启动它们。

2026-10-23 后台构建完成：`FPSGAME Win64 Development` 与 `FPSGAMEEditor Win64 Development` 最终退出码均为 0，包含最后补充的 M66 LOD 刷新与尸体组件接入。

本轮没有变更材质资产、纹理质量、光追开关、阴影分辨率、网格精度、怪物数量或攻击/命中规则。实际画面、联机插值与帧率效果尚未测试，由用户运行确认。
