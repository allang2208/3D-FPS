# 大弹鼓模型升级 · 2026-09-20

根据用户提供的正面、背侧两张照片制作游戏配件外观。更新现有 `large_drum`，不新增配件 ID，不改容量、数值、弹药结算或换弹动作。

## 外形与材质

- 重新制作圆角鼓壳、较平的上肩、分层端盖、环形凹面、壳体分缝、背面浅凹面板、上沿锁扣和供弹颈下部支撑。
- 保留 M4、AKM、QBZ-191 各自当前模型的上部入枪接口、装配坐标和枢轴；沿用原来的角色、枪匠展示与换弹掉落加载入口。
- 主体为深色注塑聚合物，锁扣销轴为对应枪型的涂层钢件。每枪独立 2K BaseColor、MetalRough、Normal；MetalRough 的 G 为粗糙度、B 为金属度、R 未使用。没有宣称包含 AO 烘焙。
- 新模型采用自己的 UV0、几何倒角与微表面法线，Blender OpenGL 法线在 UE 导入时翻转一次绿色通道。金属响应沿用此前已制作的各枪涂层采样参数；不是原 Phong 母材质的逐像素复制。
- 移除四根突出竖条后，每个作者低模 17,238 三角面。UE 中生成三个 LOD（1 / 0.55 / 0.25）和最多三个简单凸包。
- 干湿材质使用既有 `WeaponWetness` 水膜/水珠规则，新增映射合并至 `DA_WeatherPresentation`，其他映射保留。

照片中的遮挡面和深度由本次制作补全。此资产是视觉外壳，没有制作内部供弹机构，也不用于实物制造。

## 实际替换的资产

| 枪型 | 保留的运行资源路径 |
| --- | --- |
| M4 | `/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum` |
| AKM | `/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum` |
| QBZ-191 | `/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_drum` |

三份网格保留原材质槽数量与运行槽名，绑定各枪新的完整材质图集。QBZ 旧 FBX 导入材质名与运行槽名不同，重导入过程中对新旧槽进行了显式映射，随后重新生成 LOD。

没有改动 `M4DrumVisual.cpp`、枪型启用条件、挂点变换、动画或目录数据。这里列出的是被升级的既有资源路径，不代表重新测试了每个运行分支。原有跨枪加载逻辑保持当前项目行为。

正式新材质和纹理位于 `/Game/Weapons/LargeDrumUpgrade20260920/<枪型>/`。它们由已在 Cook 范围内的原运行网格引用，无需新增 C++ 路径或编译。

## 可编辑交付与入口

- `Reference/user_front.png`、`user_rear.png`：用户原始参考。
- `Reference/current_assets.json`：本次读取的当前资源与材质绑定。
- `Reference/<枪型>_current.fbx`：替换前的编辑器导出。
- `Source/OriginalDrumInterfaces.blend`：原三枪接口，在共同作者坐标下保留。
- `<枪型>/Drum_Construction.blend`：可独立编辑鼓壳、端盖、锁扣和筋条。
- `<枪型>/Drum_Editable.blend`：表面母版、游戏网格和已打包材质贴图。
- `<枪型>/Drum_Integrated.blend`：已写入原资源坐标的导出模型。
- `Export/SM_<枪型>_LargeDrum_Upgrade.fbx`：正式引擎导出。
- `Icons/<枪型>_DrumIcon_Editable.blend`：正式枪匠图标的可编辑源。
- `Scripts/prepare_inputs.py` → `author_drum.py` → `bake_export.py` → `install_assets.py`；图标由 `render_icons.py` → `install_icons.py` 制作和接入。

图标采用实际新模型、水平左向正交侧视、1024×1024 透明 PNG。M4 更新共享回退图，同时 M4/AKM/QBZ 各有专属覆盖图；没有额外生成验收渲染。

## 备份与交付边界

旧网格已保存至 `/Game/Weapons/LargeDrumUpgrade20260920/Before/`，原 FBX、源路径与旧图标同时保留。本次未删除旧制作链，也未更改用户装备或存档。

导入/保存回执：`import_receipt.json`；图标安装回执：`icon_install_receipt.json`。脚本续作依据回执跳过已保存部分，不能把回执当成实机验收记录。

已通过运行中的 UE 编辑器完成资源替换和保存；没有原生代码改动，本任务未触发编译或重启。制作期间编辑器由外部操作重新打开并进入 PIE，最后为完成图标保存结束了该次 PIE，保留编辑器打开。本任务未启动 PIE、未做游戏测试、手部接触验收或打包测试，由用户自行测试。

## 2026-09-20 竖条修正

按用户截图，仅删除供弹颈上方左右各两根 `Tower external longitudinal rib`。M4、AKM、QBZ-191 的分件源文件、表面母版、游戏网格、FBX 和正式图标同步更新；其他几何、原 UV、贴图、角点法线、材质与游戏属性保留。作者生成脚本同时取消这四根竖条。

使用 `Scripts/remove_tower_ribs.py` 删除已有独立部件，复用原贴图；`Scripts/render_icons.py` 更新正式图标，`Scripts/install_rib_removal.py` 在打开的编辑器中重导入并保存。本次模型编辑与安装回执保留在修订目录。带竖条的旧源文件、旧图标备份已移至项目根目录 `trash/attachments-grip-drum-20260920/SourceAssets/LargeDrumUpgrade20260920/`；`Reference/*_current.fbx` 与 `Source/OriginalDrumInterfaces.blend` 仍是制作依赖，保留原位。未启动 PIE 或进行测试，由用户自行测试。
