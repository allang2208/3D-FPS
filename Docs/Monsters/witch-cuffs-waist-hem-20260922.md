# 巫婆袖口、腰部与近地裙摆 Seams07 / Drape07

用户报告袖口破碎、上下衣衔接断层及近地衣物细节问题。本轮仅处理这些衣物区域，保留角色尺寸、人体、抓握/投掷及其余动作。

## 排查与调整

- 袖口问题包含实际碎裂轮廓，单降法线强度无效。移除原上衣远端袖子的 3,476 个顶点，重新制作连续袖管、宽缓褶皱和约 2.5 mm 的内翻袖口；上端搭接到保留衣层，权重沿肩、肘、前臂 twist 和手腕连续过渡。原布料贴图中的破损图案不再投射到新袖管上，新旧表面以顶点 Alpha 区分，保留织物细节法线。
- 旧内衬在腰上方突然结束，形成明显横向截面；原上衣腰口与下袍还使用不同的模拟活动范围。替换该处短内衬，制作覆盖腰腹、藏入上下衣层的连续褶皱过渡面。下端与下袍共同使用骨盆权重，上方平滑混入脊柱；上衣模拟在骨盆以上 8–20 cm 渐入，接缝区域固定。
- 原袖口按距手骨 5.5 cm 的球形范围固定，宽袖口会落在范围之外。改为沿前臂方向的最后 6.5 cm 固定区域，并保留合理径向限制，避免边缘单独飘开。
- 下摆在源姿态约 11.3 cm 高度修除拖地细尖片，边缘做毫米级起伏和薄折边，收回局部外扩拖尾。底部代理随显示边界调整，近地模拟位移上限由最高 45 cm 渐限至约 24 cm；不将连续裙摆绑到左右脚骨。
- 模拟网格仍为 1,704 点，保持 Drape06 的迭代和自碰撞预算。未重新测量本版性能，不把上版约 1.7 ms 的结果写成本版结果。

## 源文件和接入

- 可编辑母版及八个动作场景：`SourceAssets/WitchRebuilt20260921/Authoring`。仅更新场景中的衣物网格，未重新制作动画键。
- 两份网格 FBX：`SourceAssets/WitchRebuilt20260921/Delivery/SK_WitchRebuilt.fbx` 与 `SK_WitchRebuilt_ClothBuildSource.fbx`。
- 原版备份：`SourceAssets/WitchRebuilt20260921/Revision07/Before`。
- 制作：`Tools/WitchRebuilt/author_seams07.py`；材质：`install_surface07.py`；接入：`import_seams07.py`。
- 原生固定区域：`Source/FPSGAME/Monsters/WitchRebuiltAuthoring.cpp`，新布料名 `WitchRebuilt_LowerDrape07` / `WitchRebuilt_UpperDrape07`。有界显示绑定及原角色缩放不变。

## 检查范围与当前状态

按用户“排查”要求读取源网格、骨骼位置及相关绑定代码，并查看正反面制作渲染，定位和调整局部边界。`Revision07/source07_front.png`、`source07_back.png` 是源蒙皮画面，不包含 Chaos 模拟，也不是游戏截图。

接入中的 Live Coding 同时包含当前工程其他待编译的类型变化，结束 PIE 时编辑器崩溃。调用、重载与崩溃片段保存在 `Revision07/compile_live02.txt`、`live_compile_crash_excerpt.txt`；不能仅凭该日志确定具体故障对象。随后改为常规 Editor 构建。第一次常规构建被武器图标模块声明/实现的临时不一致阻挡，该模块在后续读取时已有新的实现，本任务未修改它。

在没有 PIE 和未保存包时正常关闭编辑器，常规构建最终成功：`Saved/BuildEditor/build-20260922-162333.log`，随后重新打开 UE。没有修改武器图标模块。

UE 导入和保存已完成：`Revision07/import04.txt`、`ue_asset_result.json`。实际保存的网格包含 `WitchRebuilt_LowerDrape07` / `WitchRebuilt_UpperDrape07`，上衣使用 `M_WitchRebuilt_UpperFabric07`。网格重导入显式覆盖 FBX 顶点色，源文件导出显式选用活动颜色层，保留新旧布面的 Alpha 材质分区。动作资产未重导入。

重启接入期间前几次调用未找到节点或未建立远程连接，尚未执行导入；最终调用完整完成，没有重放结果不明的资产写入。当前 UE 保持打开。本轮没有启动 PIE、动态布料或战斗测试；按此前授权结束了接入前的试玩，最终视觉效果交由用户测试。F6 → 怪物生成 → 巫婆·重建候选，重新生成可使用本版。
