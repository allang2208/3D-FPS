# 尼泊尔弯刀握柄表面 V2 · 2026-10-27

范围为棱纹胶柄、缠革握柄、层压木柄。保持现有网格、UV、握持接口、材质资产路径和游戏数值，直接更新这三款材质正在采样的纹理。

- 胶柄：石墨灰橡胶，圆润菱格的结构法线、微细模压颗粒，减少干涩粉白的表面感。
- 皮柄：深棕皮革，斜向搭接边、细毛孔与高处轻微抛光，收窄接缝。
- 木柄：纵向流动的层压木纹、细纤维法线与薄漆光泽。
- 全握持面替换旧材质，不再通过两端渐变混回原木色；原金属铆钉使用原材质遮罩及细节法线。

每款包含 2048×2048 BaseColor、ORM、Normal，共 9 张 PBR。ORM 为 R=AO、G=Roughness、B=Metallic。Normal 从三维表面烘焙到原有 UV0 切线空间，源图为 OpenGL +Y，UE 导入时开启绿色通道翻转并使用 NormalMap 压缩；ORM 禁用 sRGB，基色为 sRGB/BC7。三张图标为 1024×1024 RGBA，UI 纹理组、Editor Icon 压缩、Never Stream，无 Mip。

## 可编辑制作源

- `author_surfaces.py` / `Kukri_Grip_SurfaceV2_Editable.blend`：程序材质、结构及微表面法线，已烘焙材质与原几何。
- `surfaces.json`：三款运行路径和新贴图。
- `render_icon_inputs.py`：真实模型灰阶取景输入，仅用于正式图标制作。
- `render_framed_icons.py` / `Kukri_Grip_SurfaceV2_FramedIcons_Editable.blend`：金属方框、四角铆钉、内圆环、深灰底板与真实握柄。
- `icon-prompts.json`：内置 image_gen 请求记录。服务以 violence 分类拒绝请求（request ID 8dffdf4d-709a-4997-9bfa-2e7bef8715a2），未采用生成结果。最终图标由上述 Blender 场景直接渲染，保留当前模型、法线及灰阶规范。

## 接入

`prepare_staging.py` 复制 12 个已存在的 Texture2D 到独立最小 UE 作者工程；`import_assets.py` 在无界面 commandlet 中导入保存。`publish_when_available.ps1` 使用现有 `Local\CodexUeMcp-Port-8000` 批次互斥，等游戏工程无编辑器／commandlet 占用后，发布精确的 12 个纹理包与 3 张运行 PNG，并推进组件和正式图标清单中的三款握柄来源。

`Before/` 保留替换前文件；`Receipts/import-assets.json` 表示作者工程保存结果，`Receipts/publication.json` 的 `complete: true` 才表示已部署到游戏工程。网格不重新导入，保留上一轮修复的持久 MeshDescription 和 LOD。无需 C++ 构建。

没有启动 UE 编辑器或游戏，没有追加测试或验收渲染。游戏内效果由用户检查。
