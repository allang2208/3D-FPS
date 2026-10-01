# 暴风雪拖拽修复与冰系图标替换

用户反馈暴风雪无法从技能列表拖到底部快捷栏，并要求重制冰墙、暴风雪图标。

## 拖拽原因与调整

暴风雪的模型、卡片、快捷栏允许绑定、Drop 和存档路径已经接入；迁移时漏掉 `ColdSteelSkillPage.cpp` 中两个入口：

1. `NativeOnPreviewMouseButtonDown` 的可拖卡片列表未登记 `BlizzardDetailButton`，按下时没有进入鼠标捕获和 `DetectDrag`。
2. `NativeOnDragDetected` 的图标选择缺少 `BlizzardIconBrush`。

本轮补齐这两处，复用既有 `StartQuickDrag → DropQuickDrag → BindQuickSkill → CommitState` 链路。单击仍打开详情；拖动从列表开始，拖影使用暴风雪自身图标，投放、交换和绑定存盘沿原实现。

这是已定位并修改的源码问题，不将构建结果称为实际拖拽验收；没有启动游戏或 PIE。

## 图标制作与替换

按正式冷钢规则，使用内置 `image_gen` 以当前冰锥图标作风格参考，生成银色六边框和石墨暗底的写实冰墙、灰云/落雪/坠冰图标。最终 PNG 已复制到 `SourceAssets/IceSkillIcons20260930/` 和 `Content/ColdSteelData/Skills/` 正式同名路径。详细来源、完整提示词和恢复方法见 [图标制作记录](../../SourceAssets/IceSkillIcons20260930/README.md)。

图标为现有 UI 直接加载的 PNG，本轮没有新建 Texture uasset 或启动 UE。`skills.json` 继续使用同名路径，各显示位置共用同一图源。恢复脚本和旧资产制作入口均改读新图；旧图按散列记录保留在本机 trash，未修改玩法数值、法杖限定、材质或区域伤害。

## 构建

Editor Development 构建成功（`build-editor.log`，386.40秒，`Result: Succeeded`）。Game Development 构建成功（`build-game-low-parallel.log`，732.08秒，`Result: Succeeded`）。日志目录为 `Saved/IceSkillIcons20260930/`。

首轮 Game 构建因系统提交内存不足出现 UBA `VirtualAlloc` 失败；停止的仅是本轮 Game UBT 及其编译器子进程。随后使用 `-NoUBA -MaxParallelActions=2` 完成构建，保留运行中的编辑器。未进行运行时测试，由用户自测拖拽、投放与图标观感。
