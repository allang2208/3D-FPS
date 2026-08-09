# UI 工作流（UI 线的完整闭环）

> 目标：让 AI 产出“可控、统一、可维护”的 UI，而不是靠不断猜审美。
> 核心思路 = 情绪板定方向 → 设计 DNA 定规则 → Token 落地 → 组件复用 → 清单验收。
> 与 [WORKFLOW.md](WORKFLOW.md)（并行开发/提交纪律）配合使用。

## 0. 铁律

1. 动手前必读 `DESIGN.md`（风格唯一真源）与 `WORKFLOW.md`（文件所有权/提交纪律）。
2. 所有 UI 代码只消费 Token（颜色/字号/间距），禁止硬编码。
3. 新 UI 任务先查 `ui/registry.md` 组件注册表，能复用绝不新建；新组件先登记再实现。
4. 风格变更先改 `DESIGN.md` + 情绪板，再改代码；禁止“改着试试”。

## 1. 定风格（方向）

- 输入：用户参考图（即梦/截图/Figma 导出）、现有关键页面、竞品 UI。
- 用 GLM-4.6V 逐张读图（单张提问，避免多图串扰），提炼：配色、面板材质、
  字体、图标、布局、氛围。
- 输出：更新 `DESIGN.md`（风格 DNA + Token 表），产出/更新情绪板
  （`assets/ui/moodboard/`）。

## 2. 出图（生图管线）

- 首选 5080 FLUX.2 Dev（`flux2-dev-fp8`，1536 宽以上）；
  双机故障时兜底智谱 API（`zhipu-gen.py` glm-image）。
- 提示词按 `prompts/` 模板结构写（主题块 + 材质 + 视角 + 风格基准 + 负面写正向），
  中文标签直接写进提示词（生命/弹药/金币/波次）。
- 每个方向 3 张候选，落 `assets/ui/moodboard/`，同时保存 `prompt_*.txt`。

## 3. 验收（挑选）

- GLM-4.6V 定性描述候选图（布局/配色/风格是否符合 DNA）。
- 用户挑选或给出调整方向（如“更冷更战术”/“金色更多”）→ 回到第 2 步迭代。
- 定稿图作为该状态的实现基准，记录在 `PROMPT.md`。

## 4. 提取 Token（从图到代码）

- 从定稿图提取：主色/强调色/状态色、面板透明度、圆角、发光色、字号档位。
- 与现有 `DESIGN.md` Token 对齐：相同含义必须同一 Token，禁止同类新色值。
- 落地为 `ui/tokens.gd`（常量类，唯一数值真源），组件统一引用。

## 5. 实现（组件化）

- 按 `DESIGN.md` 三态模板实现：状态栏（`ui/status_bar.gd`）、背包/道具
  （`ui/backpack*.gd`）、Tooltip（`ui/item_tooltip.gd`）等均为独立组件，
  只消费 Token。
- 新页面 = 拼组件，不复制样式；页面间差异只体现在布局与内容。
- HUD 用 `_on_*` 转发 + 稳定信号（player/gun/enemy 契约），不改动画线接口。

## 6. 验证

- 无头运行：`--quit-after 120` 无 SCRIPT ERROR。
- 行为冒烟：`tests/test_status_bar.gd` 等，覆盖数值/状态/交互更新。
- 一致性检查清单（`DESIGN.md` 第 8 节）逐项打勾。

## 7. 提交

- 完成即提交，`ui:` 前缀，不跨任务攒改动。
- 提交前 `git status --short` 确认不覆盖对方未提交文件；
  对方正在改的文件（如 `ui/backpack*`）先停手协调。

## 8. 本次情绪板流程回顾（已落地）

1. 首版：全境封锁 × 游戏暗金六边形风格 → 智谱兜底出 3 张（v1）。
2. 参考即梦三状态图（菜单/战斗/探索）→ GLM 读图提炼 DNA →
   重出 3 张（v2）→ `DESIGN.md` 据此固化 Token。
