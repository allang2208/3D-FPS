# 战斧材质与背包图修复

本轮根据用户要求检查战斧材质和背包图，范围不扩展到玩法测试。

**当前交付状态：修正后的实装网格已保存，正式背包图已替换。** `mesh_save_receipt.json` 和 `delivery.json` 记录保存与部署结果。`Catalog/` 是最终 UE 成图；旧 UE 法线诊断图保存在 `Before/ue_pipeline_old_normals.png`。

## 发现

- `material_readback.json` 来自已打开编辑器中的实际网格与材质：网格正确使用战斧私有材质；BaseColor 为 sRGB/BC7，Normal 为线性法线压缩并翻转 G，MetalRough 为线性 Masks，三图均为 4096²、UV0。Substrate 输入接入相应纹理，无 WorldGrid 回退或错误骨骼用途。
- `blend_before.json` 显示可编辑源的三张图引用和色彩空间正确，未发现丢图。
- 作者脚本在改动顶点后读取角点法线。Blender 已随形变更新法线，此时再次应用变换造成重复旋转。原模型 584220 个角点中，547224 个与源法线的正确变换方向相反，平均点积 -0.8511；黑面主要来自错误表面朝向，不能靠提高曝光或粗糙度掩盖。
- 修正为改点前保存原始角点法线，再只变换一次；修正后相反角点为 0，最小点积 0.999998，平均约 1。原始比较保存在 `Before/normal_comparison.json`，修正后见 `normal_comparison.json`。
- 旧目录 PNG 额外走了 Blender 灰阶/独立灯光，误用仅适用于改造栏的去色规则。已从 `author_hatchet.py` 移除；后续图标用 `../export_inventory_icon.py` 调用既有 UE 目录图管线。

## 接入与检查边界

用户确认 UE 空闲后，实际发现编辑器已关闭，使用无界面 commandlet 执行 `reimport_corrected_normals.py`，网格重导、27 个退化切线角点修正及保存均完成。保留原材质、握点、UV、拓扑、Nanite 与动作。过程见 `reimport-headless-2.log`，保存结果见 `mesh_save_receipt.json`。

网格保存后，背包目录图用 `ColdSteelWeaponIconCatalog -Definition=ue_tactical_hatchet` 直接使用实际 UE 模型、原始 PBR、统一棚光和正交取景制作。最终图为 256×384 RGBA，符合 2×3 占格；alpha 轮廓中心为 (128,192)，主轴填充 91.15%。已查看最终图，刃口高光、斧面纹理和完整轮廓正常，并同步至 `Content/ColdSteelData/Icons/ue_tactical_hatchet.png` 与源 `Icons/`。导出日志为 `export-final.log`，结果 `COMPLETE failures=0`。旧模型、FBX、图标及作者脚本保留于 `Before/`。

后台首次启动被 SDK 校验占用的共享 Build.bat 锁阻塞，尚未执行导入脚本便停止了本任务进程。随后仅在资产制作进程的环境中设置引擎支持的 `UE_SKIP_UBT_SDK_SETUP=1`，没有修改系统环境、引擎文件或其他构建任务。导入和出图均成功退出；无 C++ 改动，不需要重新编译。此前互斥等待记录保留在交付回执中。

本轮做材质绑定与法线检查、目录图目视检查；不运行 PIE、攻击动画或联机测试。已有游玩会缓存 PNG 与动态图，重新进入游玩后加载修正结果。
