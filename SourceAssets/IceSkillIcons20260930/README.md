# 冰墙与暴风雪新版冷钢图标（2026-09-30）

使用内置 `image_gen` 生成最终位图，参考已接入的 `Content/ColdSteelData/Skills/ice_spike_cold_steel.png`。规则来自 `Docs/UI/ui-cold-steel-design-system.md`：拉丝银色六边框、石墨凹面、左上柔光、无烘焙文字，元素色集中在主体。原卡通砖墙和金边紫晶背景图已替换。

## 最终文件与来源

- 冰墙：`ice_wall_cold_steel.png`；内置输出 `C:/Users/allan/.codex/generated_images/01a0f010-63db-7a92-9f2d-efa92f453ae0/exec-e7b76350-4035-4325-9d68-debe626191cc.png`。
- 暴风雪：`blizzard_cold_steel.png`；内置输出 `C:/Users/allan/.codex/generated_images/01a0f010-63db-7a92-9f2d-efa92f453ae0/exec-5d7dc33e-2f49-4af6-be90-ca9e0244725a.png`。

两张正式源图均已复制到本目录，并实际替换 `Content/ColdSteelData/Skills/` 同名运行文件。`skills.json` 图源路径保持同名；列表、详情、快捷栏、拖影、升级提示沿现有 PNG 加载路径读取，图标无需新增 UE Texture uasset。共享风格参考的既有授权边界保持不变；本机生成位图不自动进入 Git 公开发布。

旧运行图保存在 `trash/ice-skill-icons-20260930/`，`archive.json` 记录原路径、替代源、大小和 SHA-256。旧模型、纹理和音效没有改动。

恢复入口为 `Tools/UI/prepare_cold_steel_skill_icons.py`；冰墙旧制作入口 `prepare_ice_wall_sources.py` 和暴风雪资产作者 `build_blizzard_assets.py` 也改为读取本目录最终图，不再重制卡通墙或复制旧金边图。

## 冰墙完整提示词

Use case: precise-object-edit. Create the final production ICE WALL skill icon for a photorealistic UE5 dark Cold Steel FPS UI by editing the supplied style reference. Preserve the reference's full square composition, point-up regular hexagonal brushed-silver metal border, bevel thickness, inset graphite-black panel, exterior charcoal background, size and margins, and soft top-left lighting. Replace ONLY the central floating sharp ice-spears motif with an unmistakable ice barricade: a compact upright wall of thick irregular interlocking blocks of realistic frozen ice, three staggered courses, roughly four blocks wide, dominant broad continuous protective wall silhouette, slight three-quarter view showing genuine thickness, uneven fractured edges and natural seams. Translucent pale glacial blue ice with realistic internal cracks, frosted white rims, subdued reflections and varied internal opacity, textured surface; the wall must look like substantial natural ice rather than a graphic diagram, toy bricks or glass plastic. Center it inside the dark hexagon, cover about 65 percent of the interior width and 60 percent height with a clean readable silhouette even at 48 pixels. Keep neutral dark background and silver frame intact, concentrate desaturated ice blue on the wall; tiny low white cold vapor at the base is permitted. No letters, labels, numbers, watermarks, gold, purple gemstone background, fluorescent glow, UI mockup, flat vector shapes, cartoon linework, or decorative snowflake symbols. One final square icon, not a contact sheet.

## 暴风雪完整提示词

Use case: precise-object-edit. Create the final production BLIZZARD skill icon for the same photorealistic UE5 dark Cold Steel FPS UI by editing this supplied style reference. Preserve the full square composition, point-up regular hexagonal brushed-silver metal frame, bevel widths, inset charcoal graphite panel, exterior dark background, size and margins, and soft top-left lighting exactly. Replace ONLY the central ice-spear motif with a compact, clear pictorial depiction of an intense blizzard: a dense grey-white storm cloud in the upper middle, a powerful curved diagonal sweep of wind-driven white snow flowing below it, with three clearly readable pale glacial-blue ice shards falling diagonally downwards through the sweeping snow, low frosty haze below. Realistic atmospheric cloud volume, individual snow-grain highlights grouped into bold streaks, substantial ice with natural fractures and rough frosted rims; photographic physical textures and believable lighting. The cloud-and-sweeping-wind combination must form one strong readable silhouette occupying roughly 65 percent of the interior width and height, recognizable at 48 pixels; distinguish clearly from a stack of ice blocks and from upward ice spears. Keep silver frame and dark panel unchanged; concentrate subdued glacial blue in ice shards, white in snow and grey in clouds, no blue flooding of the entire panel. No lettering, labels, numbers, watermarks, gold border, purple gemstone background, decorative snowflake star, glowing rune, fluorescent glow, cartoon linework, flat vector shapes, UI mockup, landscape panorama, or multiple icon variants. One final square skill icon.

未进行游戏、PIE或运行时视觉测试；用户确认游戏内观感与交互。
