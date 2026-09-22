# SVD（德拉贡诺夫狙击步枪）第三方素材声明

- **作品**：SVD (Dragunov sniper rifle)
- **作者**：LeroyCake（<https://sketchfab.com/leroycake>）
- **来源**：<https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf>
- **许可**：**CC BY 4.0** — <https://creativecommons.org/licenses/by/4.0/>（允许商用，必须署名）
- **获取日期**：2026-09-22

要求的署名文字：

> "SVD (Dragunov sniper rifle)" by LeroyCake, licensed under CC BY 4.0.
> Source: https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf

## 用途与状态

导入位置：`/Game/Weapons/SVDDragunov20260922/{Meshes,Materials,Textures}`，共六个独立网格：枪体 `SM_SVD_Body`、弹匣 `SM_SVD_Magazine`、扳机 `SM_SVD_Trigger`、拉机柄 `SM_SVD_ChargingHandle`、保险杆 `SM_SVD_SafetyLever`、PSO-1 瞄准镜 `SM_SVD_Scope`（各一套材质，共用同一坐标原点）。

截至本声明日期：**已完成模型、机械分件与材质导入为资产**。尚未绑定项目共享 Manny/M4 手臂、未做骨骼与动作、未注册武器数据/枪匠条目/图标/音效，因此**还不是可在游戏中使用的武器**。

## 修改说明

等比缩放到实枪全长 1.225 m 并把枪口转向项目约定方向（Blender -Y → UE +X）、各部件共用整枪原点、按测量区域**重组既有壳体**分出弹匣／扳机／拉机柄／保险杆（不裁切表面，面数总和与源一致）、贴图保持 4096（法线转无损 PNG）、在 UE 内重建材质（BaseColor × AO × Tint / Normal 翻转绿通道 / Roughness × Scale / Metallic）、关闭 Nanite、碰撞用三角面。未修改网格拓扑、UV 或贴图内容，未重新烘焙。逐件散列与源结构见 `SourceAssets/SVDDragunov20260922/PROVENANCE.md`。
