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

## v2：参考即梦（Jimeng）三张全境封锁风 UI 重出（2026-08-09）

参考目录：`C:\Users\allan\Downloads\新建文件夹`（菜单交互 / 战斗 / 探索三状态）

### 风格共性（从参考图提炼）

- 冷色低饱和场景（雪天 / 雨夜 / 废弃地铁），UI 与场景色调统一
- 半透明磨砂玻璃面板（透明度 30-50%）+ 青色发光边框 + 玻璃反光
- 现代无衬线中文字体，白/浅灰，极淡发光描边，层级分明
- 扁平几何发光图标（六边形/圆形/菱形），红（血条/警告）、绿（状态）、
  蓝（科技/准星）、橙（任务/进度）高饱和强调色
- HUD 四角环绕：左上小地图（蓝网格 + 橙路线/标记）、右上资源条（黄→红渐变）、
  左下状态列表、右下技能网格 + 弹药数字、中心准星（蓝光环 + 红十字）

### 三张 v2 输出

| 状态 | 文件 | 提示词 |
|---|---|---|
| 菜单交互 | `moodboard_v2_menu.jpg` | `prompt_v2_menu.txt` |
| 战斗 | `moodboard_v2_combat.jpg` | `prompt_v2_combat.txt` |
| 探索 | `moodboard_v2_explore.jpg` | `prompt_v2_explore.txt` |

生成：智谱 API `glm-image` 1280x1280（5080 FLUX 故障期间兜底）。

## v3：定稿金色方向（2026-08-09）

定稿基准：`ref_division_ui_improvement.png`（《全境封锁 1+2》UI 改进情绪板，
源自 `C:\Users\allan\Downloads\图片-1.png`）。

- 方向：**金主色 #D4AF37 + 白信息 #FFFFFF + 深灰底 #0F0F10 / #3A3A3C / #B5B5B5**；
  字体思源黑体 + 字重阶梯；按钮三态 / 金进度条 / 玻璃面板 / 分隔线。
- 按此八段式格式出的完整情绪板：`moodboard_v3_board_1.jpg` / `_2.jpg` / `_3.jpg`
  （提示词 `prompt_v3_board.txt`）。
- 同步：`DESIGN.md` 已更新为定稿方向；`ui/style.gd` 已加入 `THEME_*` Token
  （未启用，换肤时整体替换 `COLOR_*`）。

## 待办：修好 5080 后出 FLUX 精修版

远端需以 `--use-split-attention` 启动（或修复 xformers 对 sm_120 的适配），
再用 `flux2-dev-fp8 --size 1536x1024 --steps 26 --cfg 3.5` 出横版高清情绪板。
