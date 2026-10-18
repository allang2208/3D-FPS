# 大羊排 V8 原生拇指关节修正

完整原因与范围见 `Docs/Survival/large-lamb-v8-native-thumb-20261017.md`。

当前大羊排双手实际使用的 Traversal 裸臂已是 V8 表面，磁盘散列与 V8 保存回执一致；V7 路径未更名。此次修正的是持续握持时的拇指中节、末节侧折。运行代码支持相对原生局部关节的三组四元数，只给大羊排左右拇指启用，收拢与松开也沿同一组关节旋转。

制作与诊断：`diagnose.py` → `author_thumb.py` → `publish.py` → `review_saved.py`。`before_motion.json` 和 `Before` 是本轮原始记录，不应覆盖；后续迭代另建目录。`pose_model.py` 对应当前 `PotionArmPose`，包括上轮 preserve_native_roll 与本轮 local_rotations。

`candidate_motion.json` 保留本轮完整姿态；正式图 `final_present*.png`、`final_bite*.png` 从保存后的运行 JSON 求值，Blend 保留离线场景。`thumb_fit.json`、`saved_pose_review.json` 记录真实混合蒙皮接触与 13 阶段离轴量；其余四指、双掌、食物轨迹、6 秒时长和 4.65 秒接触点保持原样。进入前和释放后的碰撞数值是对不可见食物代理的度量，不当作可见穿模。

Editor 与 Game 两个目标已构建成功，回执 `20261017-002704/result.json`，本轮产物清单 `delivery.json`。没有重导手模或其他 UE 资产，没有启动 UE 界面、游戏或 PIE。离线复查不能代替用户的游戏内视觉确认。
