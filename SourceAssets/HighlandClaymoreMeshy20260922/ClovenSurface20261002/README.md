# 裂角护手翼面材质调整（2026-10-02）

用户反馈本轮表面相对优化，并要求护手采用剑身金属。后续现用材质调整见 [剑身金属适配分支](BladeMetal20261002/README.md)。该分支保留本目录制作的连续 UV，使用剑身材质图与同源四路 PBR 替换本轮独立锻钢表面。继续制作应使用该分支安装器，勿用本目录旧安装器恢复上一轮翼面材质。

用户反馈第一人称近景中护手材质糊成一片。本分支从当前 V5 连续接口母版的 `SM_Highland_Guard_Cloven_JunctionV5` 制作，专门替换两侧裂角翼面的表面。

原裂角由原装护手拉弯、加厚，沿用旧 UV；Meshy 原图集也含明显的条带拖影与明暗。大幅变形把这些信息进一步拉长。提高旧图集分辨率或仅改粗糙度不能恢复翼面细节。

## 制作

- 以弯角中心线弧长和横截面角度建立连续 UV0。中央连接区、宝石、暗槽、赤红嵌纹的 UV0 原样保留；原图集坐标另存 UV1 `OriginalAtlas`。
- 翼面分配独立材质，主体使用中性深灰锻钢底色、细加工纹理和稳定的粗糙度。去掉翼面主体原有大片黑灰拖影及画在底色中的亮暗条带。
- 原边缘纹饰重采样到新 UV，保留轮廓中的既有装饰；限制绘制高光，并降低旧法线强度。根部按 27 mm 宽度渐变回原材质。
- 转移法线先从原 UV 的切线基转入新 UV0 的切线基，避免直接换 UV 后把凹凸方向旋转。三张 2048 贴图：BaseColor（sRGB）、Normal（OpenGL）、ORM（线性，R=AO/G=Roughness/B=Metallic）。UE 导入法线翻转绿色通道一次。
- 主体粗糙度约 0.48，纹饰边约 0.375，翼面金属度 1；纹理包含轻微亚毫米加工细节，主体无低频污渍或烘焙照明。
- 顶点位置、V5 接口、宝石结构和作者面角法线保持原样。新增翼面材质槽；`M_HighlandClaymoreSurface`、`M_Cloven_Recess`、`M_Cloven_Inlay` 原材质槽保留，弹反的 `GuardCharge`/`GuardWave` 与顶点色使用原路径。

## 文件

- `author_surface.py`：从 V5 母版制作专属 UV、转移输入、FBX 及带贴图的可编辑 Blend。
- `author_textures.py`：确定性 PBR 制作和原纹饰转移。
- `Highland_ClovenGuard_ArcSurface20261002_Editable.blend`：独立作者源。
- `Export/SM_Highland_Guard_Cloven_ArcSurface20261002.fbx`：接入源。
- `Textures/`、`surface_transfer.npz`、`texture_recipe.json`、`author_receipt.json`：纹理、转移输入与制作配方。
- `install_background.ps1` / `install_surface.py`：通过项目资产批次互斥执行后台导入；已有编辑器时沿用互斥桥，不另起覆盖进程。
- `Before/<时间>/`、`install_receipt.json`：目标包安装前备份、资产保存回执。

## 接入边界

目标稳定路径为 `/Game/Weapons/HighlandClaymore20260922/SurfaceRepairV4_20260927/SM_Highland_Guard_Cloven_SurfaceV4.SM_Highland_Guard_Cloven_SurfaceV4`。目录仍沿用该路径，不回写旧 ClovenGuard 或 V4 几何。独立材质和贴图位于 `/Game/Weapons/HighlandClaymore20260922/ClovenSurface20261002`。共享高地剑材质图与纹理不修改。

导入器保留当前槽材质、LOD/Nanite 设置，导入作者法线并以 UV0 重算 MikkTSpace 切线。完成标志是 `install_receipt.json` 的 `complete: true`；仅有脚本和 FBX 不表示接入完成。后续整组重新制作 V5 时，应将本分支护手替代旧裂角源，避免旧作者脚本覆盖新表面。

本轮后台制作、导入及保存已完成。最终 commandlet 日志为 `install-20261002-004508-621.log`，退出码 0，打印 `CLOVEN_SURFACE_INSTALL_COMPLETE`。三张贴图、独立 Substrate 材质与上述活动网格已落盘；前两次导入在新材质准备阶段遇到 Python 枚举名称和 AO 引脚差异，修正后继续，未在失败阶段改写活动网格。安装回执记录最终材质槽映射和当前包备份。

来源及许可沿用本机高地剑原 Meshy 制作记录和原项目素材。本次没有新增外部下载素材。没有运行游戏、测试、截图或验收渲染，视觉效果由用户测试。
