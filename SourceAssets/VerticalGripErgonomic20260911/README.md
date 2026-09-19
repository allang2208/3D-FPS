# 垂直握把类：参考实拍抓握的左臂与手指修订

本轮依据用户 2026-09-11 的实拍抓握参考，调整 M4 垂直握把与棱镜阻手器。运行引用位于 `Source/FPSGAME/Weapons/VerticalGripAnimationFamily.h`，两款分别加载 `/Game/Weapons/M4VerticalGripErgonomic/Vertical` 与 `/Prism`。

## 这次调整

- 先查看原 `M4_idle` 和 `M4_reload` 第 146 帧、两款当前持握源的实际渲染。待机 60 FPS、0–180 帧、3 秒循环；改动保持九组动作原时长、左右手职责及换弹业务时序。
- 按原待机的肘关节弯曲平面重建上臂和前臂方向，再分配前臂旋转。旧算法逐骨最短弧对齐，不能保证两段手臂仍在原本的肘部弯曲平面内。新算法保留原手模、蒙皮、rest、骨长和缩放。
- 垂直握把先调整整掌方向，再约束四指在各自的屈伸平面内弯曲，用有限掌骨内收缩小间隙；PIP/DIP 联动，拇指贴靠食指外侧。棱镜保留其较宽、较短截面的接触适配，下方两指自然收拢。
- 新手型有专用松指与退握路径。拇指先让开、四指松开后侧退；回握反向执行。普通/空仓、普通弹匣/弹鼓的取弹、装填、压实与拍击主段不改动。

## 可编辑入口

- `vertical/M4_Vertical_Family_Editable.blend`、`prism/M4_Prism_Family_Editable.blend`：汇总九组新动作；相邻同名前缀 FBX 为引擎导出。
- `arm_profile.json`：共用肩部位置、肘部方向提示及前臂 twist 分配。数值只适用于这个 M4 视模。
- 各成员 `fit_final.json`：手掌相对枪根、手指局部矩阵与握把安装矩阵；`release_profile.json`：已烘焙松指曲线；`release_parameters.json`：作者阶段的退握参数。
- `fit_pose.py` 的 `solve_arm` 与 `build_family.py` 是当前生成逻辑。各成员 `build_animation.py` 调用共用生成器；从当前参数重新烘焙不需要重跑拟合、恢复初始姿势或覆盖用户的 Control Rig。
- 原 `/Game/Weapons/M4ArmsIKEditor/LS_M4_Vertical_Idle_IK_Edit` 及其手工编辑保持原样。旧 Raised/Horizontal 动画资源仍可作对照。

## 验证与范围

具体计数、散列和压缩读回见 `acceptance.json`。两成员共 18 个动画的源时长、骨长、缩放、手指局部平移、右手、枪根、弹匣与保留装填区间均检查；每款 446 个真实变形网格采样验证手部与配件接触。另检查全部十组指对及松手/回握。

原空仓拍击动作中各有 15 个检查采样含既有指间接触，本轮保留源动作主体；`preserved_source_self_contacts.json` 对照确认这些时刻原源也有接触，未把它们报告成全身或整段动画零穿模。待机和新退握手型的指间接触单独检查。

导入 commandlet 的既有 GameFeatureData 配置报错导致退出码 1；导入报告、另一个新进程的 18 动画 RAW/COMPRESSED 读回和真实游戏检查分别验证，不能将退出码描述为整体无错误。未做打包构建；未改声音，视频为实际游戏截图序列，只作视觉证据。

`compare_arm.jpg` / `compare_palm.jpg` 是同视角前后图。两成员 `M4_*_Ergonomic_Gameplay.mp4` 为本次游戏预览。当前结果是本轮已接入修订，最终审美取舍仍以用户后续反馈为准。

作者源继续依赖工程内现有 M4/Manny 基线及本机 Blender 5.1。商用原始模型和动画二进制未在本轮对外发布。
