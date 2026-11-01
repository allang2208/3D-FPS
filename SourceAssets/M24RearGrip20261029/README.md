# M24 通用后握把适配

## 目录与数值

新增 M24 的 `reargrip` 槽和原装 `false` 选项，复用三款通用后握把的 ID、名称、属性及共享图标。数值由注册时的 M4 通用件条目复制，不建立 M24 独立倍率。

| 改造 | 开镜耗时 | 后坐力 | 腰射随机散布 | 稳定性 |
|---|---:|---:|---:|---:|
| 幻影后握把 | +15% | -10% | +10% | — |
| 稳固防滑后握 | +10% | -20% | — | +15% |
| 均衡后握把 | — | -10% | — | +10% |

外观说明按 M24 的覆层形态填写。没有接入仅限指定 AR 枪型的 `hk416_reargrip`。

## 模型与材质

源为 `../M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend` 中 `M24_base` 的原枪托连通表面。按枪托颈部真实位置裁出覆层，保留原曲面；不替换枪托，不修改宿主骨骼网格、武器位置、V9 手臂、手指轨道或动作时间。

覆层向外偏移 0.055–0.16 mm，边缘在 3 mm 范围内收薄；前缘位于源坐标 y=0.041 m，避开扳机护圈；上缘 z=0.097 m，避开活动枪栓。三款分别使用分段横肋、橡胶颗粒和细横纹法线。纹理起伏只在材质中表达，不推挤手指接触面。

材质由共享 `M_WeaponSurface` 派生静态用途母材质，并基于 `MI_WS_CleanPolymer` 的预设设置制作三个实例，延续当前 M24 深色聚合物色调和标准湿润层。宿主 `M24_Body` 材质不变，兼容独立碳纤维栓机。

制作源：`author.py`、`textures.py`、`M24_RearGrip_Editable.blend`、`Textures/`、`Exports/`。`source_layout.py` 只读取组件结构供建模定位。

## 装配

- `M24Attachments::IsRearGrip/MeshPath/Configure` 使用原 M24 根骨配准矩阵，覆层随枪体动作。
- `SetGunsmithRearGrip` 的 M24 分支安装／移除独立覆层；卸下销毁组件，原厂握持表面一直保留。
- 既有枪匠预览和背包图标调用相同装配入口，资源通过 M24 配件列表预加载。
- 第三人称装备沿用现有附属网格快照通路。没有增加 Tick、持续碰撞或新的手部 IK。
- 继续使用枪匠实例的通用存档机制；没有修改其他枪型的默认改造范围。

正式资产：`/Game/Weapons/M24/RearGrip20261029/`。图标仅新制 `ue_m24_reargrip_false`，三款改造和分类沿用现有 `reargrip_*` / `category_reargrip` 共享图。

## 保存与构建

`run_assets.ps1` 通过现有互斥导入保存，已有编辑器时使用原桥；关闭时使用无界面 commandlet。`install_receipt.json` 记录实际资产保存，`catalog_receipt.json` 记录目录更新。旧模块化发布器已追加本次目录步骤，当前安装不运行旧的整套发布器。

`build.ps1` 编译本次装配入口及工厂部件配方消费者，`Build/build-receipt.json` 的 `published` 记录正式 DLL 是否发布。`-StageOnly` 只暂存，`-PublishOnly` 在编辑器关闭后按最新模块对象重新链接发布。

按用户规则未启动游戏、运行自动测试、接触诊断或预览验收。编译与保存不代表实机动作及观感验收。

源模型归属沿用 `../M24CustomScope20261026/ATTRIBUTION.md`；本次派生为 M24 枪托颈部覆层和程序纹理。
