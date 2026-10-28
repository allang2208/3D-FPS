# 疾律弓弦

用户于2026-10-28确认设计并授权接入，另要求中心叠层效果使用山峰印记原来的位置。

## 文件

- `Cadence_String.blend`、`author_model.py`、`Export/SK_Highland_CadenceString.fbx`：真实三挂点骨骼弓弦，深蓝/石墨纤维、银丝、五组柔性节律缠线，模型顶点色R记录缠线层数阈值。
- `Cadence_Icon_Input.blend/png`、`author_icon_input.py`：同一模型在独立图标作者场景中的灰阶素材；只为正式改造图标制作而渲染，不是游戏验收图。
- `bow_woodsteel_string_highland_cadence.png`：实际弓绳素材与项目统一金属框经内置imagegen工具制作的改造图标，提示词见`icon-prompt.txt`。
- `T_Cadence_HUD.png`：内置imagegen制作的五段细纹透明图，原始2172×724；提示词见`hud-prompt.txt`，运行时材质按五等分显示。
- `import_assets.py`、`import_hud.py`、`import_background.ps1`：模型/PBR/LOD/图标与UI材质实际导入保存，完成状态分别看`import-receipt.json`、`hud-import-receipt.json`及commandlet返回。
- `apply_catalog.py`：只合并疾律选项和律动状态条目到现有目录，保留并行修改。完成后写`catalog-receipt.json`。
- `build.ps1`：共享批次互斥下构建Game/Editor，保留已运行的编辑器。实际构建回执为`build-FPSGAME.json`与`build-FPSGAMEEditor.json`。

## 数值与接入

`highland_cadence`仅用于`bow_woodsteel`的`string`槽，归入传说级改造。被动节拍判定窗口+100%（0.20→0.40秒）；每次节拍成功放箭叠1层、每层+20%、最多5层（满层+100%）、6秒刷新；满层腰射扩散−50%、物理伤害+20%。不增加魔法伤害，不改变搭箭时钟和原有节拍的下一次拉弓速度+25%。

`UBowCadenceComponent`按服务器时钟维护并复制整组实例/层数/到期状态；普通放箭与服务端放箭都在成功保存资源和建立本箭快照后提交节拍。临时状态不落入存档。

准星下方与山鸣互斥共位，五段逐步点亮、满层白金呼吸和触发脉冲；状态栏有独立单图标、层数及6秒计时环。前后人称弓绳共用层数驱动缠线材质。

## 交付边界

默认后台制作、编译和资产保存。没有启动游戏、PIE、实机画面验收或自动测试；构建和导入回执不代表运行效果已验收，由用户自行测试。
# 当前 HUD 与数值（2026-10-28 V4）

准星下恢复 `M_Cadence_HUD` 横向五段细纹与满层白金辉光；`ColdSteelCadenceBadge` 编织弦环图案仅用于 Buff 栏。每层拉弓速度+20%，满5层+100%，原常驻拉弓速度+20%已替换为节拍判定窗口+100%（0.20→0.40秒）。满层且未过期时，成功射出任意手动箭都算节拍成功，刷新6秒并获得原下一箭节拍加速，无需满弓或命中目标；仍满足原最低50%拉弓和资源条件。未满层失拍、超时、换武器、拆弦或死亡时清空。当前记录见 `../CadenceTuningV4_20261028/` 及 `Docs/UI/cadence-rhythm-v4-tuning-20261028.md`。
