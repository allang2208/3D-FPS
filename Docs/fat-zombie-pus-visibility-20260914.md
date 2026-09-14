# 胖子脓液可见性修正

后续用户仍反馈主场景不可见，已定位并修复超大缩放地面的深度遮挡，详见 [主场景地面根因与修复](main-ground-pus-occlusion-20260914.md)。以下保留较早的材质修改记录，不作为最终根因结论。

用户反馈：脚踩死亡脓液会掉血，但地面看不到液体。本轮范围为显示链路排查和材质制作，不运行游戏或生成画面验收。

## 已有证据与判断

- 用户本轮已有游戏日志 `Saved/Logs/FPSGAME-backup-2026.09.14-04.49.43.log`，04:49:08.380、04:49:10.179、04:49:21.585 UTC 分别生成 1104、1056、912 个脓液地面三角形。结合用户确认的踩踏掉血，生成和伤害区域均已生效。
- 本轮日志没有再报 `M_FatZombie_Pus` 的 SM6 编译错误；上一轮 Alpha 接线修正已经写入当前材质。主工程与资源宿主的该主材质文件散列一致。
- 材质读取记录 `Saved/FatZombiePus/visibility_before.json` 显示：`BLEND_TRANSLUCENT`、`TLM_SURFACE_PER_PIXEL_LIGHTING`、`MTP_AFTER_DOF`，Opacity 输出仍经过 `.3 cm` 的 DepthFade，实例 Visibility 为 1。
- 引擎 DepthFade 公式为 `Opacity * saturate((SceneDepth-PixelDepth)/FadeDistance)`。脓液网格本身仅高出地面 `.35–1.45 cm`；这种透明水体深度淡出不适合承担脓液的主体可见性。深度差、透明通道和地面接近颜色是本次针对的显示风险，未采集实际像素，不能将某一环节宣称为已实机证实的唯一原因。

## 本次材质

- 改为 `BLEND_MASKED` / `MSM_DEFAULT_LIT`，主体写入正常场景深度，使用受光的湿润 PBR 表面；不再依赖透明渲染或 DepthFade 显示主体。
- 顶点 Alpha 继续限定原随机液洼和液滴覆盖，DitherTemporalAA 只负责边缘覆盖和结束时的消退。内部覆盖为 1，不再将主体叠成 45%–88% 的透明水膜。
- 薄层色由 `(0.19,0.25,0.030)` 改为 `(0.26,0.34,0.035)`，浓稠色由 `(0.055,0.078,0.008)` 改为 `(0.12,0.17,0.015)`，均为线性颜色，增强黄绿色辨识度。
- 保留已有河流水体双层细波纹、缓慢流动、污浊纹理、稀疏浮沫、低粗糙度及结束干燥参数。
- 未修改 C++、死亡时序、脓液随机几何、6 秒伤害期或敌对判定。

## 制作与交付

- 更新 `Tools/FatZombie/build_pus_material.py`；`inspect_pus_visibility.py` 读取已保存的失败材质设置，`rebuild_pus_visibility.py` 依次记录并重建。
- 初次读取脚本遇到 UE Python 对 CustomInput.Input 的受保护字段限制，已改用 MaterialEditingLibrary 的公开输入查询接口；正式重建退出码 0，日志 `Saved/Logs/FatZombie-pus-masked-authoring.log`。
- 指定 `M_FatZombie_Pus` 的 Windows SM6 着色器构建完成，退出码 0；日志 `Saved/Logs/FatZombie-pus-masked-sm6-build.log` 在 04:56:46 UTC 明确记录 `Working on Windows PCD3D_SM6`，04:56:47 完成。
- `M_FatZombie_Pus.uasset` 和 `MI_FatZombie_Pus.uasset` 已复制回主工程 `Content/Monsters/FatZombieMeshy/Pus/`。原版本备份位于 `Saved/FatZombiePusVisibility/before/`。
- 未进行游戏内测试。由用户重启编辑器后重新生成胖子僵尸，观察死亡原地液洼及周围液滴。
