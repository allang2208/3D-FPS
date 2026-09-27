# 三款木弓体制作与接入 · V14

根据 [三款方案](bow-three-body-concepts-20260926.md)，用本地 Blender 完成三款独立弓体、木纹 PBR 和实模配件图标，接入现有五槽改造的“弓体”栏。本批不调用 Meshy，不新增动作、手臂、音效或射击系统。

## 三款弓体

| 选项 | 造型与材料 | 玩法取向 |
| --- | --- | --- |
| 游隼弓体 | 窄薄木臂、明显反曲；蜜金木纹、红褐薄层 | 快拉、低消耗，牺牲单箭威力 |
| 磐木弓体 | 宽厚饱满截面；深栗木纹、深色背衬 | 单箭高伤害，拉弓和持弓代价较高 |
| 静枝弓体 | 宽扁长弧；浅白蜡木、深胡桃夹芯 | 更稳、更长保持，拉弓和举弓略慢 |

| 游隼实模配件图 | 磐木实模配件图 | 静枝实模配件图 |
| --- | --- | --- |
| 游隼（仅本机：`SourceAssets/BowBodyVariants20260926/Icons/bow_dark_riser_swift_limb.png`） | 磐木（仅本机：`SourceAssets/BowBodyVariants20260926/Icons/bow_dark_riser_heavy_limb.png`） | 静枝（仅本机：`SourceAssets/BowBodyVariants20260926/Icons/bow_dark_riser_steady_limb.png`） |

上图是改造栏使用的 Blender 实模部件图，不是 UE 游戏效果截图。概念中的弓梢在实际制作时收敛到原有弦挂点；没有让概念外形改变现有锚点。

三款使用连续木体的拓扑变形，原中央接触面与两端弦槽保留。每款约 141.8 cm 高、9,216 个三角面，局部改变厚度、宽度和弧度，整体缩放为 1。木纹和层压沿长度方向连续，中央沿用原贴图并平滑过渡到新木材。

握把缠带、弓弦、箭台、木制瞄具和箭矢仍各自独立，沿用 V13 装配关系。已有中央包握、箭台与瞄具贴合区域不改变几何。当前拉弦点、箭尾、ADS 瞄点与 V11 动作数据保持原配置；没有新增弓臂蒙皮形变。

## 已接入的数值

只换弓体、其余槽原装，不计人物属性、强化、附魔与精通时：

| 参数 | 原装 | 游隼 | 磐木 | 静枝 |
| --- | ---: | ---: | ---: | ---: |
| 基础满拉伤害 | 46 | 41.4 | 57.5 | 46 |
| 拉满耗时 / s | 1.40 | 1.12 | 1.75 | 1.54 |
| 满拉箭速 / m/s | 98 | 90.16 | 107.8 | 98 |
| 满拉体力消耗 | 3 | 2.55 | 3.90 | 3.15 |
| 满弓保持 / s | 2.20 | 2.20 | 1.76 | 3.08 |
| 进入 ADS / ms | 240 | 204 | 276 | 264 |
| 退出 ADS / ms | 200 | 170 | 230 | 220 |
| 晃动倍率 | 1.00 | 1.00 | 1.15 | 0.70 |
| 腰射扩散倍率 | 1.00 | 1.10 | 1.05 | 0.85 |

数值直接采用先前 `proposed-stats.json` 的倍率，通过现有共享公式进入手持、改造面板与物品说明。满 ADS 的随机扩散规则保持不变；静枝的优势为降低晃动与延长保持时间。其他槽继续按原规则组合。同一个弓体槽只能选一种，原装和 `strong_draw` 继续保留。

## 落盘位置与接入

- 新 UE 资产：`/Game/Weapons/DarkBow20260925/BodyVariantsV14`。三个 StaticMesh、三个材质和九张 2K PBR 贴图。
- 图标：`Content/ColdSteelData/AttachmentIcons20260913/bow_dark_riser_{swift_limb,heavy_limb,steady_limb}.png`，以及同目录的三份 Texture2D。1024×1024 透明底，朝向与现有配件图一致。
- 源文件：`SourceAssets/BowBodyVariants20260926/Bow_ThreeBodies.blend` 与 `Export/`。
- 配置：仅向 `Content/ColdSteelData/bow-gunsmith.json` 的 `riser.options` 添加三款网格与倍率，`Config/DefaultGame.ini` 添加相应打包目录。
- 备份：`Saved/BowBodyVariants20260926/Before`。保留被修改配置的原文件。
- 回执：`SourceAssets/BowBodyVariants20260926/import-receipt.json`、`install-receipt.json`。

当前基础弓和存档不自动切成新弓体。下次启动游戏后，在弓的改造台进入“弓体”，选择游隼、磐木或静枝并应用。手持和改造预览沿用已有按部件数据解析模型的路径，装备栏整弓图标继续由已有装配图标管线生成。

## 交付边界

后台执行制作、导出、导入和资产保存；没有启动交互式 UE 编辑器或游戏，没有追加自测与验收截图。本批不修改 C++，无需重建模块 DLL。模型实际观感、ADS/搭箭状态与数值平衡由用户在游戏中测试，不声明已通过游戏验收。

几何来源为项目现有的用户提供 Sadra Medieval Wooden Longbow；新模型为其局部保形衍生版本，原始资料见 [木质长弓接入记录](dark-bow-wood-longbow-20260925.md)。新增木纹、粗糙度、法线和层压贴图在本地制作，源资产保持本地使用。
