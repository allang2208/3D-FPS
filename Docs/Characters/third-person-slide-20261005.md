# 第三人称 FootOut 滑铲接入

## 来源与资产

- 使用本机 `D:/FPS3D/游戏动画示例/Content/Characters/UEFN_Mannequin/Animations/Slide` 的 Epic Game Animation Sample 动画。UE 专用来源；原始和派生二进制留在本机。
- 选择 `M_Relaxed_Slide_FootOut` 的 11 个片段：左右脚进入、左右脚冲刺进入、循环，以及站立、静止下蹲、移动下蹲、步行、跑步、冲刺退出。
- 复用已保存的 GASP → Jason 对齐重定向器，只新增 `Content/Characters/JasonPlayer20261003/SlideGASP20261005/Animations` 中的派生动画。
- 源动作的进入录制长约 7.4 秒、循环 12.5 秒、退出长约 2.8–7.5 秒。根据制作时读取的骨盆／腿部轨迹添加 `SlideBegin`、`SlideEnd` 标记，排除助跑和收尾的冗余片段；完整录制保留可编辑。
- 11 个 `Slide.*` 路径合并到 `Content/ColdSteelData/player_body.json`，身体初始化时沿现有动画库加载。

## 播放与骨骼责任

- `FPSBodySlideLayer.inl` 接管骨盆及其下肢分支，包含腿部辅助骨、脚踝和脚趾。保留原动作的屈膝平面和关节旋转。
- 开始时按脚步相位选择左右脚、按实际速度选择普通／冲刺进入，进入段用 0.42 秒完成，再进入持续循环。下坡超过最大滑铲时长仍持续循环。
- 正常结束按当前下蹲／站立、移动速度和冲刺意图选择退出片段，退出段长 0.3–0.65 秒；结束前过渡回当前行走／蹲姿。跳跃、闪避、翻越或死亡中断直接释放滑铲层。
- 片段切换从上一帧实际下肢姿态混合 0.12 秒。滑铲层淡入 0.1 秒，中断淡出约 0.08 秒。
- 第一根脊柱补偿骨盆旋转，上身保留现有装备姿态；手部仍由原持握适配负责。不改变骨长和头部缩放。
- 已接入滑铲资产时，禁用旧固定脚位／固定膝盖极向的程序滑铲；进入和退出期间禁用站立脚锁、脚掌压平和重复下蹲压低。
- 使用移动组件已有的地面法线，对整组下肢做最高 18 度的平滑坡面适配，不新增地面射线。滑动方向相对身体最多偏转 65 度。
- 根骨锁定参考姿态；角色位移、碰撞、滑铲持续时间、跳跃条件、武器攻击和命中时钟继续由原玩法系统负责。

## 制作入口

按顺序运行 `Tools/PlayerBody/` 下的 `prepare_slide_sources.py`、`retarget_slide_jason.py`、`read_slide_sources.py`、`author_slide_ranges.py`、`publish_slide_jason.py`。其中重定向、读取轨迹和写播放标记使用 UE 后台 Python commandlet；源包复制不覆盖现有不同内容。

`SourceAssets/ThirdPersonSlide20261005/` 保留源文件散列、保存路径、原始时长、制作轨迹和播放区间。标记写入派生动画，运行时只在片段切换时读取，不解析制作 JSON。

## 交付边界

11 个派生动画、播放区间及运行配置已保存。Game 构建 `Result: Succeeded`（当前产物已是最新）；同一工程已完成的共享 Editor 构建包含 `FPSBodyGrounding.cpp` 与 `FPSPlayerBodyAnimInstance.cpp`，结果为 `Succeeded`，DLL 在本批源码最后修改后于 2026-10-05 23:55 落盘。日志保存在 `SourceAssets/ThirdPersonSlide20261005/build-game.log`、`build-editor-shared.log`。

本任务未主动打开或重启图形编辑器，未启动游戏、PIE、截图或运行测试。腿部观感、持剑组合和上下坡效果由用户体验。后台制作过程中工程还报告了不属于本批的 M14 吐液音频缺失；滑铲脚本正常结束并保存全部 11 个资产。
