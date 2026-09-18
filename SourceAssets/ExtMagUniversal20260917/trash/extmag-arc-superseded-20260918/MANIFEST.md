# 扩容弹匣废案（extmag-arc-superseded-20260918）

第七轮把 M4/QBZ 的延长段改成"弧管重建"后，前六轮的构建产物、脚本与对照图整体退役到这里。
逐条记录（原路径、字节数、SHA-256、理由、替代物）见 `MOVED.json`。

## 为什么退役

- 第五/六轮"切一段带体、复制到下方再焊"的路线在接缝处必然错位（两段切环差 1.8–2.5 mm RMS），实机表现为用户看到的"弹匣建模错误、有错误截断"；
- 弧管路线（`Scripts/build_extmag_arc_tube.py`）沿弹匣自身轴线切一刀、按弧步生成延长管，接缝由构造闭合（`seam_gap_mm = 0`），已取代前六轮的几何；
- 更早被否决的：第 1 轮通用 PMAG 件、第 2/3 轮逐枪烘焙涂层（`*_finish_uv.fbx`、`bind_extmag_finish.py`、`finish_*` 回执）、弹鼓重建模（`drum*`，已退回旧鼓）。

## 保留在案（未退役）

- 当前结果：`Scripts/build_extmag_arc_tube.py`、`install_extmag_arc.py`、`Reference/arc_tube_build.json`、`install_extmag_arc_receipt.json`、`Reference/dupb_review_*.png`（第七轮审查图）；
- AKM 仍是第三轮"逐截面切线"版：`Scripts/build_extmag_from_factory.py`、`Reference/akm40_factory_build.json`、`Reference/akm_*_mag_*.png`、`ExtMag40_AKM_Editable.blend`、`install_extmag_factory.py`、`factory_install_receipt*.json`；
- 测量与座位记录（技能引用）：`Reference/seat_final.json`、`seat*.json`、`well.json`、`weapon_frame_fit.json`、`SK_*.inspect.json`；
- 图标（专属图仍在使用）：`Scripts/render_icon_per_weapon.py`、`icon_per_weapon_receipt.json`、`Reference/icon_ue_*.png`、`Reference/icon_magazine_large_drum.png`；
- 文档：`README.md`（含前几轮的过程记录，链接指向本目录）。

## 边界

- 本目录里的 FBX/PNG/Blend 属本机留存，`.gitignore` 不提交二进制；仓库只发布脚本、回执 JSON 与说明。
- `/FPS3D/FPSGAME/trash/`（仓库根，已在 `.gitignore` 中）另有整批退役件，同样不入公开 Git。
- 同级的 `trash/extmag-ringfit-superseded-20260918/` 是**第五轮版本**的副本（第六轮重跑之前的 FBX 与回执）；本目录 `FBX/*_dupb.fbx` 是第六轮重跑后的版本。两者都是"切带复制"路线的失败对照，保留以便对照两次失败的具体差别。
