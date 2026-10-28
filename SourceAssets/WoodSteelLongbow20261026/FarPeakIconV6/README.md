# 远峰重弓体图标修订（2026-10-27）

本轮仅重制 `bow_woodsteel / riser / highland_far_peak` 的改造栏图标。

- `author_part_reference.py` 从实装源 `FarPeakV4/HighlandLongbow_FarPeak_Production.blend` 提取唯一弓体，生成灰阶实物输入；输出 `FarPeak_Icon_Input.blend`、`far_peak_actual_part.png` 与 `part-source.json`。
- 内置 imagegen 使用认可的 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 和实际部件输入制作最终 PNG。完整提示词为 `imagegen-prompt.txt`；生成原件来自 `C:/Users/allan/.codex/generated_images/01a1767e-a054-7ac3-9096-1a5de77fc746/exec-28baf0ea-dcbf-4393-b5fc-f712f39bd194.png`，本目录保留项目副本。
- 外观为厚倒角金属框、四角铆钉、银色内环、深灰不透明底板与单个完整弓体，外框之外保留窄透明边。
- 部署 PNG：`Content/ColdSteelData/AttachmentIcons20260913/FramedBows/bow_woodsteel_riser_highland_far_peak.png`；同步 `FarPeakV4` 的同名作者 PNG。
- 纹理：`/Game/ColdSteelData/AttachmentIcons20260913/FramedBows/bow_woodsteel_riser_highland_far_peak.bow_woodsteel_riser_highland_far_peak`。使用 UI 组、EditorIcon 压缩、sRGB、NeverStream、NoMipmaps、最大 1024。
- `import_icon.py` 已通过 `../run_stage.ps1 -Stage FarPeakIconV6/import_icon` 在后台实际执行，纹理已保存；执行回执见 `import-receipt.json` 与 `import_icon-commandlet.json`。
- 旧 PNG、纹理和作者脚本按清单备份到 `trash/FarPeakIconBeforeV6-20261027-113018-380989/`。旧手工框场景保留为历史源；`FarPeakV4/author_icon.py` 已改为生成实际部件输入，不再用旧框覆盖最终图。

后续模型改变时，以新的实际部件输入和标准框重新调用 imagegen，并创建新的导入批次；不能把已有导入回执当成新版完成记录。

未更改武器数值、三维模型、运行材质或加载代码，不需要原生构建。未启动游戏或进行游戏测试，交由用户测试。
