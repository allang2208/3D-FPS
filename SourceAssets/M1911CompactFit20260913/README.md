# M1911 展示姿态与配件尺寸修订（2026-09-13）

用户要求改造面板显示套筒闭合的正常状态，并按手枪尺寸重新适配所有实体配件。

## 游戏接入

- `FPSGAMECharacter::UpdateActionPose` 在枪匠编辑当前装备的 M1911 时使用正常待机/瞄准基础姿态，并屏蔽动作叠加。只改变显示；不改弹药数量、换弹结算、动作计时或存档。关闭枪匠后重新使用真实空仓/动作状态。
- 全息、全景红点、消音器通过 `M1911WeaponAssets::AttachmentPath` 使用 `/Game/Weapons/M1911/CompactFit20260913/Meshes`。
- 激光和手电通过 `TacticalDeviceComponent` 使用同目录的 `laser` / `flashlight` 子目录。角色、枪匠草稿、库存展示、未装备展示与掉落继续共用装配入口。
- 新目录已加入 `DefaultGame.ini` 的 AlwaysCook。扳机和长短枪管仍为已有数值改造，不增加实体模型或改变属性。

## 尺寸及衔接

| 部件 | 本体修订 | 接口修订 |
| --- | --- | --- |
| 全息 | 原主体的 55% | 56 × 31 mm 薄座，双侧底脚按当前套筒曲面制作 |
| 全景红点 | 原主体的 62% | 38 × 35 mm 薄座，保留原照门的避让空间 |
| 消音器 | 筒体长 130.2 mm、外径 34 mm | 12 mm 接头、保留 13 mm 开口，接头根部衔接原枪管外径 |
| 红色激光 | 原主体的 70%，长度约 59.8 mm | 26 mm 曲面安装座，尾端停在扳机护圈前方 |
| 手电 | 原主体的 72%，长度约 86.4 mm | 独立曲面座，灯头移至接近枪口端面 |

瞄具挂点为枪根作者空间 `(0, 0.030, 0.0495)` m，比前版降低 4 mm、前移 2 mm，继续随 `WPN_Slide`。光学中心随各自主体比例更新。

消音器挂点为枪根作者空间 `(0, -0.16787465, 0.02898)` m，继续随 `WPN_Barrel`。导入后的消音器轴为 **UE -Y**，原代码误用 +Y；本次已修正安装方向及出口 `(0, -13.02, 0)` cm。战术设备保留自身导出的 `Emitter`、`AimGuide`，随 `WPN_root`。

## 几何与材质来源

复用现有全息、全景红点、消音器、激光，以及已选定的混元手电主体。保留原 UV0、光学/橡胶/标识分区；几何缩放后重新投射 10 cm 物理尺度的枪钢 UV。瞄具 UV3、消音器 UV2、战术设备 UV1 与原材质保持一致。

UE 继续绑定 `M1911/Attachments20260913/Materials` 和 `M1911/Tactical20260913/Materials` 中的现有 M1911 枪钢材质，沿用已登记的湿润/雨滴映射。没有覆盖共享步枪资源、当前 M1911 主体或天气库。

源资产及许可记录继承 `M1911Attachments20260913`、`M1911Tactical20260913`、`TacticalDevices20260913` 的原始来源；本次没有新增外部模型或重新授权公开分发。

## 可编辑文件与制作入口

- `M1911_CompactFit_Assembly_Editable.blend`：当前枪体和五种安装后的可编辑备选件。
- `M1911_CompactOptics_Editable.blend`：瞄具与消音器的独立网格。
- `laser/`、`flashlight/`：各自 FBX、带材质的可编辑 Blender 源。
- `author_optics_muzzle.py` → `author_tactical.py` → `assemble_editable.py` → `import_meshes.py`。
- `optics_authoring.json`、`tactical_authoring.json`：制作尺寸与接口；`installed.json`：导入资源与材质路径。

按照用户规则，本次只进行制作、导入与必要编译；未运行游戏、自动测试或验收渲染，视觉与操作效果交由用户测试。导入命令行存在工程已有 GameFeatureData / MCP 8000 端口错误，五个网格的导入保存步骤已完成；这不表示运行验收通过。

必要 Editor 构建完成，模块为 `UnrealEditor-FPSGAME-913210025.dll`，构建日志为 `build-editor.log`。没有关闭或重启用户编辑器；重启编辑器后加载本次原生改动。
