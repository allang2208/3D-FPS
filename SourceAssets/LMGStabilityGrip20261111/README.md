# 机枪稳固握把 / M249 无握把原厂

## 交付设计

- 配件 ID：`lmg_stability_foregrip`，占用 `underbarrel`，特殊改造。
- 共用范围：`ue_m249`、`ue_lmg201`、`ue_pkm_lowpoly`。
- 常驻后坐力-15%、枪械稳定性+15%，开镜耗时与空槽相同。连射从首发起线性累积，1.5 秒时后坐力合计-30%，枪械稳定性额外+15点，上限沿用100点。停火清空连射加成。三个武器共用目录和装配存档，连射进度只属于当前持枪动作。
- M249 空槽改为“无前握把”，隐藏内嵌原厂前握把；工厂装配配方移除该零件。旧空槽保持空槽，不自动赠送新件。
- M249 安装新件使用原先已认可的 SupportGrip 姿态。无握把另用新 Handguard profile，不覆盖原 profile。201、PKM 分别使用新 Stability profile。

## 模型与动画制作边界

握把主体取自 `M249Orpind20261107/M249_Editable.blend` 的原厂前握把，保留主体尺寸、外形和 UV。201、PKM 使用各自下导轨的安装位置与闭合连接座，不通过拉伸主体补足距离。

新姿态仅修改左臂及手指的局部旋转，保留原手模、权重、骨长、局部位移和缩放。M249 无握把使用 `handguard_target.json` 中的托握手型，M249 稳固握把沿用已认可的 Wrist38。离握与回握沿用 GripLayer56 的接触过渡。201 和 PKM 换弹期间用 Wrist36 的肩肘约束减小腕折。PKM 开盖时，左手沿同一盖缘移向铰链以避开镜头，窗口结束后接回原弹链接触。右手和机械轨道继承原 profile。

远端身体、世界武器的快照沿用公共附属组件通道，并补入原厂前握把隐藏材质段。新增资源进入装备预载；UI 新件沿用原握把图标，空槽使用统一减号图标。

## 重建入口

1. `collect.py`、`collect_motion.py` 从当前保存资产读取制作输入，不运行游戏。
2. `prepare_contacts.py` 计算当前关节接触；Blender 后台运行 `author_geometry.py` 输出三个主机适配件。
3. 系统 Python 运行 `author_profiles.py` 生成三个新 profile。可传 `M249`、`LMG201`、`PKM` 单独制作。
4. 在 UE 批次互斥下使用 Python commandlet 运行 `install.py`，导入并保存模型、profile 和图标。`install_receipt.json` 记录实际保存的资产。
5. `publish_catalog.py` 在资产保存完成后发布共享目录、M249 空槽和原厂配方。重新运行旧版 M249 目录生成器后，也应再执行该脚本。
6. 正式编译使用项目 `Tools/Build/Build-Editor.ps1`。编辑器必须保持关闭，不主动停止用户编辑器。

## 初版保存与构建

- `install_receipt.json`：10 个资产已保存（3 个模型、3 个姿态配置、4 个图标纹理）。
- `catalog_receipt.json`：共享改造、M249 原厂空槽及装配配方已发布。
- `build-final-2.log`：正式 Editor DLL 编译、链接成功，对应 `Saved/BuildEditor/build-20261111-183059.log`。
- 初版交付时未运行游戏。后续按用户要求进行的实拍和联机检查存于 `Review02/WireRuns`。每轮独立保存主机与客户端数据，`host.json` 包含双端用例，`client.json` 包含客户端用例。

## 关节修订

`Review02/install_support.py` 通过后台 commandlet 保存姿态，`Review02/support_install.json` 记录本轮资产哈希。`Review02/scope.py` 用引擎读回的 40 段动画核对局部平移、缩放和左臂之外的关节，并核对 M249 源网格和 Wrist38 的哈希。手感由玩家实机验收。
