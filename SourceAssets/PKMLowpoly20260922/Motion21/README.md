# PKM Motion21 — 出链口盖板与提把惯性

日期：2026-09-23。当前修改范围仅为出链口盖板的独立铰链及提把摆动。保持弹量、射击/换弹时钟、手臂动画、几何外形和 Finish20 材质。

## 出链口盖板

原件 `PKM_Part_058`（盖板）和 `PKM_Part_101`（中央铰链套）原先整件跟随 `PKM_Cover`，没有独立开度。二者刚性绑定到新增叶骨 `PKM_ExitCover`，父骨仍为 `PKM_Cover`；外侧固定铰链件 102 保持原绑定，因而打开上盖时整组仍随上盖走。

铰心取中央铰链套的实际几何中心。当前板长约 2.54 cm，横向半宽约 3.29 cm；具体数据记录在 `authoring.json`，并由作者脚本生成 `Source/FPSGAME/Weapons/PKMOutletCoverGeometry.h`。

运行层 `FPKMExitCoverDynamics` 在已有出链姿态之后执行：采样当前引导片、空链节的几何包络，计算盖板不得侵入的最低开度，另叠加重力、移动惯性和带阻尼回弹。接触开度即时约束，不让弹簧延迟把板片带入弹链。弹链移出接触区域后回落，打开上盖时使用上盖的当前坐标系继续计算。

弹链是否参与接触直接读取实际 `__OldBelt` / `__NewBelt` 显示状态，包含末发进给延迟、普通换弹、空仓换弹和新弹链出现阶段。隐藏骨的零缩放同时排除。重复求值不重复积累时间。

这是一套游戏表现用的受限铰链与弹链包络约束，不是整枪 Chaos 刚体仿真，也不宣称完成所有姿态的精确三角面碰撞验收。

## 木制提把

沿用 CarryHandle18 的真实挂点、木柄和金属支架权重。回弹频率从 3.8 Hz 降至 2.15 Hz，阻尼比从 .62 降至 .30；摆幅由 -9°/+7.5° 改为 -15°/+18°。增加靠近限位的渐进缓冲和轻微回弹，保留线性/角加速度驱动，允许奔跑、换弹与急停后产生余振。没有添加持续循环的随机抖动。

## 文件与接入

- 来源：`../OutgoingBelt19/PKM_OutgoingBelt_Editable.blend`。
- 新可编辑源：`PKM_HingedOutlet_Editable.blend`。
- 导出：`Exports/SK_PKM_Manny_Modular.fbx`。
- 作者入口：`author_hinge.py`，输入几何记录 `source_hinges.json`。
- 导入入口：`import_asset.py`，捕获当前材质绑定后重导入同一活动网格，恢复材质槽；不导入动画或新材质，不更新已有骨骼参考姿态。
- 游戏目标：`/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular` 及其 PKM 私有骨架。
- Finish20 的划痕、干湿材质和独立雨滴表保留。

制作、导出与后台导入已完成。首次编辑器桥请求未发现可连接节点，没有执行导入；用户保存关闭编辑器后，Python commandlet 已将活动网格与私有骨架保存。导入记录为 `imported.json`，后台导入日志为 `import_background_01.log`，退出码 0。导入捕获并保留了当前 Finish20 材质绑定。

动态逻辑的常规 Editor 目标构建已成功，退出码 0；记录为 `build_cpp.log`，完整构建日志为 `Saved/BuildEditor/build-20260923-092938.log`。盖板和提把逻辑已进入常规构建产物，没有启动或重启编辑器。

未运行游戏、测试或验收渲染，实际摆动幅度与换弹接触由用户测试。
