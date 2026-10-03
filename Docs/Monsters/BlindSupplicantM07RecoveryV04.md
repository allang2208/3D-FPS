# M-07 V04 全身破碎修复

**后续用户反馈：V04 仍然破碎，未修好。** 本文的“完整身体”称呼有误：护士人体材质缺少裙装覆盖的骨盆与大腿。当前修复见 `BlindSupplicantM07RecoveryV05.md`，V04 仅保留为失败输入和追溯记录。

用户指出 V03 在待机、走动、攻击、受击和死亡中都整体错位，要求先回退再重新调整。V03 不作为合格模型；V02 也曾被指出重复手和关节问题，回退只用于撤下此次损坏动作，不代表旧版已达标。

## 制作根因

`Tools/BlindSupplicantM07/author_motion_v03.py` 连续写各骨骼的世界姿态，最后才刷新依赖图。子骨转局部姿态时使用尚未更新的父骨姿态，烘焙出了本不应存在的关节平移。原 V03 待机源中头骨偏离参考位置约一米，手部局部轨道偏移最高约 2.83 米，错误已存在于 Blender 动作和 FBX。

Rig-only FBX 还将动作首帧当作默认骨骼变换，而显示网格从 REST 导出。旧骨架存在历史根缩放 100 与当前重新读取根缩放 1 的差异；当前网格、旧骨架的骨骼局部位置仍为米制数值，不能以过去的导入回执推断当前单位一致。

## 修正交付

- 先将现有 BP 的 V03 显示模型与十二个动作引用撤回到保留的旧输入，保存回退回执；随后以独立 V04 资产替换同一个 AI/F6 入口。
- `author_motion_v04.py` 使用 `Bone.convert_local_to_pose`，显式传入目标父骨矩阵，将完整世界目标转换为 `matrix_basis`；保持原骨段长度与父子局部参考位置。
- 每个动作保留真实参考帧 0；在帧 0 导出 FBX 默认骨骼变换，动画范围仍为 1..N，参考帧不进入运行片段。
- 模型顶点、骨骼参考位置/长度及动作局部位移一起转换为厘米，Blender 场景 `scale_length=0.01`，对象与根骨缩放为 1。V04 显示网格创建独立 `SK_M07_ReferenceV04`，代理与全部动作共享它。
- 保留单一完整身体、成熟人体关节/五指权重，以及原 Meshy 感知头、颈环、腕箍和监测装具。未恢复旧的 Meshy 身体与供体补体叠层，避免重复手重新进入显示资产。
- 六片显示鳃膜与隐藏的连续模拟代理继续分开；布料重新按 V04 骨架绑定，身体碰撞保存为独立 `PA_M07_V04`，不覆盖历史版本的身体碰撞。
- 待机、慢走、追击、左右攻击、受击、死亡、贴墙聆听、眩晕、倒地及两种起身动作全部替换到 `/AnimationsV04`；共享战斗时钟、AI 和 F6 注册入口沿用原合同。

## 文件与资产

本地制作目录：`SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryV04`。

- `M07_Anatomy_Master_V04.blend`：厘米参考的静态模型源。
- `M07_Motion_Centimeter_V04.blend`：同一厘米参考的十二动作源。
- `M07_AnatomyAndMotion_V04.blend`：组合可编辑母版。
- `SK_M07_Display_V04.fbx`、`SK_M07_ClothBuildSource_V04.fbx`、十二个 `A_M07_*.fbx`。
- `rollback_v03_receipt.json`：用户要求的回退保存记录。
- `ue_anatomy_delivery_v04.json`：实际导入与保存回执。

UE 目标：`/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV04`、`SK_M07_ReferenceV04`、`PA_M07_V04`、`AnimationsV04`，入口仍为 `BP_BlindSupplicantM07`。

后台编译、导入与保存属于本次制作。未启动游戏、PIE、布料试跑、预览渲染或验收；最终外观、动作和战斗表现由用户测试，未获得用户认可前不标记为合格。
