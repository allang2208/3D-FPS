# M24 共用脚架与联机修复发布

目标：`https://github.com/allang2208/3D-FPS.git` 的 `main`。本批发布共用部署判定、镜头限位、M24 展开／收架交接、实例绑定与拥有者确认修复，以及对应 SKILL。没有发布本机其他并行功能。

## 源码范围

- 完整发布 `WeaponBipodDeploymentComponent.cpp/.h`、`M24BipodValidation.inl`、`M24Bipod.h`、`PKMBipodComponent.cpp/.h`。远端此前的 M24 接入资料以历史补丁保存，本批把脚架必需的组件实现补入正式源码。
- 共享 `FPSGAMECharacter.cpp/.h` 只纳入 M24 型号识别、检查夹具 friend、收架后换弹、ADS 显示权重、手部姿态调用及拉栓未结束判定；不提交整份混合工作文件。
- 共享 `FPSGAMEPlayerController.cpp/.h` 仅纳入部署维持所需的面板继续动作接口；既有库存／枪匠等面板占用新输入与维持已有动作分开处理。
- 更新个人 SKILL 与工程参考。工程入口仅提交本批新增导航，不夹带入口中其他未提交条目。保留原共享索引中其他功能的暂存差分。

## 资产与恢复边界

本批不分发 UE 包、模型、密集动画、DLL、完整构建日志或玩家存档。完整本机项目与有权使用的已保存 Content 仍是运行条件；之前的 M24 目录、枪匠与宿主接入边界见 `Docs/Publication/M24_20261101/README.md`。本批不是整个项目的干净检出构建验收。

必须保留的本地资产包括 `/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9`、`/Game/Weapons/M24/ContactRepair20261101/DA_M24_Bipod`、`/Game/Weapons/M24/Bipod20261029/SM_M24_Bipod_Base` 及两条支腿。普通／扩容弹匣的两条手部 clip 由该握持 Profile 提供。没有修改当前认可的换弹手型或重新导入动画。

新的部署 RPC 和复制结构包含武器实例，主客机必须使用同版本模块。

## 归档与证据

17 个废弃探测文件、SDK 阻塞启动日志及被替代源码快照，共 333,883 字节，已移入 `trash/m24-bipod-20261103/`。原路径、目标、原因、替代物、大小与 SHA-256 见 `archive-manifest.json`；读回结果见 `archive-receipt.json`。全部为可恢复移动，无永久删除；`trash` 不进入 Git。

正式源码、成功检查脚本、74 项原生结果、构建／执行日志与交付回执保留于原 `Saved/M24BipodNetworkReview20261103/`；上一轮成功证据保留于 `Saved/M24BipodParity20261103/`。本批精简历史证据位于 `HistoricalReceipts/`。

2026-11-03 的本机 Editor 正式构建成功，74 项单进程原生检查通过。网络分支直接调用处理函数，未实际发送网络包；真实主客机延迟、丢包、晚加入与远端画面仍未覆盖。本次归档、文档与 Git 发布没有重跑 UE 或游戏测试。发布前核对限定为依赖／调用点、暂存差异、空白、文件大小、敏感信息与许可边界。
