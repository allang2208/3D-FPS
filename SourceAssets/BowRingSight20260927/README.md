# 弓细杆圆环瞄具 V17（2026-09-27）

按用户要求在 Blender 重新建模：细木杆从弓体伸出，闭合圆环中央为从下方上伸的竖向准星。原弓及三款改造弓体的安装区域一致，瞄具继续使用独立 `sight` 改造槽。

## 形体与材质

- 圆环外径 3.44 cm、内径 2.96 cm；支杆主体直径 0.35 cm。
- 竖杆尖端坐标沿用弓局部 `(-3.5, -10.1, 16.5)` cm，实际顶端用于 ADS 对位。
- 木座沿原弓的实际表面拟合，Z 范围 14.65–18.35 cm，边缘压薄并略埋入原木表面。
- 支杆根部加宽，再渐细成杆；使用精确布尔和局部圆角形成连续衔接，环和竖杆保持规则轮廓。
- 两道细亚麻绑线、两个齐平木销构成安装细节。圆环不加玻璃、不发光。
- 导出模型为 16,628 个三角面、3 个材质槽。
- 木纹、粗糙度和法线取自工程已使用的 WoodLongbow 贴图。木纹沿杆身及圆环走向铺设；木座使用原弓表面 UV。材质为新资产，不修改原弓材质。法线力度降低至 0.35，粗糙度下限 0.50。

几何为本次原创；木纹来源与许可沿用 `SourceAssets/DarkBow20260925/WoodLongbow20260925` 的记录，不新增外部素材。

## 作者源与入口

- `Bow_FineRingSight.blend`：可编辑源，包含最终网格及隐藏的 `EDITABLE_CONSTRUCTION_UE_cm` 原始木座、杆、环、竖杆。贴图已打包。
- `Export/SM_Bow_FineRingSight.fbx`：厘米制导出，采用既有弓的 FBX 坐标约定。
- `author_sight.py`：Blender 后台建模与导出；`authoring.json`：制作参数记录。
- `prepare_pipeline.py`：生成当前导入与后台构建入口。
- `run_import.ps1` / `import_assets.py`：导入并保存 UE 网格和三份静态材质，互斥等待已有批次。
- `run_build.ps1`：必要的 FPSGAMEEditor 原生构建，不打开 UE。
- `install_config.py`：保存资产后更新默认模型、改造槽、ADS 距离和 cook 目录。

UE 目标目录：`/Game/Weapons/DarkBow20260925/RingSightV17`。

## ADS

完整弓、双手、弦与箭共用原有瞄准变换：实体准星距相机从 75 cm 改为 67 cm，整体向相机移动 8 cm。保留 FOV、开镜时长、箭矢指向校正、V15 形变和 V16 快速搭箭。拆除瞄具选项的沿箭杆 ADS 也缩短 8 cm。

目录表现版本提升到 28；旧官方瞄具通过既有迁移更新，保留自定义模型及已选改造件。未直接改写玩家存档。

## 交付边界

以 `import-receipt.json`、`install-receipt.json` 和 `Saved/BowRingSight20260927/build-editor-v17.log` 记录实际执行结果。源码备份位于 `Saved/BowRingSight20260927/Before`。

按用户规则不启动游戏、不做截图、预览渲染或验收测试；最终外观、遮挡和手感由用户进游戏确认。

## 用户追加截图请求（2026-09-27）

上面的未测试状态为最初制作交付时的记录。用户随后明确要求截图，已补拍：

- Blender 衔接近景：`Review/sight_connection_detail.png`（1600×1200）；脚本 `render_detail.py`。
- UE 实机：`Saved/BowRingSight20260927/BowSightCaptureAudit_20260927_111801/`，包含腰射待机、ADS 待拉、ADS 满拉三张 1920×1080 PNG。
- 同目录 `capture.txt` 记录实际阶段、拉距、ADS 权重与加载的 `RingSightV17/SM_Bow_FineRingSight` 路径；截图时 ADS 权重均为 1，满拉拉距为 1。
- 使用独立 `-game -RenderOffscreen` 进程、独立测试档及现有净空测试地图；右键、左键通过实际 PlayerController 输入进入动作。未改玩家存档，拍摄进程已正常退出。
- `run_capture.ps1` 为重拍入口；`BowSightCapture.cpp` 为显式启用的 Editor 构建截图入口，必须使用 `BowSightCaptureAudit_` 开头的隔离档。
- 新增源文件时构建使用 `run_build.ps1 -RefreshSourceFiles -BuildLogName build-screenshot-capture.log`，刷新 UBT 源文件列表。

截图用于外观与遮挡验收，没有扩展为射击命中、音效、性能或全动作回归。
