# M4 双手抬枪奔跑 — 2026-09-09

参考：修改前实机 `Saved/GunplayUpgrade/m4-finger-final60/Frames/Frame_0123.png`；现有 Idle 双手握持骨骼姿态。原奔跑只有整体压低与未按摄像机轴组合的旋转。

实现位于 `Source/FPSGAME/FPSGAMECharacter.h/.cpp` 的 M4 Sprint 属性和 `UpdateViewmodel`。这是可编辑的运行时程序动画，继续使用 RigV4 和现有 Idle；未生成或替换 FBX 动作。动画归角色实例持有，仅影响本地第一人称显示，不新增网络状态或更改移动速度、射击解锁时间。

- 在摄像机空间叠加抬枪旋转：俯仰 35°、偏航 -12°、滚转 -8°。
- 双手、武器和附件整体运动，维持左手与护木的接触。
- 奔跑位移偏置 `(6, 3, -9)` 厘米；左右摆动 ±1.8 厘米，上下起伏 ±0.45 厘米。
- 满速时每秒 1.65 个左右周期，按实际速度调节；停下、换弹、瞄准等状态平滑退出。进入速率 12/s，退出 24/s。
- 普通行走摆动随奔跑权重减弱，避免两种步频叠加。保留现有腰射取景、ADS 校准、自然弯曲食指换弹和 AKM 路径。

`run_validation.ps1 -Fps 60 -Label <唯一名称> -SprintPreview -CaptureFrames -D3D12` 使用独立测试存档及真实 UE 渲染。`SprintPoseAudit` 在既有验收空闲区间增加约 3 秒奔跑、退出瞄准、30 Hz 截帧和逐帧骨骼采样。固定模拟更新频率不是实测帧率。

`make_preview.py <Saved/GunplayUpgrade/测试名称> --video` 导出动画、前后对照和采样校验；不改动源截图。先检查最终 result.json 与 sprint_validation.json，再验收视频。备份在 `trash/M4Sprint-before-20260909`，包含当时的源文件；并行开发时应只撤回本次相关改动，勿整体覆盖。

## 最终验证

- 编译：`build-76.log` 成功，重新编译所有角色头文件依赖，排除并行修改期间混用旧布局的中间产物。
- D3D12 完整枪械回归：`m4-sprint-final30-offscreen`、`m4-sprint-final60`、`m4-sprint-final144`，每组 46 项通过，进程正常退出。
- 三组共 785 个奔跑区间采样，稳态枪口仰角约 33.90–36.02°，左右总行程约 3.60 cm，上下总行程约 0.90 cm；左手相对枪身漂移为 0。
- `Saved/GunplayUpgrade/m4-sprint-final60/Preview/sprint_preview.mp4`：真实游戏渲染的起跑、连续奔跑、收枪瞄准，30 Hz 截帧；同目录含 GIF、前后对照图和步态检查图。
- 早期 v1–v4 的完整回归不作为交付证据；重编译修复旧字段布局后，首次 30 Hz 运行仍被桌面输入打断一次。最终使用独立渲染运行重新通过，不修改正式输入或存档逻辑。
- 当前已打开的编辑器可能仍持有旧模块；保存工作后重新启动编辑器可加载编译结果。未关闭用户编辑器。
