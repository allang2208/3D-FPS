# 风誓翼锋护手 · 实心羽翼版

高地双手剑护手槽 `highland_gale_wing`。依本轮提供的三视图建模，使用 `Inputs/GaleWing_ThreeViews.png` 正视描线，俯视定侧厚，保留原握柄与三种剑身接口。模型局部 X 沿护翼、Z 朝剑尖，原点和装配偏移不变。旧镂空型已移入 `trash/HighlandSword20261107/SourceAssets/HighlandGaleWingGuard20261107`，保留历史恢复来源。

- `Highland_GaleWing_Feather.blend`：Blender 5.1 可编辑母版，含单独的装饰件、三件剑座、三个已三角化的游戏模型。默认显示装饰件和棱脊接口；其他接口在集合中选用。
- `Export/`：三个带 UV、法线和切线的静态 FBX。Native 用于普通配置；Broadblade 有专用剑座材质槽，只有该槽响应剑身改色；Ridge 以棱脊穿甲刃的低位接触环对接。
- `Textures/`：三种接口共用一套 2048 × 2048 BaseColor、NormalGL、ORM（AO / 粗糙度 / 金属度）。实心羽槽、翼脊、镶嵌金结、握柄束环和正反两面的宝石切面均有几何；表面纹理只提供细磨痕、材质分区和槽面粗糙度。
- `surfaces.py` → Blender 后台执行 `author.py` → `icon_source.py` 可重建模型、导出和从实物取得的灰阶图源。剑座沿用原生 JunctionV5 母版和本目录存档的棱脊接触环。
- `Icon/`：生产图源、内置 imagegen 使用的合成提示词与正式框图。配色规则只适用于图标；实物为银钢、香槟金和冰蓝色宝石。
- `install_meshes.py`、`install_catalog.py`、`install_icon.py`：按顺序保存新资产、替换护手模型路径和说明，再保存实际 UI 纹理及同键 PNG。运行中的编辑器使用工程互斥桥，编辑器关闭时可用 `import.ps1` 启动无界面 commandlet。
- 资产回执 `saved-assets.json`、目录回执 `catalog.json`、UI 回执 `saved-icon.json`。不改变攻击或奔跑体力计算、复制和存档格式；未运行游戏、截图或进行联机验收。


后续已接入击杀返体与3秒迅捷。当前机制、目录恢复顺序及检查范围见工程 `Docs/Publication/HighlandSword20261107/README.md`，本目录初次模型保存记录只描述模型制作阶段。
