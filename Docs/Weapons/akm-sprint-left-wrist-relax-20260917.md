# AKM 战术冲刺左手收回：腕关节扭曲修复（V2 改自然下垂）

日期：2026-09-17。范围：仅 AKM 的单手竖枪战术冲刺（`RifleTacticalSprint20260915`）中左手松开—收回—回握的左手腕与手指；AKM 各握把 idle、枪体、机械与右手全部不动；M4 与 QBZ191 的动作数据不修改。

> **V4（2026-09-17 第三次反馈：二代共振握把，当前生效）**：V3 弧线路径只按 Base 验证；穿孔贴身握（Angled/共振二代起始肘弯 74.7°、Canted 59.6°）在可见窗口内 `withdrawn=smooth(.16,.82)` 几乎未启动，折叠全程可见。V4 在 hang 分支把收回调度提前加速为 `smooth(.10,.60)`：Angled 可见段弯度 71→62→49°（进度 0.15–0.25）并于 0.30 出画，Canted 同步受益，Base/Vertical/Prism 峰值 ≤43.8°、0.20 出画。起始折角即各穿孔握姿 idle 本身（已接受），不可再降。
> **V3（2026-09-17 第二次反馈）**：V2 末态虽为直臂垂手，但收回中段手沿直线斜切回身侧，肘弯反升到 86°、可达比跌到 0.74，读作折臂。V3 把手路径改为肩心圆弧+前半程先延展（方向球面插值、半径二次缓出、0.3 单位向外偏置避开枪身）：中段肘弯峰值 46°、可达比 ≥0.934，手在进度 0.30 即出画；末态与 V2 相同。
> **V1→V2（2026-09-17 第一次反馈）**：V1 的腕部松弛解决了关节反转，但收回末态仍是折臂垂手，用户判定不达标，V2 把收回目标改为肩下自然下垂点。V1/V2 参数与过程保留在下文作记录。

## 现象与诊断

用户反馈 AKM 战术奔跑左手收回时手臂关节扭曲，参考 191 与 M4 的自然收回。用 `diagnose_left_arm.py`（复用 `author_sprint.py` 同一套数学 + `DanWesson71520260913/author_weapon.py` 的 `hand_at` 整臂解算）逐进度度量腕/肘关节相对 rest 的局部偏差，并用 FP 相机与整臂旁观相机渲染确认：

- 收回末端（Enter 进度 1.0 / Loop）AKM 左腕关节偏差被推到约 172–179°（Base 177°），扭转分量约 170°——腕关节整体反转，手背折向前臂，指呈爪形；前臂在 Enter 约 0.5 s 处竖直扫过画面下缘（`ReviewCurrent/AKM-Base-enter-06/10.png`）。
- 同一路径下 QBZ191 只有约 122–133°，且以弯为主，读作自然下垂（用户已接受）。
- 根源：共用脚本对所有枪施加同一个世界坐标腕部再定向 `turn(-20, 8, -16) @ idle腕`。AKM 各握把 idle 的左腕本身已极端——Base 是苏式掌心朝上托木，腕部偏差约 107°（191 仅约 17°）；带着这个已卷死的掌面走完约 30 cm 的收回路径，解算前臂换弯折平面后腕关节局部旋转被推过 180°。

各握把修复前峰值：Base 177°、Angled 123°、Vertical 172°、Canted 179°、Prism 172°。

## V1 修复方式（`left_wrist_relax`，已被 V2 替换）

`author_sprint.py` 新增按枪配置分支（`sources.json` 只给 AKM 配置；无配置的枪走原逻辑，数值逐位不变，QBZ191 复算回执与修改前完全一致）：

- 松开/收回时不再保持 idle 的世界朝向，而是把**腕关节局部旋转**从"idle 握姿局部"球面插值到"rest 自然局部"：`amount = 0.55×released + 0.40×withdrawn`（满收回时 0.95）。
- 手的世界朝向改由**解算后的前臂**推导：先用原位置做一次 `hand_at` 求出前臂朝向，再按 `前臂 @ 腕局部` 重建手腕矩阵做第二次 `hand_at`。位置两次相同，故肩肘解不变，仅重新定手向——这与 191/M4 已接受"手随前臂自然下垂"的构成等价。
- 手指松弛比例对 AKM 提到 0.68（其余枪保持 0.52）。位置轨迹、节奏（Enter 0.30 s / Loop 0.60 s / Exit 0.30 s 反向）、18 帧连续进度与可逆性全部保持。

修复后峰值即 idle 本身（收回只从握姿偏差单调放松到近自然位）：Base 107°、Angled 60°、Vertical 30°、Canted 26°、Prism 31°；均值降到 6–23°；扭转峰值 ≤63°（Base）。渲染确认爪形手与竖直前臂消失，整臂末态与 QBZ191 已接受姿势同构（`ReviewFixed/`）。

