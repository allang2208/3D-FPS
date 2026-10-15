# 法杖快捷魔法源码复核

范围：本次新增的十格圆盘、P 配置抽屉、法杖左键和右下角魔法状态行。按用户请求进行源码和资源引用检查，修复明确问题；不启动编辑器、游戏或截图，不把源码推演等同实机复现。

## 发现与修复

1. **快捷键施法预览残留**：已凝聚火球后按住 Q 进入轨迹预览，再长按 R 打开圆盘，圆盘吞掉 Q 松开事件；原先打开时仅 `CancelStaffMagic()` 清除左键来源，Q 来源仍留在 `AimPreviewIndex`。圆盘接管输入前改为调用公共 `CancelSpellAimPreview()`，同时清除预览和输入来源；不通过模拟松手发射魔法。
2. **忙碌期间插入圆盘**：法杖 R 分支缺少已有弹药分支的武器／施法忙碌检查，可能先由 `FireReleased()` 中断挥击，再让之前排队的施法开始执行。R 按下和保持期间均使用现有 `IsWeaponBusy()`、`IsSpellGestureBlocking()` 仲裁。已经凝聚、手势已结束的悬浮魔法仍可打开圆盘；执行中的动作完成后再切换。
3. **打包后的纹理引用遗漏**：11 个魔法图标 PNG 和同名 `.uasset` 均存在，但配置仅 `DirectoriesToAlwaysStageAsUFS=ColdSteelData/Skills`。圆盘和状态行使用异步 UObject 路径，不能用原始 PNG 携带代替烘焙。本机引擎 `CopyBuildToStagingDirectory.Automation.cs:846–848` 明确把 `.uasset` 从额外 UFS 目录排除。补充 `/Game/ColdSteelData/Skills` 的 `DirectoriesToAlwaysCook`；没有执行完整 Cook／打包。
4. **配置抽屉 DPI 不同步**：原先字体和外部尺寸随布局刷新，标题高度、内边距及收回按钮样式停留在首次创建的 DPI。配置栏现在跟随 `UpdateInventoryLayout()` 更新这些尺寸和主题画刷，保持与技能栏一致。
5. **圆盘命中超出可见区域**：绘制外沿为 1 个半径，命中却允许到 1.06 个半径；拖放到盘外仍可登记。命中范围改为可见外沿，仅保留浮点边界容差。
6. **重复挂载的旧图标**：`NativeDestruct()` 原先只把已请求技能设为 None，图片刷子仍保留；控件复用且当前选择已清除时，后续 None 提前返回会留下旧图标。销毁阶段统一走图标清除函数，取消请求、清空刷子并折叠图标。

## 其他检查结论

- 十格为空／默认不选、选中魔法随交换移动、清除选中格自动取消选择、保存失败不提交：沿用模型提交路径；本轮未改动存档结构。
- 右下角冷却覆盖全部 11 个可登记主动魔法，读取对应技能的实际剩余值，未建立独立计时器。
- 已选魔法失败不会挥杖，中心／空槽确认取消选择后才恢复原普通攻击入口；Esc 不提交选择。
- 菜单、换武器、死亡及失焦的圆盘关闭路径仍在；配置拖放保留来源快捷栏，过期绑定快照不提交。
- 实际键鼠、图标观感、多分辨率画面、联机和打包运行仍需游戏内确认。

## 已完成的检查和构建

- 对照 `skills.json` 的 11 个主动魔法检查 PNG 与同名 `.uasset`，22 个文件均存在；纹理目录已加入 AlwaysCook。
- 本轮修改文件的 `git diff --check` 通过，仅有工程既存 CRLF/LF 提示。
- 共用 Editor 构建开始于本轮最后源码修改之后，完成全部 223 个动作和 DLL 链接，`Result: Succeeded`，213.31 秒。收据副本：`Saved/BuildEditor/staff-magic-review-editor-shared-20261014.log`。
- 首次共用 Game 链接受到并行更新的 `UFPSSurvivalComponent::GetState()` 声明／实现时间差影响；原失败收据保存在 `Saved/BuildEditor/staff-magic-review-game-20261014.log`，未修改生存组件。实现完整落盘后，共用完整 Game 构建成功；本轮最后的 Game 构建也完成 3 个动作及 EXE 链接，`Result: Succeeded`，17.34 秒，收据：`Saved/BuildEditor/staff-magic-review-game-final-20261014.log`。
- 未启动编辑器、游戏或执行完整 Cook／打包。上述结论属于源码排查、资源引用检查及构建证据，不代表实机输入、画面或联机验收。
