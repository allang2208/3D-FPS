# 魔法书 V27：书本方向、托掌起伏和开合节奏

用户反馈效果过弱后的排查与修正见 [V28 托掌与节奏排查](spellbook-focus-v28-20261012.md)。本页保留 V27 制作记录。

用户指出待机和展开时整本书方向都反了，要求只调书的方向，保留已认可的手势与整体翻转；另要求展开后的手掌有轻微抖动，移动时不僵硬，开合有速度段落。

## 本次实现

- 书本挂点增加局部 X 轴 180° 转向，原握点位置不变。X 为书脊到书口的方向，转向反转书的上下与封面朝向；不写入手腕、前臂或手指的作者姿态。
- 开书资产的局部根倾角同时作对应坐标转换 `C * Alignment * C`。待机、脱手、阅读、回握使用一致方向；阅读终点保留原位置、页面平面和倾角，印刷内容顶部反向。两侧封面、页骨和原材质复用，金光基底同步。
- 展开后 0.4 秒渐入托掌呼吸与轻微晃动。恢复步幅权重后，移动时叠加同一脚步相位的起伏。小幅平移和旋转作用于整个左臂链，保留指形和腕臂相对关系；关闭前段 0.35 秒平滑收住，在回握前归零。
- 0–1.28 秒的握持翻转、松指过程保持原采样时序。之后采用连续速度的分段 Hermite 时间映射：起势稍慢、展开加速、末端缓停。完整开书由 1.95 秒延长至 2.16 秒；recover 倒放同一条映射，中途取消从当前显示进度回收。
- 16 秒阅读翻页周期、F 推击判定、主副手条件及资源消耗不变。

## 文件与资产

运行时代码在 `Source/FPSGAME/Weapons/Spellbook/`。新增 `SpellbookBookOrientation.h`；节奏位于 `SpellbookFocusMotion.h`，展开托掌层位于 `USpellbookComponent::FocusHandSway`。V24 的原始手臂关键帧表未重新生成。

动画目标目录 `/Game/Weapons/SpellbookEvildeer20261009/Animations/FocusV27/`：

- `A_Spellbook_FocusOpen_V27`：源动画 1.95 秒，运行时映射至 2.16 秒。
- `A_Spellbook_FocusFlip_V27`：同一新朝向下的阅读翻页。

制作脚本、导出 FBX、书本 Blend 和修改前源码备份位于 `SourceAssets/SpellbookEvildeer20261009/Focus/IntegratedV27/`。`export_book.py` 制作新书本轨迹；`import_book.py` 导入并保存动画。`save_editable.py` 从 V24 原始动作采样，保存当前开书与倒放 recover 的可编辑源，不渲染。

活动制作入口 `Focus/author_focus.py`、`author_return.py`、`save_editable.py` 使用后台 Blender 执行，转入 V27 制作脚本。`Focus/Spellbook_Focus.blend` 和 `Spellbook_Recover.blend` 包含本次书本方向和时序；阅读阶段按步伐叠加的托掌起伏保留为运行时层。V23/V24/V25 原预览源保留。

## 交付边界

构建及导入结果记录在 `IntegratedV27/delivery.json`、`import-receipt.json`；编译日志为 `Saved/BuildEditor/build-spellbook-v27-20261012.log`。

按用户规则，未运行游戏、测试、截图或验收渲染。本次效果由用户在游戏中体验确认。
