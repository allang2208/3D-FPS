# M870 快速近战：SUPER90 R9 参考版 R1

## 2026-10-17 归档状态

本目录旧输出及安装入口已移至 `trash/m870-retired-20261017/SourceAssets/M870QuickMeleeSuper9020261017/`；仅 `author_motion.py` 仍为 R3 读取的工具前缀，保留原位。当前制作和保存入口为 `../M870QuickMeleeElbowR3_20261017/`。下文为历史过程，不再作为当前资产安装步骤。


> 用户已否决 R1：快速近战中右臂扭曲，上臂开口进入画面。修订制作位于 `../M870QuickMeleeR2_20261017/`；下面的完成记录仅表示 R1 当时已保存，不表示视觉认可。

用户要求以 SUPER90 为参考重新调整 M870 快速近战，重点处理右手。

制作来源是当前安装的 SUPER90 快速近战及其原厂、vertical、canted、prism、angled 握姿。沿用竖直收臂、右手向前送枪托的节奏与 R9 前臂扭转分配方法。M870 的手掌和手指以本枪各握姿当前 idle 为依据，保持枪根空间的接触，重新解算肩、肘、前臂支撑。

旧的 `M870TriggerGrip20261016/author_trigger_grip.py` 在持枪阶段对 `clavicle_r` 下整条右臂应用 `gun_delta @ template`，近战时右肩至右手一同刚性随枪移动。新稿将肩肘运动与固定掌部接触分别处理：肩肘参考 SUPER90，腕端锁定 M870，辅助骨仅承接沿前臂轴的旋前，不把完整腕弯传给整段前臂。

## 范围

- 替换当前入口 `/Game/Weapons/M870/Tactical20261015/Animations/A_M870_quick_melee`。
- 同步更新四个 `DA_M870_*` 前握把 Profile 的 quick_melee 条目，保留其他动作条目。
- 保留 0.9 秒时长与 1/6 秒命中时点，不修改伤害、冷却或联网协议。
- 起止使用 M870 当前 idle；相机空间沿用已保存的 SUPER90 对齐待机偏移。
- 沿用 `Super90MeleeArmAuthored` 曲线，配合已有通用左臂支撑节点及动作收势权重。
- 不修改骨架、网格、手指握姿、ADS、装填或冲刺资产。

## 文件

- `read_inputs.py`：读取实际安装的 SOURCE 动画、原生绑定与 Profile，保存到 `inputs.json.gz`。
- `author_motion.py`：制作基础动作及四个稀疏握姿差量，输出 `animation_patch.json`。
- `save_editable.py`：保存包含五条可编辑时间线的 `M870_QuickMelee_Super90_R1.blend`，不渲染。
- `A_M870_QuickMelee_Super90_R1.fbx`：新版原厂动作导出源；资产的导入来源同步指向该文件。动作重制仍须通过本目录更新对应 Profile，不能只重导入 FBX 而保留旧差量。
- `save_assets.py`：备份并保存一条动画与四个 Profile；仅更新 quick_melee 条目。
- `run_asset.ps1`：沿共享批次互斥，在已有编辑器或后台 commandlet 中完成实际读取、保存。
- `save_receipt.json`：实际保存结果；只有 `completed=true` 才表示五份资产均已落盘。

本轮不启动游戏、不渲染预览、不追加动画自测或联机测试。制作、保存与用户视觉认可分别记录；未将源计算当作自然度、无穿模或运行验收。

## 交付状态

后台制作和保存已完成。`save_receipt.json` 记录基础动画与四份 Profile 均已保存；新版可编辑 `.blend` 和原厂 `.fbx` 已导出，原资产保存在 `Before/Content/`。本轮没有 C++ 变更，不需要原生代码重编译。未启动编辑器界面或游戏，实际动作观感仍由用户测试。
