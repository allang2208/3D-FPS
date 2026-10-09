# 发电区文字卡片修订 · 2026-10-05

按用户要求处理 RefineV2 文字卡片拉伸和贴面闪动，保留现有三连房布局、设备主体、容器交互与其他主题资产。

已通过现有 UE 编辑器互斥桥实际导入并保存 7 个修订网格、1 张 4096×4096 图集、1 个不透明搪瓷文字材质；原测试地图中 26 个 Actor 更新，覆盖 175 块实体牌面。入口仍为：

```text
open /Game/GameMaps/Design/L_PowerTheme20261004_Subject
```

## 原因与处理

- 原导出 FBX 的 `PW_Labels` 面采样整个 0–1 UV 范围，没有保留各文字的图集矩形，长条实体承载了方形图集。`author_scene.py` 现改为新增角点颜色属性后重新取得 UV 层，避免向过期的自定义数据句柄写入坐标。
- 原控制台文字片与封闭底牌只相隔 0.1 mm，柜体铭牌也另叠加了相隔 0.4 mm 的文字薄片。现在删除对应旧牌壳／印刷片，制作唯一印刷正面、侧壁和背板，不在文字下面保留第二层金属正面。
- 服务器柜两块不同比例的实体铭牌共用长条文字矩形，其中一块约有 2.89 倍比例失真。现在按实际尺寸分别排版；柜体规格牌等同步处理。
- 44 块源牌面使用 34 种尺寸与内容版式，复用工程 Noto Sans SC 字体原生绘字，不缩放文字位图。图集取样高度保留亚像素边界以对应真实比例；牌区有 12 px 色带，正常 mip，完整精度 UV。
- 保留其余三角面、自定义法线、UCX、轴心和场景变换。配电柜与服务器柜使用本主题独立资产，未重写共享模型。货架和容器的原文字 UV 比例正确，继续复用。

## 源文件和落盘

- `cards.json`：位置、朝向、牌面尺寸、内容与图集范围。
- `Authored/*.blend`、`Authored/*.fbx`：可编辑模型和引擎导入文件。
- `Authored/T_Power_TextCards.png`、`Authored/atlas.json`：图集和字体来源。
- `collect_cards.py` → `author_art.py` → `repair_geometry.py`：从原配方恢复牌面、原生文字排版、局部替换几何。
- `install.py`：独立命名空间导入，只替换 PowerTheme 相关组件并保存原测试地图。
- `Receipts/install.json`：实际保存回执，状态 `map_saved`；`Receipts/ue-install-02.txt` 为桥返回记录。
- `Receipts/source-diagnosis.json`：本次用户要求的问题定位数据。

引擎命名空间：`/Game/Dungeons/PowerTheme20261004/TextCards20261005`。原 FBX 和旧 UE 资产保留。`Scripts/text_card_revision.py` 已接到样板重建与地牢草案导出；当前 `Config/module-drafts.json` 同步采用修订网格，仍为草案，没有注册随机地牢。

本轮未运行游戏、PIE、渲染截图或验收测试；视觉效果由用户进图体验。导入／保存成功不代表运行验收通过。
