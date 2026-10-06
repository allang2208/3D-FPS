# RSH-12 加长方盒消音器模型

依据用户认可的方盒造型及随后给出的加长方向制作。模型、可编辑源、独立 PBR 贴图和游戏格式已在后台导出。初次交付为建模阶段；用户随后认可实际模型预览并要求继续，现已完成后台资产导入、运行引用更新及基础 DLL 编译。

## 外观与装配

- 长方盒主体，宽平面和削角保留概念图的轮廓；两侧长浅槽沿主体连续延伸，端盖与接座独立制作。
- 阶梯形钛色接座、黑色过渡肩部、装饰螺钉和薄暗接缝分件保留。源枪口护罩的端面外轮廓用于后接座，避免套圆筒接头造成断层。
- 使用当前 RSH 枪口配件的原点与坐标系：Blender 米制，局部 +X 向前、+Y 向右、+Z 向上。FBX 执行一次厘米转换。后续接入可沿用该枪挂载基准，并按作者清单更新前端表现点。
- 前端只有封底浅凹和外壳装饰，不制作内部机构。单张概念图中未展示的面按游戏美术需要补全，不称作实物结构复原。

## 交付文件

| 文件 | 内容 |
| --- | --- |
| `RSH12_CubeSuppressor_Long_Editable.blend` | 独立配件；可直接编辑的成品、保留修改器的分件、浅槽切割体和挂点标记；贴图已打包 |
| `RSH12_CubeSuppressor_Long_FitSource.blend` | 同一配件加原 RSH 静态装配参考；参考枪不参与导出 |
| `Exports/SM_RSH12_CubeSuppressor_Long.fbx` | 游戏 LOD0，6,442 三角面，三个材质槽 |
| `Exports/SM_RSH12_CubeSuppressor_Long_LOD1.fbx` | 保留轮廓、侧槽和接座的低细节版本，3,286 三角面 |
| `Exports/SM_RSH12_CubeSuppressor_Long.glb` | 带材质和贴图的独立模型 |
| `Textures/` | Shell、Titanium 两组 2K BaseColor / ORM / NormalGL / NormalDX，共八张；Recess 使用消光常量材质 |
| `Reference/RSH12_Cube_Concept_v2_Long.png` | 本次建模采用的加长概念图 |
| `author_model.py` | 可重做模型、材质及导出的作者入口，不启动 UE 或渲染 |
| `authoring.json` | 实际产物、面数、材质槽、坐标关系及未接入状态 |

三个材质槽为 `RSH12Cube_Shell`、`RSH12Cube_Titanium`、`RSH12Cube_Recess`。主体颜色和粗糙度沿用当前 RSH 导轨表面参考，钛色接座独立分区。BaseColor 按 sRGB，ORM 为线性 R=AO、G=Roughness、B=Metallic；Blender / GLB 使用 NormalGL，后续 UE 使用 NormalDX，避免再次翻转绿通道。UV0 使用统一物理纹理尺度，延长不拉伸表面颗粒和划痕。

作者几何尺度只服务于本游戏的外观比例与虚拟接口，不是现实产品规格。Blender/FBX/GLB 的实际生成信息见 `Author-console.log`；glTF 导出器给出共享纹理采样节点提示，两组节点使用相同的默认采样设置，日志原样保留。

## 状态与来源

- 制作和导出已完成；应用户“看看预览”请求生成下列 Blender 实际模型渲染。预览获认可后已导入 UE 并切换运行引用；未运行游戏测试。
- 加长概念来自本对话已保存的 image_gen 图片；配件外观由本轮 Blender 脚本制作。
- 静态宿主及虚拟接口来自项目现有 Medji RSH-12，沿用 `Docs/ThirdParty/RSH12-Medji-CCBY4.md` 署名。装配参考仅在本地源文件中保留，配件导出不含宿主枪体。

## 用户请求的模型预览

- `Preview/RSH12_Cube_Long_Mounted.png`：原 RSH 枪体安装效果，宿主使用原始 PBR 贴图。
- `Preview/RSH12_Cube_Long_Detail.png`：配件独立细节，展示加长主体、侧槽、端盖与接座。
- 对应 `.blend` 保留预览相机、灯光和地面；`render_preview.py` 可重新生成两图，`Preview/preview_receipt.json` 记录此次预览范围。

图片来自 Blender Cycles，对应当前源模型，不代表 UE 游戏画面。预览不改动成品源文件、几何或导出文件。`authoring.json` 的 `rendered: false` 为初次建模交付时状态，后续渲染记录单独保存在上述预览目录。

## 认可后的游戏接入

用户认可实际预览并要求继续接入。本次使用独立资产目录 `/Game/Weapons/RSH12/CubeSuppressor20261004`，沿用 `rsh12_heavy_suppressor` ID、现有安装变换及属性，更新 `RSH12MuzzleAssets.h` 的模型路径和前端表现点。旧存档不需要更换改造 ID；现有单持、双持及展示装配继续共用原有入口。

制作入口：`prepare_integration.py` 生成 WS 材质所需通道，`import_assets.py` 保存模型、三套材质及贴图，`import_icon.py` 保存实际 FramedFirearms 查找位置的 PNG / Texture2D，`publish_catalog.py` 仅更新该选项外观描述，`publish_runtime.py` 从已保存资产回执更新共享运行引用。图标采用 imagegen 内置工具，输入与原始提示词见 `icon_generation.json`。

后台入口 `run_stage.ps1` 提供 Import / Icon / Finalize / Build；已有编辑器时使用现有桥和 `import_live_batch.py`，LOD1 的补入在关闭编辑器后的 Finalize 阶段完成。基础 DLL 更新要求编辑器不再占用文件。各阶段是否实际执行完成以独立回执为准；当前制作脚本不自动代表资产或二进制已经保存。未运行游戏测试。

### 本次实际落盘结果

- 2026-10-04：编辑器退出后，后台 Import 批次已保存 LOD0 / LOD1、三套材质、八张运行纹理和配件图标；`import_receipt.json` 中 `complete`、`lod1_saved` 均为 true。一次离线 Import 已包含 LOD1，无需再执行 Finalize。
- 枪匠选项描述、PNG / Texture2D 和共享模型引用已更新，入口与回执为 `publish_catalog.py` / `catalog_receipt.json`、`publish_runtime.py` / `runtime_source_receipt.json`。原有改造 ID、安装变换、数值与消音分支继续使用。
- `FPSGAMEEditor` 基础模块编译成功；DLL 落盘时间为 2026-10-04 09:32:53 UTC，见 `build_receipt.json`、`Build-console.log`。未启动编辑器或游戏，运行效果由用户测试。
- 必要构建修复：修正本次头文件输出的重复 CR 换行，发布器改为显式 UTF-8 字节写入；已有 `EcologyWindowDiagnosisCommandlet.cpp` 的不可用 `GetComponentsByClass` 调用替换为类型化 `TInlineComponentArray`，未执行该诊断 commandlet。
- 原圆筒作者文件保留；其发布入口在方盒版正式发布后沿用新版运行引用与说明，RSH 总目录重建入口也保留该专属选项。
