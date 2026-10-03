# M-07 V32：以待机腿姿校准近战支撑

2026-10-03。用户反馈 V30 攻击双脚已经贴地，但小腿关节组合仍不正常，要求参考待机，避免腿部扭曲。

## 本次修改

当前实际待机为 `AnimationsPalmArmV20/A_M07_Idle`。读取其源骨架后，左右膝弯曲平面均与旧攻击解算使用的全局前向极向量相反；V30 调用 V17 的绑定姿态膝轴，不会重现当前待机腿部关系。V30 还保留库内较大的骨盆平移，而双脚只有短距离踏步，造成额外伸腿与旋转需求。

V32 从已保存 V30 的两段攻击制作，保留肩肘腕、胸背和骨盆旋转，以及各脚踝／爪部目标轨迹。腿部改为：

- 以实际待机的髋、膝、踝位置和骨骼旋转建立左右独立参考；参考屈膝角约 54.33°／59.08°，保留该角色自己的弯曲方向。
- 将待机整条腿的弯曲平面随髋踝连线整体运输，小腿仅增加同一膝轴上的屈伸，不再独立重建小腿滚转，也不按全局正轴翻转膝面。
- 保留固定骨长，按真实父子偏移重建大腿、小腿和踝部 FK。
- 相对待机的骨盆水平位移缩至原 30%、垂直位移缩至原 20%；保留源运动时序、转体和上身挥击，以小幅重心移动匹配固定脚底。
- 离线保留屈膝余量并连续调整支撑高度；首尾使用同一待机腿部参考，恢复段不再回到相反的膝面。

制作、调整及采样均在 Blender 离线烘焙；不新增运行时 IK、Tick 或布料预算。原模型、蒙皮和 V31 背膜均未改动。V25 移动、V30 悬浮施法、V29 方向死亡继续使用。

## 已落盘

两段 2.00 秒、60 fps 攻击已导入并实际保存：

- `/Game/Monsters/BlindSupplicantM07/AnimationsIdleLegSupportV32/A_M07_SweepLeft`
- `/Game/Monsters/BlindSupplicantM07/AnimationsIdleLegSupportV32/A_M07_SweepRight`

原 `BP_BlindSupplicantM07` 的 `MeleeLeftClip`、`MeleeRightClip` 和 `AttackClip` 已保存指向新版。接触时间仍为 0.60 秒，窗口 0.20 秒，播放倍率 1；距离和伤害设置未改动。

可编辑源：`SourceAssets/BlindSupplicantM07Meshy20261001/IdleLegSupportV32/Motion/M07_IdleLegSupport_V32.blend`，同目录含两份 FBX 和 `idle_leg_support_manifest_v32.json`。

保存回执：`SourceAssets/BlindSupplicantM07Meshy20261001/IdleLegSupportV32/ue_idle_leg_support_delivery_v32.json`，`saved: true`，记录两段动画和原蓝图三份资产。

生产日志：`Saved/Logs/M07-Author-IdleLegSupportV32.log`、`Saved/Logs/M07Import-20261003-194049.log`。工具为 `Tools/BlindSupplicantM07/author_idle_leg_support_v32.py` 和 `import_idle_leg_support_v32.py`。

本轮未启动编辑器、游戏、预览或渲染，未进行自动测试。保存成功不代表视觉验收通过；由用户通过 F6 重新生成后体验。