3. 下一步：5080 修好后 FLUX 横版精修；Token 落地 `ui/tokens.gd`；
   状态栏/背包按新 Token 统一。

## 9. 落地到日常工作（具体执行）

### 角色分工

- 你（用户/设计决策）：定方向、给参考图、挑情绪板、拍板换肤（v1 暗金 ↔ v2 全境封锁）。
- AI（执行）：读 `DESIGN.md` + `style.gd` 后实现；改样式只动 Token 层；跑自动化门禁。

### 每次 UI 任务的五步（固定）

1. 读 `DESIGN.md`（风格真源）与 `WORKFLOW.md`（文件所有权）。
2. 查 `ui/style.gd` 是否有可用 Token；没有 → 先加进 `DESIGN.md` + `style.gd` 再写代码。
3. 查 `ui/registry.md`（+ `registry.json`）复用组件（`status_bar.gd` / `backpack*.gd` / `item_tooltip.gd`），
   禁止复制样式；新组件先登记再实现。
4. 跑门禁：`tests/test_ui_tokens.gd`（Token 对齐 + 无硬编码）+ 相关组件冒烟。
5. `ui:` 提交；`git status` 确认不覆盖对方未提交文件。

### 换肤 = 改 palette.json（已落地，方案 A）

色值真源 = `ui/palette.json`（`ui/style.gd` 启动时自动读取并覆盖，组件引用方式零改动）。
不需要写代码调色：
- 打开 `tools/palette-editor.html`（网页调色面板）→ 加载 palette.json → 调色 → 导出覆盖原文件 → 重开游戏。
- 或直接编辑 palette.json 里的 hex 值（`#RRGGBB` / `#RRGGBBAA`）。
- 新增/同步色值：跑 `tools/gen-palette.ps1` 重新生成（从 style.gd 提取）。
- 改到 DESIGN.md 关键 Token 时同步更新 DESIGN.md，否则 `test_ui_tokens` 报不一致。

### 自动化门禁（已落地）

`tests/test_ui_tokens.gd`：
- DESIGN.md 关键 Token 与 `style.gd` 数值必须一致（不一致即红）；
- `status_bar.gd` / `item_tooltip.gd` 出现裸 `Color(` 硬编码即红；
- 待对方提交后把 `backpack_hud.gd` 纳入扫描。

### 新颜色进组件的唯一路径（禁止跳步）

`DESIGN.md` 加色值 → `ui/palette.json`（或 gen-palette.ps1 重新生成）→ `style.gd` 默认值兜底 → 组件引用。
任何一步缺失都算硬编码。

## 10. shadcn 模式落地（本机已部署）

### 本地 shadcn 文档站

- 部署位置：`E:\3d\shadcn-ui`（官方仓库 `shadcn-ui/ui`，MIT，文档 v4）。
- 一键启动：`powershell -ExecutionPolicy Bypass -File tools/shadcn-docs.ps1` → http://localhost:4000
- 局域网（5080 副机等）访问：加 `-HostName 0.0.0.0`；停止：`-Stop`。
- 注意：官方 `pnpm icons:dev & next dev` 的 `&` 在 Windows cmd 下是顺序执行，icons:watch 永不退出导致
  next 永远不启动；脚本已拆成两个独立后台进程规避。首次运行脚本会自动补 `pnpm install` 与 `registry:build`。

### 借鉴到 Godot UI 线的三点

1. **注册表（已落地）**：`ui/registry.md` + `ui/registry.json` 对应 shadcn 的组件注册表与
   `r/index.json`——新组件先登记、AI/人类共用一份组件清单，避免“第 2 套风格”。
2. **组件即代码 + 文档驱动**：每个组件独立 `.gd` 且只消费 `style.gd` Token，对应 shadcn“代码复制进你
   的项目、可定制”的哲学；组件接口/依赖/验收登记在 registry，改动先改文档。
3. **设计参考**：本地文档站的按钮/弹窗/拖拽/无障碍交互，作为把 Web 成熟交互翻译成 Godot 实现的参照；
   情绪板与 DESIGN.md 仍是我们风格的唯一真源。