逐握把复核（2026-09-17，仅针对本修复）：五个握把各自的 idle 在 Enter 第 0 帧逐位保持（诊断脚本 progress 0 偏差等于各自 idle 偏差，Angled 渲染帧确认斜握把接触不变）；`ReviewFixed/` 内 Base/Angled/Vertical/Canted/Prism 五个 `*-retracted-arm.png` 整臂末态均为自然下垂手，Angled 第 6 帧、Vertical 第 10 帧、Canted 第 6 帧 FP 抽查无爪形、无竖直前臂。弹鼓分支沿用原厂（Base）握姿，随 Base 一并覆盖。

## V2/V3：自然下垂（当前生效为 V3 弧线路径）

- V3 路径（2026-09-17 第二次反馈后）：手路径由直线 lerp 改为肩心弧线（`author_sprint.py` hang 分支内 `t=withdrawn` 极坐标段），消除中段折臂。
- V2 依据实测骨架（左肩约 `(-0.23, -0.07, -0.13)`，臂长 0.5502 m）把收回目标从旧的胸前收袋 `(-0.26, -0.10, -0.36)`（可达比 0.44，深折臂）改为**肩下自然下垂点**：`left_wrist_hang = {reach: 0.98, side_offset: [-0.055, +0.03], swing: [-0.006, -0.050]}`——肩点外移 5.5 cm、前移 3 cm、沿臂长 98% 下垂，肘弯仅约 23°（近伸直软弯）；98% 而非 100% 是为避开解算器 98.5% 伸直钳制，避免触发肩部搬运（实测搬运 0.00 cm、无肘翻转）。
- Loop 摆动只保留前后 5 cm 的正弦项（首尾帧为零，Enter/Loop 接缝无跳变），运行时仍随脚步相位采样。
- 腕部仍用 V1 的局部松弛（末态腕偏差 5–8°），手与前臂同向自然下垂；手指 0.68 松弛不变。
- 五握把诊断：Loop 稳态骨点 0 入镜；Enter 中骨点在进度 0.25–0.50（约 4.5–9/18 帧）间自然出画；肘弯峰值 23°、腕偏差峰值即各握把 idle 本身。
- 渲染目检（`ReviewFixed/`）：五握把 `*-retracted-arm.png` 均为上臂—前臂近直线+放松垂手；Base FP 第 6/10/14 帧、Vertical 第 6 帧无竖直前臂、无爪形手。
- 重制并仅重导 AKM 15 段（`import_sprint.py` 改用 `RIFLE_SPRINT_ONLY` 环境变量过滤，191 不再被误重导；回执 `partial: AKM`，30 段齐全）。导入脚本逐段加载+保存断言通过，日志 `LogExit: Exiting.`、零 Python 错误；commandlet 包装层退出码 1 与 9-15 记录的收尾噪声同类，与 2026-09-15 资产导入时 AssetManager ensure 的处理一致，未作为"无错误通过"声明。

## V1（已替换）：腕部局部松弛

- 修改：`SourceAssets/RifleTacticalSprint20260915/author_sprint.py`（relax 分支 + `finger_relax`）、`sources.json`（仅 AKM 两个键）、`import_sprint.py`（合并式回执 + 可选武器过滤参数）。
- 新增工具：同目录 `diagnose_left_arm.py`（关节偏差度量）、`render_retract_review.py`（FP 序列帧）、`render_arm_pose.py`（旁观整臂帧）。
- 重制并导入：AKM 5 握把 × Enter/Loop/Exit 共 15 段，`/Game/Weapons/RifleTacticalSprint20260915/AKM/<握把>/`，120 Hz，压缩设置仍为 `BC_AKM_GripPrecision`；回执 `import.json`（30 段，含 191 原条目）。导入命令退出码 0，脚本内逐段加载+保存断言通过。
- 说明：本次 `-run=pythonscript` 未转发 `-- AKM` 过滤参数，191 的 15 段也按其原有 FBX 重导了一遍（同源等价重导，未改任何 191 数据源）。
- 渲染证据：`SourceAssets/RifleTacticalSprint20260915/ReviewCurrent/`（修复前）与 `ReviewFixed/`（修复后）。

## 文件与交付（V2 当前状态）

- 修改：`SourceAssets/RifleTacticalSprint20260915/author_sprint.py`（`left_wrist_relax` + `left_wrist_hang` + `finger_relax` 分支）、`sources.json`（仅 AKM 三键）、`import_sprint.py`（合并式回执 + `RIFLE_SPRINT_ONLY` 过滤）。
- 新增工具：同目录 `diagnose_left_arm.py`（关节偏差/肘弯/入镜度量）、`render_retract_review.py`（FP 序列帧）、`render_arm_pose.py`（旁观整臂帧）。
- 运行资产：`/Game/Weapons/RifleTacticalSprint20260915/AKM/<握把>/`（15 段，120 Hz，`BC_AKM_GripPrecision`），路径未变，游戏端自动生效。
- 渲染证据：`ReviewCurrent/`（修复前）、`ReviewFixed/`（V2 现状）。
- 未运行游戏、未做实机回归；按全局规则由用户实测。测点建议：W+Shift 进入/松开退出、半途反向、五握把与弹鼓（弹鼓沿用原厂握姿分支）、ADS/开火退出。
