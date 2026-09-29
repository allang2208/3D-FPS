# 病区药物推车与输液架

接入独立病区 `L_AbandonedIsolationWard_Subject`。房池注册不变。

## 资源与交互

- 药车母资产：`/Game/Props/MedicalCart20260929/SM_Hospital_MedicalCart`。
- 病区药车：`/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_MedicalCart`。原模型整体高度约 136 cm，病区派生版采用 0.82 倍，整体约 112 cm；顶部柜台处于现有 120 cm 翻越范围内。保留原始导入母资产、原贴图和材质分区。
- 药车由柜体、托盘、轮架等源几何制作 61 个凸碰撞体，使用 `QueryAndPhysics / BlockAll`，允许 StepUp，不模拟物理。玩家通过现有 `FPSTraversalComponent` 的空间、接触与落点判定进行翻越，不新增按键、提示或另一套攀爬规则。
- 输液架母资产：`/Game/Props/IVDripCrutch20260929/SM_Hospital_IVDrip_Crutch`。
- 病区输液架：`/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_IVDripCrutch`。保留输液架和拐杖组合、原尺寸；不导入简单碰撞，实例明确设置 `NoCollision`，不影响导航。

## 随机生成

扩展现有 `AWardBedScatter`，不添加相互独立、无法共享占用数据的生成器。原生类仅在开始后的下一帧生成一次；每次重新指定种子时清理既有小件实例。

1. 先按现有规则完成所有病床摆放。
2. 每间病房药车随机 0–1 台、输液架组合随机 0–1 组，两件道具均保持直立并随机水平朝向。五间病房的小件最多 10 件。
3. 用旋转后的可见网格完整包围盒筛选房间内部、门口活动区、既有过道以及家具之间的间隔，并沿用世界阻挡查询。
4. 药车与既有物体至少保留 100 cm 的轴向包围盒间距；输液架至少 80 cm。床间原有 110 cm、墙边 65 cm 的规则保留。
5. 无碰撞的输液架同样写入公共占用记录；后续实例不能穿过它的可见边界。每件目标最多 48 次尝试，空间不足少放，不强塞，不在 Tick 中继续重试。

目前仍使用病区已有的单机运行和随机种子约定，没有新增多人同步协议。

## 作者入口与交付

`SourceAssets/DungeonIsolationWard20260929/MedicalProps20260929/`：

- `author_props.py`：从现有 FBX 制作派生模型与碰撞；不渲染。
- `prop_design.py` / `update_config.py`：房间配置和模块草稿。
- `import_assets.py`：实际导入、继承材质、保存；保留源网格。
- `save_map.py`：正式构建后配置原有病床生成 Actor 并保存地图。
- `install.py`：两步安装入口。
- `Receipts/assets.json`、`Receipts/map.json`：实际保存状态；缺少对应回执就不视为该阶段完成。

`prepare_design.py`、`configure_ward_beds.py` 和整房安装脚本同步维护这些引用。本轮正式构建日志：`Saved/BuildEditor/build-20260929-212404.log`。

未运行 PIE、游戏、渲染或验收测试；实际翻越手感和分布由用户测试。

## 来源署名

以下载包内 `license.txt` 为准（导入回执中的旧作者名称与其不一致）。

- “Rusty medical cart”，CarlosTorresVFX，CC-BY-4.0。源页面：<https://sketchfab.com/3d-models/rusty-medical-cart-508d17d0d77c4d10a3a9ddc043241d31>。
- “Crutch and IV Drip”，Matt LeMoine，CC-BY-4.0。源页面：<https://sketchfab.com/3d-models/crutch-and-iv-drip-5cc65c6aed374220b67f7d60e679153e>。

派生资产的 `SourceCredit` 保留下载包完整署名文字；未发布或上传资源。
