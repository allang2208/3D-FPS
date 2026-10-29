# 尼泊尔弯刀：Meshy 上挑第三人称

后续更新：2026-10-27 已将当前单持、双持上挑接到[双手剑下半身与端正躯干版本](kukri-uppercut-sword-lower-20261027.md)。本页保留 Meshy 主挥击与手部适配的来源记录。

## 来源与范围

使用用户提供的 `C:/Users/allan/Downloads/Meshy_AI_Gray_Full_Body_Manneq_All_Animations (3).glb` 中的 `Charged_Upward_Slash`，源动作约 3.1667 秒。原 GLB 保留在 `SourceAssets/KukriMeshyUppercut20261025/`，散列记录在 `source.json` 和 `authoring.json`。该文件不是 CC0 素材，不推断其公开再分发许可。

本次替换 Jason、Kaitlin 的 `Kukri.FullBody.Uppercut`。两套原生动画位于各自 `ComboV3/<角色>/Animations/UppercutMeshyV5/`，名称为 `A_Kukri_Uppercut_MeshyRisingSlash`。

## 动作制作

主挥击使用源动作完整的右肩、肘、腕轨迹，并保留躯干发力、骨盆起伏和迈步。将源动作约 1.0–1.2 秒的上升挥击映射到当前攻击的 0.300–0.433 秒，0.350 秒对齐接触点，0.433 秒进入收势。最终轨道 120 Hz、153 帧、38/30 秒；仍由现有武技速度和暂停时钟播放。

源动作包含较大的转身和向前位移。第三人称保留限幅的蓄势与释放转体，剥离整体位移，前进仍由现有上挑胶囊移动处理。未修改第一人称、伤害、音效和技能时长。

源骨架没有独立手指，且主挥击前的空手腕弯折较大，因此进行握刀适配：

- 右手复用当前 Kukri 原生掌心挂接和有限手指链握持，拇指、四指及指节辅助骨一并写入。
- 保留源肩肘轨迹，使用目标角色骨长和肘部弯曲平面；腕部连续限制弯折与旋转范围，不逐帧翻腕。
- 在挥击阶段用真实刀柄坐标引导刀刃由前向上，手指与武器共用同一握点。
- 上臂及前臂 twist 辅助骨按本角色骨段站位生成。
- 左手作为胸前护拳，保留源动作的反向配合；拳形按手指顺序闭合，拇指稍后包覆。

起势从当前已接入的 Kukri 待机进入，收势回到同一待机；整条肩肘腕链连续混合。双脚采用错开的起落时间，避免两脚同时滑回。握刀指形贯穿全段，装备手指层仍使用相同原生来源。

## 接入与回执

制作目录：`SourceAssets/KukriMeshyUppercut20261025/`。

- `read_source.py`、`source.json`：源动作提取。
- `author.py`、`*-actions.json`、`authoring.json`：可重建的作者轨道和时间映射。
- `save_assets.py`、`run_commandlet.ps1`：后台 UE commandlet，在批次互斥下保存两个全新动画包。
- `assets-saved.json`、`save_assets-commandlet.json`：实际资产保存与 commandlet 退出回执。
- `publish.py`、`published.json`：通过共享配置事务入口，只写两套角色的 `Kukri.FullBody.Uppercut`。
- `delivery.json`：最终本地交付状态。

作者脚本读取当前待机入口；若待机资产已更换，会要求重新采集边界后制作。旧 UppercutV4、旋风、三连击和其他动作均保留。

按用户规则，本次不启动 UE 编辑器或游戏，不运行测试、截图或渲染验收。保存与接入完成不代表实机自然度、服装穿插已获确认；开始新的游玩实例后，由用户通过 F6 第三人称／固定第三人称体验。未执行 Git 提交或推送。
