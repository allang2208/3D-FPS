# M4 垂直握把：精修、抓握与游戏接入

已完成，最终实机标签 `vertical-final-v2`。游戏入口：M4 枪匠 → 前握把 → 垂直握把。安装时自动选择专用九条动画，拆卸后恢复原动作；保留共振握把与棱镜阻手器，槽位互斥。

## 模型与材质
- 26,324 三角面，连续圆角顶部、装饰紧固件、底部环纹与细槽；零非流形边、零零面积面，具有 UV。
- 上级目录保存真正的 5080 原始模型。握身按生成模型轴向轮廓重新布面，顶部和细节为作者修整，不能称为原始 AI 网格直接输出。
- 统一使用当前 M4 的 `/Game/Weapons/M4InfimaV3/Body_001` 材质及其 BaseColor、Normal、Roughness、Metallic 贴图；贴图源与散列见 `model_validation.json`。已有项目素材沿用原许可，网页参考未获再分发许可，不公开发布原图和商用贴图。
- 资产目录 `/Game/Weapons/M4VerticalGrip`，模型 `SM_VerticalForegrip`，配件 ID `vertical_foregrip`。仅为游戏美术资产，生成尺度已按游戏挂点与手模校准。

## 手部与动作
四指环握、拇指对握；使用原 M4 手臂、骨架、蒙皮和材质。局部屈伸轴限制拟合，保留骨长、scale 与手指局部平移。逐指松开、侧退后接回原换弹，原取弹、插入、压实、拍击、右手和机械轨道保持，时长及音效合同不变。

待机、ADS、腰射/瞄准射击、装备、普通/空仓换弹、弹鼓普通/空仓共九条专用动作。`reference_contract.md` 记录源帧段；`fit_final.json`、`release_profile.json` 保存本次接触与逐指轨迹。

## 交付
- `M4_VerticalForegrip_Integrated_Editable.blend`：可编辑完整 M4、手臂、配件与九条专用动作。
- `VerticalForegrip_Refined.blend` / `SM_VerticalForegrip.fbx` / `VerticalForegrip_Refined.glb`：模型源及导出。
- `A_M4_Vertical_*.blend/.fbx`：各动作独立源与 UE 导入文件。
- `M4_VerticalForegrip_Gameplay.mp4`：四种换弹实际截图按捕获顺序组成的静音预览；不作音频同步证明。
- `grasp_closeup.png` / `grasp_front.png` / `wrist_review.png` / `idle.png`：最终实机画面。

## 验证
- 最终新游戏进程：344 PASS、0 FAIL，验证安装、互斥替换、保存重载、ADS/射击、装备与四种换弹及弹药恢复。
- 枪匠界面：24 PASS、0 FAIL，含草稿取消、保存失败重试、图标、完整横向取景、卸除和未装备实例。
- 446 个手指/配件几何采样无交叉；这不等同整枪整臂和连续时间绝无穿模。
- 九条源动画合同检查通过；导入读回通过，最大 RAW/COMPRESSED 探针位置差约 0.00151 cm。
- 原生模块 `2026094138` 编译成功。导入命令行退出码为 1，日志包含已有 GameFeatureData 配置与 8000 端口占用错误；具体资产读回和后续新进程游戏验证分别通过。未进行完整打包验收。
- `acceptance.json` 保存最终资产散列、误差和运行计数。

## 复现入口
`refine_model.py → polish_material.py → fit_pose.py → refine_contact.py → final_contact.py → sync_material.py → build_animation.py -- idle → fit_release.py → fit_release_profile.py → build_animation.py → validate_source.py / check_geometry.py -- --full → import_assets.py → run_validation.ps1 -Run <新标签> → make_delivery.py <同标签>`。
`ReferenceWorkflow` 是隔离的作者脚本依赖；本次参数不能原样套用其他握把。模型后改需 `sync_models.py` 同步到可编辑动作并重新检查几何。组合源由 `assemble_editable.py` 生成。

## 后续抓握修订

本版被用户指出抓握不够紧。模型、材质和配件功能继续使用；九条动画当前已由 `../TightGrip/` 修订替换，掌面与四指完整包握，拇指连续外展。最新视觉与运行验收见 `../TightGrip/README.md` 和 `../TightGrip/acceptance.json`，本文件上文为前一版历史记录。
