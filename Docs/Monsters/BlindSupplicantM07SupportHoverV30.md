# M-07 V30：近战脚底支撑与悬浮施法

2026-10-03 用户反馈攻击腿脚浮空，要求微调腿部，同时让施法像无重力一样浮空，结束后 recover 落地。

近战从已经保存的 V27 连续收势版读取完整姿态，保留库内肩肘腕、胸背、头部及背膜旋转。原方案只按两脚中最低的一点整体调整高度，本轮改为逐脚支撑：支撑脚持续接触，前脚短踏 12 cm，前摇／收步时短暂抬脚 4 cm，后脚在出手时有限抬跟并保留趾端支撑。两腿沿同一解剖膝铰链求解，按双脚可达距离下沉骨盆，避免拉直锁死后把脚重新提离地面。出手配合 3.5 cm 承重下沉；上身旋转、2 秒总长、0.60 秒接触和既有伤害窗口继续使用。

施法从 V28 完整缓存读取，重新合并后整体制作，再在同一边界帧拆回蓄力／释放：约 0.18–0.98 秒缓慢升空 40 cm，双膝放松、双脚错位垂下，释放后的 1.62–2.14 秒平缓下降，末尾以约 4.5 cm 屈膝下沉吸收落地，到 2.40 秒回到站姿。蓄力 1.1 秒、释放 1.3 秒、释放后 .30 秒出手保持原值。所有高度烘焙于骨骼动画，不切换角色导航或重力模式；既有掌心发射原点随骨骼升降，火球／冰锥 +65 cm 离身偏移保持。

本轮制作四段 `AnimationsSupportHoverV30/A_M07_SweepLeft`、`SweepRight`、`MagicGather`、`MagicRelease`。显示网格、骨架、蒙皮、V25 移动、V29 八向死亡和原技能数值继续使用。没有新增运行时 IK、地面射线、Tick 或原生改动；无需为本轮动画构建 C++。

## 制作文件

- 可编辑源：`SourceAssets/BlindSupplicantM07Meshy20261001/SupportHoverV30/Motion/M07_SupportHover_V30.blend`。
- 同目录四份动画 FBX、`support_hover_manifest_v30.json`。
- 导出：`Tools/BlindSupplicantM07/author_support_hover_v30.py`。
- 导入：`Tools/BlindSupplicantM07/import_support_hover_v30.py`。
- 保存回执目标：`SourceAssets/BlindSupplicantM07Meshy20261001/SupportHoverV30/ue_support_hover_delivery_v30.json`。

制作源、四份 FBX、四段 UE 动画和原 AI/F6 蓝图引用均已实际保存；回执 `ue_support_hover_delivery_v30.json` 的 `saved=true`。后台导入日志为 `Saved/Logs/M07Import-20261003-185113.log`。本轮仅修改动画，无需 C++ 构建。没有启动游戏、运行测试、截图或渲染；动画效果由用户自行体验，离线支撑制作不代表实际坡面接触已经验收。
