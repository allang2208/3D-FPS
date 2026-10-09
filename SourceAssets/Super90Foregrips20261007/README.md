# Super90 通用前握把

为 `ue_super90` 接入现有五种通用前握把：垂直、战术垂直、45°侧倾、棱镜阻手器、共振二代。

## 制作内容

- `Exports/`：保留通用握把主体比例、UV 和材质分区，加入贴合原装护木底部的曲面安装座和下导轨。资产固定在原生 `WPN_root`，组件坐标安装点为 `(0, -16, -80.15)` cm。
- `Profiles/`：四个 `WeaponGripProfile` 的生产 JSON 与可编辑 Blender 文件，两款垂直握把共享垂直握姿。手掌和手指沿用已认可通用握姿，转换到 Super90 原生骨轴；保留各关节长度，把腕部旋转分配到原生前臂辅助骨。
- 每个姿态层覆盖 12 个现有源动画，包含 idle、walk、run、fire、fire_last、equip、inspect、quick_melee、reload_one、reload_full、reload_empty、reload_continuous。ADS 使用原生 idle/fire，因此沿用同一套握姿层。
- 原动作由右手装填，左手持枪。姿态层仅修改左臂，不改动枪身、右手、弹壳、枪栓或装填时钟；连续换弹的侧倾和跳过空余装填循环逻辑保留。
- 枪匠沿用现有通用配件 ID、属性和实例存档链路；卸下握把销毁对应组件，恢复原装护木姿态。

## 生产入口

1. `export_inputs.py` 在后台 commandlet 读取已保存原生骨架和动画，供制作使用。
2. Blender 后台执行 `author_assets.py`、`author_profiles.py`。
3. `Tools/ModularOutfit/Run-Authoring.ps1` 执行 `import_assets.py`，保存 `/Game/Weapons/Super90/Foregrips20261007` 下的网格、材质和姿态层。
4. `publish_catalog.py` 仅更新 Super90 的 underbarrel 选项；`Tools/Build/Build-Editor.ps1` 编译。

通用配件原始来源保留在 `models.json` 和 UE 资产元数据。Super90 枪身、贴图、骨架及现有动画资产未在本批次重新导入。

未进行游戏运行、截图、渲染或自动验收，由用户测试。生产落盘情况见 `import_receipt.json`，目录接入情况见 `catalog_receipt.json`，构建情况见 `build_editor.log`。
