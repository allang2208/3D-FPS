# 技能快捷栏拖拽（2026-09-14）

实现记录：`D:/FPS3D/FPSGAME/Docs/UI/skill-quickbar-plan-20260914.md`。原 game-dev 依据为 `src/ui/quick-bar.js` 和 `src/ui/skill-manager.js` 的主动卡拖放处理。

- 用户选择 Q/E/X/1–4 七槽，技能与消耗品混放；E 优先仓库／拾取／传送门，无交互目标才使用绑定。C 滑铲和左 Shift 闪避保留。
- `ColdSteelQuickBarTypes` 的混合引用和 `ColdSteelQuickBarModel` 是权威绑定。快捷栏版本 1 从旧数字四槽迁移；Q 初始绑定火球。`Hotbar`／`HotbarDefinitions` 只作为数字槽兼容视图，不直接另写一套数据。
- 已绑定内容投放到占用槽时交换，空槽移动；未绑定内容覆盖目标引用。同一技能／物品实例只绑定一次。解绑不移除技能或背包实体，不重置技能冷却。
- `ColdSteelQuickSlot` 管理显示和鼠标入口；`ColdSteelQuickDrag` 的图标由现有 `ColdSteelDragVisual` 跟随指针，避免默认拖影插值。主动技能卡点击查看、拖动绑定；被动卡不拖动。
- 面板视觉隐藏与输入释放分开：技能卡起拖隐藏抽屉，松手后关闭并还给游戏。栏外释放解绑；Esc／关闭／失焦是取消，不解绑。拖动期间屏蔽游戏技能输入。
- 绑定快照判定拖放失效，不用自动保存的 Generation 单独使拖动过期；物品实体投放继续使用原实例快照。提交成功后由模型事件和既有 HUD 冷却刷新更新显示。
- 已完成必要构建，未进行实机测试。今后用户提出测试时再检查实际拖放、焦点、持久化和不同窗口尺寸。

## gamedev 图标与冷却表现迁移

用户随后要求恢复原项目的居中图标、右下角键位闪动、黑色 CD 遮罩及完成白光。现行数值和层序见 `Docs/UI/ui-cold-steel-design-system.md` 第 10 节，实施记录见 `Docs/UI/weapon-details-quickbar-plan-20260914.md`；替换历史隐藏技能图标、移除按键持续闪动的条款。

- UMG 快捷槽外层 OverlaySlot 必须双向 Fill；槽壳显式零 Padding，图标在固定框内 ScaleToFit，避免天然图片尺寸改变槽位和角标的参照区域。
- `SColdSteelCooldownMask` 通过裁剪完整圆角画刷实现顶部固定遮罩，插值只影响展示。冷却继续来自技能／物品实例，初次显示或换绑建立基线，同一绑定冷却归零才触发白光。
- 快捷键、数量置于闪光之上。动画曲线按原 CSS 的时间坐标求值，不重建控件、不更新预览或写业务冷却；默认仍由用户测试。
