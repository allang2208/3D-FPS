# Kaitlin 女性角色源码、配方与接入修复

本批公开 F6 身体切换、原生身体/衣物/毛发选择与异步重建、女性服装配置、家具相机采样及制作脚本。初次装配、头发 LOD 修正和后续补齐均来自同一角色工作线。原始 Kaitlin 来自用户选择的 [Fab 商品](https://www.fab.com/listings/ebbc58e2-f745-482c-bb9a-9d73b6379d93)；获准本地使用不等于可以公开其资源包。

## 直接进入运行树的内容

- `FPSPlayerBodyVariants`、`FPSPlayerBodyAppearance`，以及身体/换装组件和 F6 面板中本批拥有的差量。
- `player_body.json.body_variants.kaitlin` 的完整身体配方与 `modular_outfits.json.body_variants.kaitlin`；Native/Kaitlin 的 Cook 目录。保留已公开的平行战锤动作值，后续新版值列在延后字段清单。
- 原公开包体基准相同的登山包、行军包、重装远征包、斜挎包：男性工装夹克配对字段；女性六款配对均在女性变体内。
- `Tools/KaitlinPlayer` 的当前制作/保存/字段发布入口及三处技能参考。需要合法取得的模型、作者输入和生成回执才能复现，脚本不是素材替代品。

## 共享宿主与延后字段

**此提交不是完整本机工程的可构建检出。** 当前公开 `ColdSteelPlayerState` 尚缺本机的库存确认、分片恢复等前置，`FPSFurnitureRestComponent` 也未完整公开。本批不把这些混合宿主整文件复制入库。

`integration-prerequisites.json` 对应七份补丁：四份联机宿主增量、家具相机调用增量和诊断命令的头/源文件。恢复相应本机宿主后，按规范化 LF/UTF-8 的前置 SHA-256 应用；哈希不符时合并本批语义，不覆盖现有文件。四份联机补丁应一起应用：旧镜像保留最新头型/发型；库存快捷事务和确认基线保持未上传外观的待发送状态；心跳、库存、篝火生产者记录对应上传身份。

`Integration/deferred-config-fields.json` 保留九个延后字段：开拓者/远界男性夹克配对所需的新包体基准尚未在公开运行树到位，另有一项平行战锤的女性动作修订。清单含所需原网格/刚体变换或已公开前值，不能在旧包体上直接拼入不匹配的新背带。工装夹克物品目录、ST6 下装新修订、最新床铺源及部分原生手部/第三人称宿主同样依赖本机对应制作批次；这里公开女性适配引用，不冒充这些功能已由本提交发布。

## 本地资源与恢复

- 保留 `.mhpkg`、绑定后的 AuthorHost、原生完整身体/脸/DNA、贴图、Groom、衣物/背包、动作、密集几何与采样；这些二进制及作者数据不上传。`SourceAssets/Kaitlin*` 已显式忽略，正式运行 JSON 仍按字段发布。
- 主线为 `prepare_source` → `assemble`/`export_full_body` → 原生提取与适配 → 保存资产 → 字段发布。已绑定源不需要重新绑定。当前补齐使用 `prepare_completion`、`complete_furniture_assets`、`complete_furniture_cameras`、`author_jacket_packs`、`complete_pack_assets`、`publish_completion`。
- `publish.py` 属于初次完整接入入口；后续修订使用明确字段发布器，不能用旧快照覆盖已更新装备和动作。旧家具直接发布器已经退役；通用重定向脚本要求显式批次，当前包装入口为 `complete_furniture_assets`。
- 资产恢复后沿既有 UE 批次互斥后台保存；整理/源码发布不自动启动编辑器、PIE 或游戏。

## 归档与证据

93 份废案（约 219 MiB）已移至 `trash/kaitlin-retired-20261024/`，包括未发布的首版背带、36 个被替换动作包、旧更新器及失败/中间输出。48 个包在当前运行 JSON 和 UE 包引用中未发现外部使用，逐文件原路径、归档路径、字节数、SHA-256、原因和替代物见 `archive-manifest.json`；移动后散列一致。当前六份复用 Idle、全部正式 R2 包、活动动作和制作依赖保留，重定向缓存移除已退役条目并刷新当前角色映射。

历史完整本机 Editor/Game 构建成功；18 个家具映射、54 条女性眼位轨迹、男女各六份夹克背带已落盘。隔离图仅确认女性 Chair/Sofa/Bed 姿态能播放，不证明实际 E 键交互。此前没有真实主客机、晚加入、重连、死亡重生、换图或视觉穿模验收，脸部与 Fab 的相似度仍待画面对照。

本轮只作归档、技能维护和推送检查；没有重跑游戏/视觉/联机测试。公开裁剪树没有重新构建，不能把历史完整本机构建记作本提交的编译证明。发布范围与内容校对见 `publication-manifest.json`，本机完整交付回执位于 `SourceAssets/KaitlinCompletion20261024/delivery.json`。
