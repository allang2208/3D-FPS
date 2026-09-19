# 棱镜阻手器三视图 v01

**当前版本：** 用户选择混元并要求修整后，游戏资产已更新为 [Polish 细节修整版](Polish/README.md)。该目录的 FBX、可编辑源及导入脚本是当前来源；下文记录首次接入，父目录旧源保留用于比较。

**当前握姿：** 已接入 [GripAnimation 棱镜专用抓握](GripAnimation/README.md)，安装后自动切换，含普通/弹鼓换弹脱离与回握；下文首次接入阶段的“沿用持枪动画”已由此版本更新。

按用户提供的低分辨率参考图，由内置 image_gen 生成侧视、正视、俯视概念图。用户随后要求继续，已使用 TokenHub 混元 3D 3.1 生成，并接入 M4 的前握把槽。

文件：`user_reference.png` 为用户原图；`three_views_v01.png` 为设计参考。未见角度是艺术重建，三视图尚非从同一 3D 网格渲染的严格投影。

提示词要点：保留短横向安装座、短小后倾渐收阻手部、内侧弧线、防滑纹及棱面；同尺度 SIDE / FRONT / TOP 正交展示；深石墨灰聚合物、浅灰金属座、浅灰背景，无枪械、手、UI 或品牌标记。参考图不能辨认的深度由一致造型推定。

生成入口：内置 image_gen，参考原图生成，非混元模型渲染。原始输出保留于 Codex generated_images。

## 3D 来源与处理

混元任务 `1489624951358898176`，原始 GLB、ZIP、请求及 SHA-256 保存在 `Saved/Hunyuan3D/Candidates/prism_handstop_v01/manifest.json`。只提交一次生成任务。服务将三视图重建为三个独立造型；最终保留左侧造型，未将其称为多视图融合结果。

`PrismHandstop_Raw.blend` 保留完整生成结果；`PrismHandstop_Editable.blend`、`SM_PrismHandstop.fbx`、`PrismHandstop.glb` 为处理后模型。处理包括分离左侧模型、焊接重复顶点、统一方向和比例、减面到 16000 三角面及双材质分区。保留 UV；生成法线与原始贴图留作参考，正式材质采用本地石墨聚合物/金属常量，避免生成贴图的白色外观与接缝。

`export_validation.json` 为 GLB 独立读回：一个网格、有 UV、零零面积面、零开放边、零非流形边。该模型是生成结果的整理版，未手工重新拓扑为生产级四边面模型。

## 游戏接入

资源 `/Game/Weapons/PrismHandstopV1/SM_PrismHandstop`；目录 ID `prism_handstop`，槽 `underbarrel`（界面“前握把”）。当前仅适配 M4。沿用原手臂，安装后使用 `/Game/Weapons/M4PrismGrip` 的 9 个专用动作；不改变枪械数值。制作方法以 [改造配件标准](../../skills/ue5-weapon-workflow/references/attachment-standard.md) 为准。

`M4HandstopVisual.cpp` 将组件绑定到 WPN_root；改造草稿、角色存档恢复和背包图标共用此入口。整枪展览递归收集配件，自动包含新模型。关闭未保存预览时恢复原配置，未装备实例改造不影响当前武器。打包资源目录已登记。

## 验证与边界

`build-final.log` 原生 Editor 构建通过。`import-final.log` 有 PRISM_IMPORT_PASS，资源尺寸与材质读回成功；commandlet 因项目既有 GameFeatureData 配置报错返回 1，不能称为干净退出。

`prism-v1/runtime.log` 首轮 24 项通过；最终焊接网格和贴合位置修改后的 `prism-final/runtime.log` 同样 24 项通过、0 失败，测试进程退出码 0。检查覆盖选择、草稿隔离、取消、保存失败、保存与重新加载、移除、未装备实例和图标，以及实际侧视、旋转、第一人称和全套配件截图。已查看最终侧视与全套配件画面，安装座贴近护木，整套配件在展示区内。开发模式验证，不代表完整打包或全套动作接触验收。

![最终游戏接入](prism-final/prism-side.png)

素材来源：用户参考图 + 内置图像生成 + 用户账户 TokenHub 混元生成；材质为本地创建。未公开推送原图、生成资产或商业资源。实际游戏画面使用工程现有 M4，沿用其来源许可。
