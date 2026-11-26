# S12K 护木与前机匣材质升级 · 2026-10-31

针对上一轮实际 UE 离屏画面中护木和机匣表面过于均匀、呈现灰白模观感的问题，更新当前枪体实际绑定的五个材质实例：Handguard、Body、ReceiverCover、Barrel、GasTube。五份 `.uasset` 已通过现有编辑器桥和 UE 包保存接口落盘，保存回执为 `SourceAssets/Saiga12KMaterialRepair20261031/upgrade-receipt.json`。

护木改用更深的聚合物底色，粗糙度中心为 0.56；恢复已有 WS1 细纹与细颗粒的粗糙度响应，纹理平铺尺度为 4 cm。其湿润响应明确为 Polymer，避免沿用金属湿膜参数。

机匣、机匣盖、枪管和导气管保持深色金属身份，分别设置 0.36、0.34、0.31、0.37 的粗糙度中心，并启用低强度细纹粗糙度变化。保留干净表面，不加入大块斑驳、随机磨损或划痕。

复用原有 `T_WS_Grain` 及其三向投影；本次细纹表现为粗糙度变化，没有新增法线或纹理资源。原始结构法线、遮罩、UV、几何、材质槽、骨骼和运行引用不变。共享母材质与其他枪械预设不变，枪托、弹匣和改造附件未改动。

制作配方在 `SourceAssets/Saiga12KMaterialRepair20261031/finish-upgrade.json`，已合入 `SourceAssets/Saiga12KClosure20261018/finish.json`。当前制作入口 `Tools/Saiga12KClosure/install_assets.py` 接受每个部位的标量覆盖。升级前五份材质资产及两个制作源文件备份在本轮 `BeforeUpgrade` 目录。

本轮只更新并保存材质实例，无 C++ 修改。未进行升级后的渲染、游戏或视觉验收，效果交由用户测试；同目录 `before_*.png` 是升级前检查画面，不能作为本版效果图。
