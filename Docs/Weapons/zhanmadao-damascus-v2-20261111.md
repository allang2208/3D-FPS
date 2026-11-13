# 斩马刀大马士革钢 V2（2026-11-11）

当前美术方向已按用户提供的两张参考图改为 [参考图修订 V3](zhanmadao-damascus-reference-v3-20261111.md)。下文保留 V2 的初次制作和固定种子接入记录；纹理与表面参数以 V3 记录为准。

本轮按用户确认方案覆盖全部 8 款斩马刀刀身：三类锻纹、每把武器固定变体、低反差钢层、浅蚀刻与分区磨抛。保留原生装饰色、11 月 10 日确定的中段符文布局和现有改造属性。

| 刀身 | 锻纹 |
| --- | --- |
| 原厂、加长、赤霄、逐风 | 流水层纹 Flow |
| 厚脊、腾云游龙 | 扭绞回流 Twist |
| 轻刃、破锋雁翎 | 羽状层纹 Feather |

## 表面制作

`SourceAssets/ZhanmadaoDamascus20261111/author.py` 原创生成 3 张 1024×4096 纹理数据图，每张表示 12×176 cm 的连续纹场。R 存放钢层混合，GB 存放浅蚀刻坡度，A 存放低频磨抛变化。按线性 BC7 导入，启用平均 mip 和流送；普通与时停材质共享相同纹理。

流水采用纵向长层纹；扭绞在连续层纹中加入疏密不一的局部折返；羽纹围绕柔和中心线形成斜向汇合。固定种子控制采样位置、小幅密度变化、横向扰动与蚀刻明暗，羽纹的横向变化限制在中心轴附近。

从 8 款当前 FBX 的实际截面制作独立的 `profiles.json`，拟合刀身中心、宽度、累计弧长与磨抛方向。坐标计算放在顶点阶段，纹样使用实际厘米尺度。网格、原 UV、结构法线不重导。

新表面降低旧版深灰／银白层的底色反差，以粗糙度差异、浅蚀刻和沿刀弧的定向反光表现钢层。刀面接近缎面抛光，边缘细化，侧面更平静。以上为制作参数，尚无游戏内视觉验收。

## 装饰与符文

- 复用当前原生色图／ORM 的装饰遮罩，分别保护红带、金饰及逐风青色。
- 遮罩同时控制 BaseColor、Roughness、Normal、Metallic、Anisotropy、Tangent。
- 独立黄铜材质不参加本轮替换。
- 现有 RuneTexture 节点、图案比例、投影位置、语义配色及发光保持；使用原符文覆盖度轻微降低其下方钢纹反差。
- 普通与旋风时停表面都接入 V2；保留时停材质自身的渲染设置。已有时停切换通过 `CopyMaterialUniformParameters` 传递种子。

## 固定变体与生命周期

`ColdSteelModularSword::BladeFinishSeed` 从已保存的物品 `InstanceId` 派生 24 位整数，作为可被材质浮点数精确表示的 `DamascusSeed`。空 ID 的目录预览使用定义 ID 得到确定的默认外观。无新增随机重抽、每帧写参数或物品存档字段。

装配入口把种子传到材质；视觉缓存键包含种子，避免两把同配置武器共用错误的外观。`FFPSBodyAttachment.BladeFinishSeed` 随现有反射外观快照携带，第三人称材质重建与外观缓存使用同一值。

源码涉及 `ModularSwordVisual.h/.cpp`、`FPSPlayerBodyTypes.h`、`FPSBodyRuneVisual.cpp`。本轮改变了反射结构，需常规 `FPSGAMEEditor` 构建；单独保存材质不能替代这一步。

## 制作入口与保存范围

- 原创纹场与截面：`SourceAssets/ZhanmadaoDamascus20261111/author.py`。
- 材质配方：同目录 `materials.py`，仅作用于斩马刀 V2 分支，移除原共享材质中的旧大马士革计算。
- 接入：`install_assets.py`，按当前目录解析 9 个实际刀身材质槽及 9 个时停配对，目标共 18 个材质与 3 张纹理。
- 材质中的新纹理位于 `/Game/Weapons/Zhanmadao20261018/Damascus20261111/Textures`。
- 刀身重制入口通过 `DaoLongitudinal20261110/rune_material.py` 接续已安装的 V2；共享表面安装器也接入 V2，保留后续重建顺序。
- 修改前资产备份保存在本目录 `BeforeAssets`。安装和构建结果分别记录在 `material-receipt.json` 与 `build-receipt.json`。

## 交付状态

纹理源、刀身截面、材质脚本和固定种子源码已完成。常规 `FPSGAMEEditor Win64 Development` 构建成功，退出码为 0，记录见 `SourceAssets/ZhanmadaoDamascus20261111/build-receipt.json`。

正式资产已通过后台 commandlet 保存：全部 8 款刀身、18 个普通／旋风时停材质、3 张纹理，合计 21 个资产；`material-receipt.json` 中 `complete=true`，材质编译错误记录为空。接入进程退出码为 0，日志为 `install_assets-20261111-182817.log`。本轮沿用原材质路径接入，现有改造表的属性与引用无需替换。

本轮不启动游戏，不执行测试、预览渲染或截图；外观与联机效果交由用户测试。
