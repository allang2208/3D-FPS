# 第三人称双手锤左手施法

适用：整条左臂进入胸腔、开掌扭曲、施法恢复跳动。案例为 2026-10-17 DirectionV2；用户已认可该方向修正。

- 第一人称掌姿不能直接变为第三人称肩肘目标。Jason/Kwang 持锤胸腔本身有偏转，固定角色 X/Y 或镜头方向并不等于当前胸前、身体左侧。用原生参考胸腔与当前胸腔构造解剖基底，再定义肩—肘—腕的连续路径。
- 主体继续采样原生持锤动作，右手和锤柄不参与左手施法。左手 Cast 分支跳过通用持械 IK，专用层放在原生动作和其他持械混合之后；法杖 StaffCast 不走此层。
- 肩、上臂、前臂、腕以及影响蒙皮的 helper/twist 链一起处理。先复制有效局部姿态，再转换、回写；不要把未初始化局部姿态写回。仅腕点正确或骨长不变不能证明整臂没有穿胸。
- 用掌宽方向校正前臂滚转，限制两骨链最大伸展。不要整链局部四元数插值穿过胸腔；恢复阶段继续走安全腕肘路径，终点采样当前原生持锤姿态。
- 缓存以动作开始时间、武器实例和阶段区分。新施法或换锤清缓存；远端进度校正时阶段内行程只前进，避免手臂沿路径回抽。
- ReleaseFraction 对普通攻击是固定阈值，对左手 Cast 才是移动掌进度。单独复制 CastPalmProgressRate，仅同一次 Cast 采样并限制外推年龄 0.12 秒；不能套用到攻击命中阈值或 StaffCast。

源码：Source/FPSGAME/Characters/FPSBodyHammerCastPose.inl，FPSPlayerBodyAnimInstance.cpp、FPSPlayerBodyNetwork.cpp；诊断工具 Tools/PlayerBody/*hammer_cast*20261017.py。旧穿胸求解器在 trash/living-armor-retired-20261018 下。

用户授权排查时，以实际原生 AnimInstance 输出检查肩/肘/腕相对胸腔的位置和 helper 链；离线骨长结果不代替蒙皮画面。2026-10-18 新增网络采样修正完成 Editor/Game 构建和 20 项离线权威/副本检查，未做真实双端渲染或弱网验收；默认不启动这些检查。
