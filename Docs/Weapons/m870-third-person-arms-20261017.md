# M870 第三人称武器副本的手臂剔除

用户反馈：第三人称使用 M870 时，枪上仍出现第一人称手臂。

## 原因

后台读取当前 `/Game/Weapons/M870/Tactical20261015/SK_M870_V7` 后，确认材质槽 1、2 为 `MI_Super90JointSkin_Arms`、`MI_Super90JointSkin_Arms_2`，槽 3 为 `MI_Super90JointSkin_Hands`。

通用家具接入用 GeometryScript 重写材质表时，将原先 `Manny_M870_*` 显示槽名替换成了导入材质名。`CaptureWeapon` 的旧剔除规则仅能识别其中的手部，漏掉两段手臂。

实际模型读取记录：`Tools/Weapons/M870ThirdPerson20261017/material_slots.json`。读取过程没有保存或修改模型资产。

## 修改

- `FPSPlayerBodyEquipment.cpp`：补充带边界的 `_Arms`、`_Arms_*` 名称识别，同时依据网格原始材质名称识别手臂，避免仅依赖可被重写的显示槽名。
- 仍通过现有 `HiddenMaterials` 传递给第三人称武器副本；现有生成与动作材质可见性刷新会在所有 LOD 应用该列表。
- `SourceAssets/M870CommonFurniture20261016/install.py`：新建原厂家具分区时恢复原有材质显示槽名。

第一人称原始网格、手部姿势和动画无需重导入。枪体、弹壳及原厂家具仍走原有的可见性规则。

## 交付边界

后台 `FPSGAMEEditor Win64 Development` 构建返回 `Succeeded`（当前目标已是最新，无需重复编译）。记录保存在 `Tools/Weapons/M870ThirdPerson20261017/build_editor.log` 与 `Saved/BuildEditor/build-20261017-084028.log`。

本次没有修改或保存模型／动画资产，不启动游戏，不进行第三人称画面或联机验收，由用户体验。
