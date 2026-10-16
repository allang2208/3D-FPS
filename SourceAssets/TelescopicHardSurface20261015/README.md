# 伸缩后托精确硬表面重建 — 2026-10-15

用户否决了旧生成网格的多轮平滑、法线修复及 M4 直接复用方案，要求重新建模。本轮只给 M16 接入新的后托主体，保留原配件 ID 和真实安装接口。

## 新制作

- 全新解析几何：车削套管、锁紧套圈、真实穿孔的背带环与定位齿条、带套管净空的托腮座、独立聚合物侧板、凹六角紧固件、规则槽纹调节旋钮、释放扳片、镂空连接支架、三角开口的后脚框架、带实体防滑槽的橡胶尾垫。
- 大平面保持平直，曲面来自规则圆环。高光由几何倒角和作者角点法线形成。
- 唯一保留的旧几何是 M16 机匣侧 1,268 面闭合安装接口，来自前轮已保存的装配源；旧生成后托主体和法线贴图不参与新模型。
- 四种独立 WS1 材质：阳极铝、聚合物、橡胶与紧固件钢。结构法线使用中性法线，微细表面仅轻微影响粗糙度；不采样旧生成图集或旧 M16 后托材质分支。
- 约 49,600 个三角形。长度与后端位置沿原安装合同，M16 根空间下导出，现有运行缩放与枪匠 ID 保持原值。

## 交付文件

- `design.json`、`author.py`：尺寸、分件和可复现的建模入口。
- `Models/M16_Telescopic_Parts_Editable.blend`：分件可编辑源。
- `Models/M16_Telescopic_Game_Editable.blend`：合并游戏源。
- `Models/SM_M16_Telescopic_HardSurface.fbx`：游戏导出。
- `production.json`：实际分件、面数、尺寸和材质记录。
- `Before/`：接入前的 M16 网格与材质映射备份。
- `install.py`、`install_receipt.json`：导入、实际保存和当前引用回执。

独立源资产位于 `/Game/Weapons/M16A2/TelescopicHardSurface20261015/`；M16 实际运行入口仍为 `/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic`。当前材质绑定清单同步此新模型，重导入源指向本轮 FBX。

只制作、必要资产构建、导入和保存。不自动运行游戏、渲染预览或测试；模型观感由用户自行查看，保存完成不等于视觉验收。实际接入是否完成以 `install_receipt.json` 的 `complete` 为准。

实际交付：4 个独立材质实例、独立新网格及 M16 原运行网格均已保存，材质映射已更新；`complete=true`。后台 commandlet 退出码 0，本次新网格导入/构建日志没有近零切线或退化切线提示。没有进行游戏或视觉验收。
# 后续状态（2026-10-15）

用户要求继续排查后，同条件对照确认 R2 法线纹理引入菱形异常。M16 当前已恢复原始低模与匹配法线，接入记录见 `../M16StockMaterialDiagnosis20261015/README.md`。本目录的重建模型及回执保留为历史候选，不再代表 M16 当前运行几何。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/TelescopicHardSurface20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
