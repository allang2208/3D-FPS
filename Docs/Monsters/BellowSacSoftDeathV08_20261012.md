# 鼓囊 M-09 连续软体死亡 V08

按用户指定的非人形怪物连续软体死亡标准制作，沿用 M-14 V19 的 XPBD 接触、内部耗散、伸长限制和共享尸体预算，为鼓囊独立制作代理与表面绑定。不是用固定死亡片段将角色拉回站姿。

## 动作与交接

- 从致命伤发生时的待机、移动或攻击可见姿势接管，四肢失去支撑后重力下落，背囊和躯干接地后连续摊开，喷管随身体垂落。
- 按原骨骼的蒙皮权重识别四条远端腿链及喷管。权重总和至少 0.65 的代理节点解除压缩支撑；骨盆、胸部、背囊与近端肢根保留正常体积约束。
- 使用本物种的原地下落配置，不增加通用向前推力、横向移动惯性或临时撑脚。继续保留防翻转、拉长限制、真实地面接触和无回弹响应。
- 当前父类 `AWolfMonster::EnterState` 已在权威端与客户端进入死亡时调用 `TryStartSoftDeath`；绑定到实际活体网格后直接沿现有入口生效。`OnDeathPresentationStarted` 取消未释放攻击，已发射囊弹继续自身飞行和引信。
- 奖励、死亡状态复制和原尸体寿命继续沿用。待机、移动、V03 蓄压攻击、4 秒投掷间隔、V06 声音与 V07 圆环不改动。

## 制作与预算

读取原 V01 活体网格的 133,403 个源顶点，焊缝去重为 99,017 个位置；专用代理为 652 点、2,238 个四面体，间距约 19.19 cm，低于标准 700 点上限。各模型独立表面权重与正重心嵌入，不复用 M-14 的几何或骨编号。

尸体拥有独立网格、骨架、数据和变形法线材质；保留原 PBR 贴图与主体表面，仅尸体重绑。活体网格只增加运行时硬引用绑定；尸体只保留已重绑的 LOD0。

共享作者函数新增可选 `unsupported_source_bones` 配方字段，在生成节点权重后离线分类，避免在线读取文件或扫描模型。未提供该字段的旧配方行为不变；运行时求解器未修改。仍用既有 120 Hz 固定子步、每帧最多六步及共享准入预算，稳定后停止更新。

## 入口与产物

- `Tools/BellowSacLobber/prepare_soft_death_v08.py`：从当前蓝图动作集引用导出原表面及独立尸体副本。
- `Tools/BellowSacLobber/author_soft_death_v08.py`：复用共享四面体作者，生成本物种代理、表面嵌入和解剖支撑配置。
- `Tools/BellowSacLobber/install_soft_death_v08.py`：保存尸体、变形法线材质与正式活体网格绑定。
- 制作源与回执：`SourceAssets/BellowSacLobberMeshy20261012/SoftDeathV08/`；`Before/` 保留绑定前的活体包。
- UE 目标：`/Game/Monsters/BellowSacLobber/V08/SoftDeath/`。

Editor／Game Win64 Development 构建均成功，记录为 `Saved/BellowSacLobber20261012/build-soft-death-v08-editor.log`（38.51 秒）和 `build-soft-death-v08-game.log`（47.36 秒）。

后台导出、安装 commandlet 均退出 0；安装日志 `install-soft-death-v08.log` 包含 `BELLOW_SOFT_DEATH_V08_INSTALLED`，`SoftDeathV08/delivery.json` 记录五份实际保存包：尸体材质、尸体网格、独立骨架、数据及带绑定的正式活体网格。原 V03 动作集引用保留。未打开图形编辑器。

未运行游戏、测试、截图或预览渲染。实际死亡动作、落地观感和性能由用户体验确认。
