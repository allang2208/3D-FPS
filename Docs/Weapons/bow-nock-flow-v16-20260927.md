# 快速搭箭与无后摇输入锁 V16

用户要求：参考视频的快速手部衔接，消除箭直接在弦上出现的观感；射出后可以立即衔接下一次拉弓。

## 动作与箭的交接

参考 BV1jGdDBkEkc 的 37.6–37.8 s、44.4–44.7 s 画面：可见手部快速回到弓前并接弦拉开，未完整展示从箭袋抽箭。浏览器细分截图保存在 `Saved/BowReferenceNocking20260927`；本轮据此制作三维适配，未运行游戏验收。

- `QuickNock`：0.20 s，左手抬弓，右手从右下方带箭进入，末端对齐弦与箭台。
- `ChainNock`：0.20 s，用于 Release/Recover 中再次按下左键。弓保持抬起，右手退出、画外补箭、带入并接弦，无须先回到待机。
- `Nock`：保留 R 键原有约 0.68 s 和改造倍率，加入带箭方向标记；箭随手运动，靠近接触时才对齐箭台。
- 两个快速动作都包含在原 0.20 s 入场预算内，不额外增加搭箭等待。箭在约 34% 入场进度时随右手显示，在约 90% 时接弦；入场完成前不增加拉距、不扣箭。
- 手持箭的尾点与方向取自 `bow_nock`，朝向先随携带姿势移动，再平滑交接给箭台—箭尾轴线。手型、原生骨长、握把与 V15 拉弓动作保留。
- 已经搭好箭时沿用原来的到弦入场，不再凭空再取一支。入场中松手取消，仍不发射、不扣箭。

## 后摇与连续输入

`BeginPrimaryAttack` 在 Release 和 Recover 阶段都立即接受下一次左键，直接进入新的 DrawEntry，不排队、不等待阶段结束。新动作从当前显示姿态做 50 ms 的交接，交接包含在入场时长内。

Release/Recover 的原 0.30 + 0.34 s 仅用于不继续射击时的自然收势；不再作为下一次射击的输入锁。伤害、箭速、耐力、拉满时长、腰射散布和 ADS 数值均保留。左键仍须真实松开发射，不变成按住自动连射。

上一次释放的弓弦、弓臂余振和镜头退力用独立的短表现时钟衰减，接入下一次动作时不会硬清零；新搭箭不会继承满拉力。切武器、施法等高优先级取消仍清除反馈。

## 文件与状态

- 作者源：`SourceAssets/BowNockFlow20260927/Bow_QuickNockV16.blend`、`author_actions.py`、`generated_actions.py` 与三份 FBX。
- UE 动画：`/Game/Weapons/DarkBow20260925/NockFlowV16/A_Bow_Nock`、`A_Bow_QuickNock`、`A_Bow_ChainNock`；复用现有 ContactV9/V7 手臂骨架，不替换身体或四款弹性弓体。
- 三个新路径用 `bow_nock_animation`、`bow_draw_entry_animation`、`bow_chain_entry_animation` 接入原异步加载；旧的自定义弓无覆盖路径时保留原动作回退。
- `bows.json` 表现版本升到 27，由现有库存迁移读取；打包目录加入 NockFlowV16。V15 动画与资产保留。
- 指定文件修改前备份在 `Saved/BowNockFlow20260927/Before`，导入记录在作者目录 `import-receipt.json`。

三段动画已后台导入并保存。`FPSGAMEEditor Win64 Development` 构建返回 `Result: Succeeded`（当前目标已为最新），日志：`Saved/BowNockFlow20260927/build-editor-v16.log`。已执行目录安装脚本，表现版本 27、三个覆盖路径与 cook 目录已落盘；安装回执：`SourceAssets/BowNockFlow20260927/install-receipt.json`。

未启动游戏、未运行测试、未渲染验收图。用户体验时，射出后再次按住左键应立即进入 0.20 s 补箭入场，无须等待原 0.64 s 收势；补箭期间松手仍取消，不发射未搭好的箭。
