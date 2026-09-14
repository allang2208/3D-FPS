# 改造配件图标：发布与本机恢复（2026-09-14）

本轮将用户已接受的枪托图标规则推广到全部改造配件：实际模型、枪械前方朝左、水平正交侧视、透明背景、单件展示。机械瞄具使用一个完整后照门组件。选项和分类图优先使用武器专属文件，缓存使用实际解析键，避免切换枪型后复用错误造型。

## 已完成的制作记录

[制作报告](../../SourceAssets/AttachmentIconAudit20260914/README.md) 和 [审计记录](../../SourceAssets/AttachmentIconAudit20260914/audit_report.json) 记录 5 把枪、124 个有效选项及 74 个实际解析的选项图文件。最终 PNG 共 104 张：保留已接受的 5 张枪托图，替换 26 张，新增 73 张。55 张实物图和 1 张空槽符号由模型渲染，其余为登记过的复用。

制作阶段已导入 99 张 UE Texture，回执见 [import_receipt.json](../../SourceAssets/AttachmentIconAudit20260914/import_receipt.json)。2026-09-14 用户保存并关闭编辑器后，常规 `FPSGAMEEditor Win64 Development` 构建成功；本机日志为 `Saved/BuildEditor/build-20260914-125015.log`。这些是先前制作阶段的记录。本次归档和发布仅进行仓库整理、发布差异及脚本语法检查，没有重新构建、渲染或运行 PIE；游戏效果由用户测试。公开提交按本轮图标改动取样，未包含共享工作区的其他界面改动，也未单独构建公开提交快照。

## 公开内容与本机依赖

- 公开内容：图标加载代码、作者脚本、精简源路径及安装朝向、渲染与复用清单、审计／导入记录、SKILL 标准和归档清单。
- 当前运行目录：`Content/ColdSteelData/AttachmentIcons20260913`。恢复报告列出的 104 张 PNG 及对应 UE Texture。PNG 属于已有 UFS 打包目录；本轮没有增加新的打包路径。
- 本机最终可编辑源和预览：`SourceAssets/AttachmentIconAudit20260914/Icons/*.blend`、`Icons/*.png`、各总览图及 `after_icons_*.png`。这些文件仍保留，不是废案。
- 模型、贴图、FBX、Blend 和 uasset 含既有素材及其衍生内容，原素材许可未扩展为公开再分发许可，因此不纳入本次 Git 提交。图标不是仅凭脚本即可从空仓库恢复的公共素材包。
- 原始可编辑源路径见 [source_paths.json](../../SourceAssets/AttachmentIconAudit20260914/source_paths.json)，逐图选择和复用关系见 [render_manifest.json](../../SourceAssets/AttachmentIconAudit20260914/render_manifest.json)。清单中的 `D:/FPS3D/FPSGAME` 是制作宿主路径；在其他宿主重建时先修改这些路径和脚本中的贴图位置。
- 材质恢复还需要 `WeaponAttachmentFinish20260913/Textures`、`M4Infima/SK_M4_Infima.fbm`、`M1911Attachments20260913/Textures`、`DanWesson715Attachments20260914/Textures` 中被脚本引用的已许可贴图；拟合朝向需要垂直／斜握把源目录的 `fit_final.json`。完整引擎资产恢复边界沿用 [AssetSetup](../AssetSetup.md)。

## 作者脚本的用途与顺序

脚本位于 `SourceAssets/AttachmentIconAudit20260914`；使用 Blender 5.1 的 Python 环境渲染，普通 Python 步骤需要 Pillow，UE 导入脚本需要启用 Unreal Python。中文预览使用本机微软雅黑字体，字体文件未入库。

1. `make_manifest.py` 从精简的 `source_paths.json` 建立渲染／复用清单；`frame_reference.json` 保存导出附件需要的两处安装参考矩阵，替代整份模型扫描报告。
2. `render_icons.py` 读取清单，调用 `icon_geometry.py` 与 `icon_materials.py`，输出可编辑场景、PNG 和来源 JSON。Blender 参数 `--` 后可指定图标键，仅生成指定项。
3. `audit_and_install.py` 是此次授权审计的一次性部署工具：读取固定的 `inventory.json` 制作前基线，保留已接受枪托，生成别名图并同步 PNG；旧版备份位置为本机 `trash/AttachmentIconAudit20260914/Before/Icons`。`audit_report.json` 包含此次部署变化，新轮制作应使用新任务目录和新基线，不重跑覆盖历史结果。
4. `import_icons.py` 按部署记录的变更项导入同名 UE Texture，设置 UI、sRGB、无 mip；保留导入回执。必要的编辑器关闭和原生构建仍按宿主构建脚本要求执行。
5. `make_sheets.py` 与 `make_delivery.py` 在用户要求预览／审计时制作联系图和报告，不自动作为后续每次交付的验收门槛。

扫描探针已完成任务，其重建所需信息已提炼为精简输入。旧图、改动前源码／SKILL 副本、旧联系图和诊断中间件归档至本机 `trash/AttachmentIconAudit20260914`，详见 [逐文件归档清单](../AssetArchives/attachment-icons-20260914.json)。清单保留原路径、目标路径、大小、SHA-256、原因及保留替代物。没有整理其他任务的未提交资产。

可复用规则已同步到 [配件图标标准](../../skills/ue5-weapon-workflow/references/attachment-icons.md)，并从枪械技能、配件标准和通用模型技能进入。
