# 201 通用改造件接入 — Accessories22

**后续替代（Magazine24）**：用户已取消 201 弹药箱。当前只启用原装 30 发弹匣，普通／空仓换弹及四组握把版本改由 `../Magazine24/` 制作、保存和接入。以下弹箱及 56 条动作数量是首次制作历史，不代表当前启用清单；本目录旧脚本不再重写换弹资产。

2026-09-28，按配件标准与认可的 VRE 成组抓握工作流制作。仅后台导入、保存与必要编译；未运行游戏或进行动作验收。

## 本轮交付

- 当前启用 14 个 201 专用适配静态网格：五款前握把、四款枪托、三款后握把、激光、手电。
- 用户限定 PSO-1 仅供俄式枪械：已从 201 目录与运行装配支持中剔除，制作/重导脚本也不再接入。旧存档的该选项由现有目录归一化移除，恢复原厂瞄具。首次导入的 PSO 资源和回执仅作为历史制作记录保留。
- 五款前握把使用四组动作：垂直与战术垂直共用 vertical；canted、prism、angled 保持独立。
- 每组 14 条动作，共 56 条已保存 AnimSequence。包括普通/空仓弹匣换弹与普通/空仓弹箱换弹。
- 供弹仍为现有原厂弹匣、弹药箱；原有瞄具、枪口和脚架选项保留。没有新增弹鼓或扩容弹匣。
- 首次导入保存私有干湿材质 68 个、34 对雨天映射（含后来退出 201 目录的 PSO 历史材质）；以当前 201 Material21 枪钢为基准，保留来源的聚合物、橡胶、光学区域、UV0 法线与 AO。
- 原厂枪托、原厂后握把及对应分类图，共四张 201 专属灰阶图标；其余相同造型使用已登记的共享图标。

## 左手制作依据

`sources.json` 记录实际安装资源、哈希与骨架；没有按旧 FBX 的日期选母版。

手型来自当前 PKM Accessories14 四组 idle 的原生 FK 整臂链，手指、腕、肘、肩和 twist/helpers 一并迁移；保留 201 本地骨长与缩放。握把与整臂使用同一刚性安装变换，没有重新求解 IK，没有单独扭转手腕或重写 twist。

`author_animations.py` 复制当前 201 的动作，只覆盖左臂抓握/脱手/回握区间。右臂、枪根、弹箱、弹链、机匣盖、音效事件和动作长度继承当前 201 来源。弹箱换弹中段保留 PKMFK19；普通弹匣按既有脱手/回握区间适配。冲刺进入时脱手，循环保留原收手，退出回握。

`LMG201_<family>_Editable.blend` 保存四组原生 V7 抓握编辑场景；`Keys/` 保存全部 56 条动作的本地轨道，UE AnimSequence 为完整动作编辑资产。十五件配件各自保存可编辑 Blend 和 FBX。

## 安装与运行引用

- `/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_<part>`
- `/Game/Weapons/LMG201/Accessories22/Animations/<family>/A_LMG201_<family>_<clip>`
- `/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials`
- `Source/FPSGAME/Weapons/LMG201Attachments.h`
- `Content/ColdSteelData/gunsmith.json` 中 `ue_lmg201` 条目

前握把位于护木下沿、弹箱前方，保留原厂脚架。枪托和后握把使用实际原厂接口，安装时隐藏对应 FactoryStock/FactoryRearGrip 槽位。激光与手电保留实际 Emitter 插座及原有功能。201 瞄具位于固定后导轨，挂接 WPN_root；先前挂到 LMG201_Cover 的处理错误，已在 FixedRail23 中纠正。开盖时只运动前部机匣盖，瞄具随固定后机匣运动，不能套用 PKM 的活动盖挂点。

## 制作与落盘

1. `collect.py`：读取当时实际来源并导出静态件。
2. `read_geometry.py` / `author_geometry.py`：读取接口、适配几何，保留来源 UV。
3. `author_animations.py` / `save_editable.py`：生成 FK 轨道与编辑场景。
4. `install.py`：保存网格、材质、雨天映射与动画；`install_receipt.json` 为本次实际回执。
5. `author_icons.py` / `install_icons.py`：生成并接入四张原厂图标；`icon_receipt.json` 记录共享图标依据。

`integrate.py` 是本轮一次性源码/目录补丁记录，不作为资产重导入口；不要在已经接入的源码上重复执行。共享文件原始片段在 `Before/`，它们不是可整体回滚并行工作的版本。

游戏内手臂观感、配件组合与接触效果由用户测试；本记录不宣称通过游戏验收。

首次接入的后台常规构建已完成：`Tools/Build/Build-Editor.ps1` 返回成功，生成正式 `UnrealEditor-FPSGAME.dll`。构建日志：`Saved/BuildEditor/build-20260928-210754.log`。该日志早于后续 PSO 剔除，不代表这次剔除已编译。

PSO 剔除：目录、源码与后续重导入口已落盘。用户关闭 UE 后，后台常规构建成功，正式模块已更新；日志为 `Saved/BuildEditor/build-20260928-214057.log`。没有主动关闭或启动编辑器，没有进行游戏测试。
