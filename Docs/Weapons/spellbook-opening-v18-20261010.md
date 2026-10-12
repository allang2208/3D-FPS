# 魔法书 V18：专注入场与关节衔接

本版曾被用户指出未遵守逆时针要求；定向排查确认持书段实际为顺时针。后续 [V19](spellbook-counterclockwise-v19-20261010.md) 因用户实机截图中的严重手臂扭曲被明确要求撤回，现已恢复本版文件与动画源。V18 仅作为回退基线，转向及关节衔接未获认可；以下保留原制作记录。

用户恢复开发，首先处理进入专注时「手和书像重复翻转」及手部关节扭曲。V17 是本轮输入；V3 侧握、低位走跑、F 前击及原阅读页面朝向继续保留。收书 V9/V11 仍是待重做现场，本轮不将其列为完成。

## 本轮修改

- 翻掌时固定手腕相对前臂的原握姿关系，前臂与原生辅助骨作为完整骨段运动；肩、肘跟随腕点和肘弯平面，保持原生骨长。取消以独立手腕补偿完成翻掌的做法。
- 五指先求完整的目标局部姿态，再从夹书姿态逐段过渡。目标相对最终父骨一次求出，不再相对正在混合的父关节逐帧重算；各指节使用自己的表面背侧方向，拇指保留独立骨轴语义。
- 0.36 秒以前保留固定夹书接触，随后错峰松开拇指和四指；0.72 秒结束开掌。松手时书承接手的位移与旋转速度，连续转到原阅读姿态，0.90 秒到位，0.94–1.29 秒展开封面。页面最终位置 `(44,-19,-14)` cm 与 25° 阅读倾角保持不变。
- 原运行逻辑在跨越松手时刻后才捕获姿态。现在同帧采样准确的 0.36 秒接触姿态，剥离 V7 导入缩放，再恢复该帧手臂时间。书与手共用离线制作的轨迹，不重新启动独立的翻转缓动。

## 实际落盘

- 作者入口：`SourceAssets/SpellbookEvildeer20261009/Focus/author_focus.py`，转发 `OpeningContinuityV18/author_opening.py`。
- 已生成 `focus.json`、89 组手臂姿态 `SpellbookAuthoredFocus.h` 和 110 组书本轨迹 `SpellbookAuthoredOpening.h`。运行时采样已烘焙的表，不逐帧求解关节。
- 已后台保存 `Focus/Spellbook_Focus.blend`，包含手臂、开合、翻页和保留的收书段；保存日志 `OpeningContinuityV18/save-editable.log`。
- 修改 `SpellbookFocus.cpp`、`SpellbookFocusPose.cpp`、`SpellbookFocusMotion.h` 完成运行引用。无需重新导入书本模型或替换既有 Open/FlipPages 动画资产。
- 修改前的活动文件保存在 `OpeningContinuityV18/Before/`，用于恢复本轮输入。

## 构建与接入范围

现有编辑器通过项目 MCP 批次互斥调用 `CompileLiveCoding`，返回 `Result: Success` 与 `Live coding succeeded`，本轮代码已热编译应用。结果落盘于 `OpeningContinuityV18/livecoding-result.txt`，交付记录为同目录 `delivery.json`。同时修正了姿态缓存按当前键数重建，已有组件不再继续索引旧的 40 键数组。

此次没有关闭、启动或重启 UE。基础 `UnrealEditor-FPSGAME.dll` 未做常规重建；后续关闭编辑器后的常规构建仍需从当前源码生成。未运行游戏、渲染、截图或动作验收，重复翻转和蒙皮观感由用户测试；不以姿态约束或编译结果代替视觉认可。
