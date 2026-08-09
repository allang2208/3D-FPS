# UI 情绪板（全境封锁 × 无尽轮回）生成记录

## 风格基准（双向融合）

- **全境封锁（The Division）侧**：战术射击 HUD，暗蓝黑底色，细琥珀/橙色描边，
  数据面板、分段血条、弹量计数、地图/技能环、扁平半透明玻璃面板、扫描线、暗角。
- **无尽轮回侧**：暗色面板 + 金色（#ffd84a 系）强调、六边形金边徽章 + 底部浮雕宝石底座
  （技能图标既有体系）、中文界面（生命/弹药/金币/波次/击杀）、现代无衬线中文字体。

## 提示词（FLUX.2 dev，正向表述，负面约束写入正向）

```text
UI mood board concept sheet for a tactical sci-fi FPS game interface, The Division-inspired HUD combined with the game's dark gold hexagonal badge style: in-game first-person HUD mockup on a dark navy-charcoal battlefield backdrop, thin amber and gold accent lines, flat translucent dark glass panels with subtle scanlines and faint grid, segmented health bar with Chinese label 生命 at top-left, small text 波次 and 击杀 at top-center, gold coin counter 金币 at top-right, large ammo counter 弹药 at bottom-right, three weapon inventory slots at bottom-center, skill icons as hexagonal badges with bright gold trim and engraved crystal gemstone bases, center crosshair with four thin ticks, clean modern sans-serif Chinese font, crisp sharp vector-like interface elements, professional AAA game UI concept art, high detail, frontal screen view, no watermark, no blur, single coherent HUD layout
```

## 生成参数（实际执行）

- 首选 5080（`flux2-dev-fp8`）出图失败：远端 ComfyUI 注意力算子未适配
  Blackwell（RTX 5080，capability 12.0），`memory_efficient_attention_forward`
  无可用实现，SDXL 同样失败 → 按管线兜底走**智谱 API**。
- 模型：`glm-image`（智谱），尺寸 `1280x1280`，watermark=false
- 输出：`moodboard_zb_1.jpg` / `moodboard_zb_2.jpg` / `moodboard_zb_3.jpg`（三张候选）
- 提示词原文见 `prompt.txt`（同一份）

## 待办：修好 5080 后出 FLUX 精修版

远端需以 `--use-split-attention` 启动（或修复 xformers 对 sm_120 的适配），
再用 `flux2-dev-fp8 --size 1536x1024 --steps 26 --cfg 3.5` 出横版高清情绪板。
