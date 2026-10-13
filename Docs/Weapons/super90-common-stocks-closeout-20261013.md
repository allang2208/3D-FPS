# SUPER90 通用后托收尾与发布

2026-10-13，范围仅为五种通用后托及其 SUPER90 专用连接结构。

## 完成内容

`stock` 槽支持原厂恢复、骨架、镂空轻型、高性能、战术伸缩、可调式战术后托。通用选项沿用公共属性和图标，原厂恢复使用本枪真实模型图标。

原厂后托按原材质分出三个可隐藏组。替换件保留原装前接颈，以封闭过渡座、23.2 mm 连接杆和各自入口过渡连接；连接杆随枪托一起装拆。沿用 `SetGunsmithStock`、枪匠草稿/应用/取消、Parts 保存、掉落及展示装配；图标资源异步预加载、第三人称隐藏分组和 Cook 目录已接入。

金属匹配 SUPER90 的 WS1 表面；聚合物、橡胶和原有装饰保留各自身份。不改手臂、抓握、动画或武器玩法时序。

## 收尾发现与处理

- 旧位置阈值多选了扳机护圈附近 120 个三角形。改为从肩托端追踪独立聚合物网格，原厂隐藏组由 4158 修正为 4038 面；这 120 面留在原枪，替换件中也移除了对应碎片。
- 原导入脚本依赖 UE 元数据标签，但包重载后标签为空，导致二次导入误判宿主改变。现按实际材质组识别，已有分组不会重复拆分；拆分前输入受到保护。
- 两款配件的外观介绍重复描述了属性卡效果。已改为简短结构介绍，数值保持不变。
- 原生产网格位置和三角索引完全保持；全部 UV、权重及绑定骨架保持。最终法线读回在小数点后五位的比较精度内一致；不据此宣称文件逐位相同。
- 五套新连接结构均无新增开放后端或零面积面。UE 网格、材质引用、选项及图标已读回。
- 五款连接杆与接座完成离线灰模侧向检查，接头连续；这是结构检查，不是 UE 材质或游戏视角验收。

检查回执留在 `SourceAssets/Super90CommonStocks20261013/asset_check.json`、`model_check.json`。

`FPSGAMEEditor Win64 Development` 正式构建已成功，日志为 `Saved/Super90StockCloseout20261013/Editor-UHT.log`。早期构建还遇到角色反射头的生成宏行号过期；使用 `-ForceHeaderGeneration` 重新生成 UHT 后完成普通模块链接，没有改写并行任务的业务代码。编译针对当前完整本机工作区，不等同于对公开源码切片做了独立克隆构建。

5 份过期建模自动备份已移入 `trash/super90-stock-closeout-20261013/`，逐项散列见 [归档清单](../AssetArchives/super90-stock-closeout-20261013.json)。原始输入和资产回退包继续保留。

未进行 PIE、ADS/换弹视觉验收或双端联机运行测试，不宣称整个 SUPER90 没有任何缺陷。

## 本机资产与恢复

26 个 UE 资产已保存，主目录为 `/Game/Weapons/Super90/CommonStocks20261013`；生产网格继续使用 `/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7`。

完整制作源与恢复入口：[SourceAssets README](../../SourceAssets/Super90CommonStocks20261013/README.md)。保留 `Inputs/`、`inputs.json`、`Before/SK_Super90_V7.uasset`、母版 Blend、导出 FBX、材质与图标；这些资产及许可依赖留本机。重建顺序为保留输入 → `author_models.py` → `author_factory_icon.py` → `install.py` → `integrate_catalog.py`。已经完成原厂分组后，不重跑 `read_inputs.py` 覆盖前置输入。

公开范围为本次 C++、目录与 Cook 配置的精确改动、原创制作/检查脚本及说明；不公开 UE 包、第三方模型、纹理、密集几何、备份或构建输出。并行任务改动不纳入本次提交。
