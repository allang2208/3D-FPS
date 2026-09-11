# 强化材料写实三视图与 RTX 5080 对比

日期：2026-09-11。阶段：已完成游戏接入及后续紫色矿石/蓝色粉尘材质变体；此处保留生成对比历史，最终接入见 `Docs/Art/enhancement-materials-20260911.md`、`enhancement-stone-amethyst-20260911.md`、`magic-dust-blue-20260911.md`。

物品身份沿用 `enhancement_stone`（强化石）及 `magic_dust`（魔法粉尘）。参考来自当前 `Content/ColdSteelData/Icons/*_realistic_v1.png`。三视图使用内置 imagegen 生成，黑底隔离，分别裁切为 front/right/back 输入 TRELLIS.2。矿石隐藏面属于三维重建。粉尘第一版重复角度已弃用，最终版本纠正为方罐面朝镜头的正交视图，并调整背面粉堆方向。

## 对比合同

同物品使用相同输入、seed、Euler 采样、同一相机灯光。baseline：512，结构/形状/纹理 12/16/12；high：1024_cascade，16/32/24。两档都使用 2K 贴图、100000 面导出目标，先隔离重建档位差异；未试验 4K 贴图或100步上限。baseline token 上限49152，high 999999，实际分辨率须结合日志验证。

每档保留 `raw_geometry` 未减面几何母版（无纹理），以及 `textured_master` 带贴图重网格导出（目标10万面，不是未减面原始几何）。实际三角面和贴图尺寸以 `*_mesh_report.json` 为准。节点快照 `nodes.json`，硬件 `hardware.json`，回执/完整工作流/执行历史按物品档位命名。`vram_samples.jsonl` 仅记录定时采样设备显存，不是精确峰值，也不排除系统及其他进程占用。

全部来源为当前已有自制参考图、内置生成及本机授权 RTX 5080 管线。原始 GLB 与可编辑 Blender 文件保存在此目录，运行时玻璃/粉尘分件质量须独立检查。

## 实测结果与交付

| 任务 | 执行时间 | 原始三角面 | 带贴图母版三角面 | 状态 |
| --- | ---: | ---: | ---: | --- |
| 强化石512 | 102.29秒 | 2443554 | 98804 | 成功，下载与SHA-256校验完成 |
| 强化石1024级联 | 726.05秒 | 9075790 | 99756 | 成功，下载与SHA-256校验完成 |
| 粉尘512 | 324.13秒 | 11155582 | 94554 | 成功，下载与SHA-256校验完成 |
| 粉尘1024级联 | 未完成 | 未导出 | 未导出 | 恢复至 HR 采样后用户接受现有精度并叫停，已定向请求取消 |

强化石高档断面起伏更细，部分512圆滑边缘得到改善；本次耗时约为512的7.1倍，不是最大参数测试。输入三视图分辨率分别1942×809和1983×793，单视角约647/661像素宽，未来更高质量单视角参考仍有提升空间。

粉尘512的原始模型把玻璃和粉末合成偏黑外壳，增加面数并未解决真实透明结构。本轮另做玻璃内外壁、盖、粉末、晶粒分件重建，明确作为人工制作版本。原始5080输出保留对比。

推荐候选位于 `Delivery/`：强化石20000面，粉尘12070面，2K贴图，底部中心原点，可编辑Blender和内嵌贴图GLB。图像参考用内置imagegen；模型预览和旋转视频来自实际GLB的Blender渲染，未使用生成图冒充模型。已导入 UE，绑定 `/Game/Items/EnhancementMaterials`，独立测试档 27 项检查通过；实际正立与掉落截图见项目 Saved/EnhancementMaterials*InGame.png。

强化石首次1024任务因误判阶段日志未刷新而被中断，后重新完整运行成功，上表726.05秒仅计算成功运行。高分辨率形状约353秒，纹理约232秒；中途未写进日志不代表没有计算。相关回执保留为 `*_attempt1.receipt.json`。

强化石直接从908万原始面烘焙的实验产生黑斑（法线图负切线Z约48.4%）；保存为 `*_raw_bake_rejected*` 并淘汰。正式低模改从整理后的99756面高模烘焙，负切线Z约0.42%，渲染检查已通过。不能用高面数替代表面质量检查。

## 图像生成提示词

共用要求：Create a photorealistic 3D modeling reference turnaround sheet from this reference. Wide landscape image split into exactly three equal width invisible panels. Left is straight front orthographic elevation, middle is right side orthographic elevation, right is rear orthographic elevation. Same exact physical object rotated, consistent silhouette dimensions, material details, lid and fill height, same scale and baseline. Each object centered in its third with generous margins. Eye level, no perspective or visible top-down view. Pure solid black background, no floor, no contact shadows, no panel borders, no text or labels. Neutral soft studio illumination showing real material roughness and microstructure. Real photographed artifact look, physically plausible restrained colors, absolutely no illustration or stylized low-poly appearance. This is input for multiview 3D reconstruction; coherent hidden surfaces are essential.

强化石身份：Preserve the reference ore identity: asymmetrical angular charcoal metallic ore chunk with silver fractured mineral planes and inset pale icy blue crystal veins. No added pedestal, magical aura or floating fragments.

魔法粉尘身份：Preserve the reference container identity: squat thick clear rounded square glass jar, broad shoulders, short circular neck, weathered dark silver knurled screw lid. Lower two-thirds contains fine silver-gray powder and small pale ice blue mineral grains. No label. Do not replace the jar with a pile.

粉尘修正提示词：Correct this modeling turnaround sheet. Currently the three jars show essentially the same corner-on view. The jar is a SQUARE cross section with rounded corners, not cylindrical. Regenerate three truly orthographic FACE-ON elevations: FRONT flat glass wall facing camera squarely, RIGHT SIDE flat glass wall squarely, BACK flat glass wall squarely. No vertical corner ridge in the center of a panel! Broad single rectangular front face, rounded vertical corners only at far left and right edges. Identical jar dimensions and powder fill. Distinct physically coherent powder grains seen from respective sides. Rear powder heap reverses left-right position compared to front. Camera at jar midheight, no visible lid top surface, lid is flat horizontal profile. Photorealistic clear thick glass, closed silver knurled lid and silver powder with pale blue crystal grains as reference. Exactly three equal thirds, same scale, solid black background no floor no labels no text. Maintain all material identity and realistic details.

用户已接受当前精度并要求暂停。已向恢复任务发送带 prompt_id 的定向 interrupt，HTTP 200；检查时当前节点仍为 in_progress，未把请求接受记作任务已退出。共享队列其他任务保持不动，本地监测脚本已停止。此次粉尘高档对比不再继续，不记作成功或显存失败；最终采用已验收的分件模型。记录 `recovery_pause.json`。

明确失败的 raw_bake_rejected 模型和法线已归档到 `trash/non-weapon-items-20260911/SourceAssets/EnhancementMaterials5080_20260911/`，散列清单见 `Docs/Art/non-weapon-items-archive-20260911.json`。原始高模及有效母版仍在本目录。
