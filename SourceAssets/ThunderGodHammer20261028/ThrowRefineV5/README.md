# 雷神之锤投掷动画 V5：用户要求自查后的修正

本轮检查蓄力换握、前挥、松手和随挥。后台重新生成 FBX、导入并保存了现用的两条动画；没有修改 C++、公共手模、召回/接锤动作、伤害或雷击逻辑。

## 发现与修正

- V4 右手分指松开太晚。投射物在出手动画 0.24 秒离手，而该时刻食指、中指尚未展开，形成锤柄穿过握拳的观感。V5 将右手分指起始提前到 0.166–0.195 秒，每段展开 0.038 秒、指节延迟 0.002 秒，最后一节在 0.237 秒完成既定张开姿态。保留各指轻微弯曲，不拉直成僵硬手板。
- 当前实际 V9 手模与旧作者手模形状存在差异，换握和左手撤离空间偏小。V5 在蓄力换握中加入外侧绕行，右手最高额外外移 7.5 cm、左手 6.5 cm；出手时增大左手向左、向后和向下的撤离量，降低双手交叠。

## 已保存的运行资产

- `/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1/A_ThunderHammer_ThrowCharge`
- `/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1/A_ThunderHammer_ThrowRelease`

`import_receipt.json` 记录保存结果及修改前备份。继续编辑入口为 `author_motion.py` 和 `ThunderHammer_ThrowRefineV5_Editable.blend`。

## 本次检查范围

使用当前保存的 `SK_Warhammer_BareArmsSprintV1` V9 网格、真实骨权重与动画数据模型逐帧读回，在 `../ThrowReviewV4/` 保存结果和正面/侧面关键帧。该检查目录沿用原名，`native-poses.json`、`native-frames/` 为 V5，带 `before` 的数据为 V4。

检查内容包括：运行资产版本、骨架一致性、全段武器轨迹不变、原生骨长不变、实际 2 秒满蓄力至出手零帧衔接、0.24 秒离手前的右手张指。离线表面检查覆盖 12 个正面/侧面关键帧。

未启动 UE 图形编辑器或游戏。离线蒙皮图没有执行运行时 117 个 JC 动态修正形态，也没有复现游戏相机、材质和全部动作叠加；它们用于检查姿态与手掌空间，不代表实机视觉验收。
