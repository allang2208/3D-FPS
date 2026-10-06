# RSH 紧凑瞄具修订

重建 RSH 的 `holographic` 与 `eoth_holographic` 镜体和直接夹座。前者采用开放式短镜框，后者采用短封闭保护罩。移除原有步枪镜体的长电池盒与叠加导轨结构，保留配件 ID、属性和通用图标。

## 制作源与接入

- `author_optics.py`：Blender 后台精确建模，输出两个可编辑 `.blend` 与四个 `.fbx`。
- `authoring.json`：制作参数、导出路径、分区材质与光学挂点。
- `import_assets.py`：保存两款瞄具、夹座、私有消光材质和天气注册。
- `publish_catalog.py`：仅更新 RSH 的两条瞄具描述。
- `BeforeAssets/`、`BeforeCatalog/`：首次导入与发布前的本地恢复副本。

建模坐标为已测量的 RSH `2_l` 导轨框架，+X 朝前；夹座沿用该导轨的肩面与横槽接触点。镜体与夹座分开导出，镜体顶点和 ADS 挂点同时烘焙既有 `RSH12OpticAssets::OpticMount` 偏移的逆变换。保留当前已部署的组件位置、固定 `WPN_root` 挂接和资产路径，C++ 无需变化或重编译。

四个运行资产仍位于 `/Game/Weapons/RSH12/Optics20261004/Meshes/`：

- `SM_RSH12_holographic`、`SM_RSH12_Rail_holographic`
- `SM_RSH12_eoth_holographic`、`SM_RSH12_Rail_eoth_holographic`

外壳与夹座沿用 RSH 导轨采样的金属材质，新增 UV 按物理尺度投射，不套用步枪镜体图集。内壁、密封件与按键使用私有消光材质；透明镜片和抗锯齿环点分划复用项目通用光学材质。分划平面独立设置尺寸，未随镜体整体缩放。

ADS 使用已有 `SightRear`、`SightFront`、`SightUp` 插槽入口，`AimCenter` 与分划中心一致。现有背包保存、配件预加载与运行装配通过原资产路径取得修订。旧版初始导入及缩放修订入口均会转交本目录处理这两款，避免后续重导恢复旧造型。

这是游戏内紧凑适配造型，并非实物型号复刻。原始建模由本任务制作；导轨适配依据 Rsh-12 / Medji / CC BY 4.0。

## 执行状态

模型、四个运行网格、消光材质、天气注册及四组 ADS 挂点已后台导入保存，RSH 两条瞄具描述已发布。最终保存回执为 `import_receipt.json`，命令行记录为 `Import-commandlet-05.log`。FBX 重导保留旧公开槽名时，以 editor-only `imported_material_slot_name` 绑定新材质，并处理本批原有槽名；外壳不再采旧步枪 UV 图集，分划复用清晰环点材质。

这轮瞄具接入沿用现有 C++ 路径和挂接，不需要原生改动。期间另行修复了用户报告的 RSH 双持换弹循环，源码与基础 DLL 状态见 `Docs/Weapons/rsh12-dual-reload-fix-20261004.md`。未运行游戏测试、预览或截图，未主动打开编辑器，最终外观由用户测试。
