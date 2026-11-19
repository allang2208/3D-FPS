# 技能树与子专精（2026-11-15）

用户于 2026-11-15 要求把技能面板升级为技能树并接入游戏，后续再慢慢调整内容和数值。规划与界面合同见 [技能树接入规划](../../../Docs/UI/skill-tree-plan-20261115.md)，设计稿在 `Work/SkillTreeMockup20261115/`。

## 数据

- `Content/ColdSteelData/skill-tree.json` 是唯一来源：分组、系别行、每个技能的列/行/前置，以及专精节点。由 `Work/SkillTreeMockup20261115/export_tree_json.js` 从设计稿导出；前置等级可用同目录 `balance.py` 按「同阶门槛 ≈ 同等击杀修炼量」重算（中级 40 / 高级 150 / 终极 400 次）。
- 新增技能要进树：在 json 的 `skills` 下加条目（branch、lane、column、requires）。不在树里的技能（环绕飞剑、水晶照明等武器技能）始终可用。 原因：技能树控制登记技能的习得条件，未入树的武器能力仍沿用自身可用性规则。
- 专精节点的 `effect.stat` 是 C++ 读取的数值键；`implemented:false` 的节点只显示，不能投点。新机制做好后把它改成 true。 原因：显示节点不代表运行机制已经存在，提前允许投点会消耗资源却没有实际效果。

## 存档与判定

- `FColdSteelProfile::SkillTreeVersion / LearnedSkills / SkillSpecs`。不要用 Level 0 表示未习得：`Skills` 里的等级始终 ≥1，大量公式依赖这一点。 原因：同一个数值在不同区域重复或换口径展示会产生歧义，详情需要保留明确的数据来源。
- 迁移 `ColdSteelSkillTree::Migrate`：旧存档全部技能视为已习得；全新角色只开放无前置的根基与各系起点。
- `MasteryProgress(Id)` 对未习得的树技能返回 Level 0，所以现有 `MasteryProgress(...).Level<1` 判定（客户端与服务器权威）自动表示「未习得」。步枪、手枪、暴击、闪避、巧手的进度读取也走它，未习得时被动加成为 0。
- `ColdSteelSkills::AddExperience` 不给未习得技能加修炼经验。
- 施放拦截：快捷栏 `CanBindQuickSkill`、服务器 `ExecuteCastRequest` 阶段 0、快速进战（客户端与 `ServerQuickCombat`）、上挑 `CommitSwordUppercutRelease`。新增主动技能如果绕过快捷栏，要自己加 `IsSkillLearned` 判定。
- 联机：习得与投点在客机本地 `CommitState`，随档案上传；主机 `SanitizeGuestProfile` 调 `ColdSteelSkillTree::Sanitize` 剔除前置不满足的习得记录和超额专精点。`ColdSteelProfileMerge::Progression` 合并 `LearnedSkills` 取并集；专精点不合并（重置会降低），以上传为准。

## 专精数值接入点

- 火球：`FireballStats(AtLevel, bApplySpecs)` 是唯一权威位置（主机模型或服务器影子档）。半径、射程、下坠开始时间 `DropDelay`、引燃灼烧 `SpecBurnStacks`；灼烧在 `ApplyFireballExplosion` 追加 `AddBurn`。
- 下坠开始时间要同时改飞行与预览：`AFPSFireballProjectile::Tick` 的解析位置和 `FPSMagicPreview::SamplePath`（新参数默认 0，冰锥共用）。 原因：轨迹预览与投射物需要相同下坠起点，否则瞄准提示将偏离实际飞行路径。
- 元素箭：`ElementalArrowStats` 调 `FireballStats(-1,false)`，火焰元素按 `inherit.scale`（0.5）继承火球的爆破与灼烧专精；冰、雷爆发半径不受火球专精影响。自身专精：火焰倍率、寒冷、眩晕、`ElementalArrowManaCost`（射出、准备、持续检查三处共用）、拉弓耗蓝在 `TickRuntime`。
- NPC 档案没有专精，`SpecStat` 返回 0。

## 界面与提示

- P 键与右侧「技能」入口打开全屏 `UColdSteelSkillTreeScreen`；抽屉技能页只保留给「配置快捷魔法」。
- 网格与连线是 game-dev 科技树算法的 C++ 移植 `ColdSteelSkillTreeLayout::Build`，绘制在 `SColdSteelSkillTreeCanvas`。改布局后用 `node Work/SkillTreeMockup20261115/grid_check.js` 离线检查交叉。
- 顶部提示 `UColdSteelProgressNotification` 改为 game-dev 格式：无底板；`bUpgrade` 提示为金色 28px 带辉光、绿色 18px 说明；普通 `PostNotice` 为银白 20px。习得、可以习得、专精点、专精解锁提示由 `QueueSkillTreeNotices` 从前后档案差异生成，迁移本身不发提示。
- 专精重置：F6 交互开发面板 · 基本调参「专精重置」卡；重置代价留待后续。

## 自绘踩坑（2026-11-15 用户反馈：卡片白底、选中链路图标消失）

- `FSlateDrawElement::MakeBox` 把传入的 Tint 当作圆角画刷的**填充色**，描边颜色则直接取画刷自身的 `OutlineSettings`（引擎 `DrawElementTypes.cpp` `MakeBoxInternal`）。传 `White` 就是白底；给“只描边”的画刷传金色 Tint，会把整张卡片填成金色并盖住同层图标。
- 规则：填充用画刷自己的颜色（`SColdSteelSkillTreeCanvas.cpp` 的 `Fill(Brush, Alpha)`）；每种描边颜色单独建一个透明填充的画刷，绘制时 Tint 传 `Transparent`；描边、选中框放在图标和文字之上的层。
- 全屏技能树打开时，按地图面板的做法隐藏 buff 栏（`UStatusEffectsHUDSubsystem::SetWorldMapOpen`）与任务追踪栏（`UColdSteelHUDWidget::SetWorldMapOpen`）。HUD 的顶部提示层在 Z60 全屏面板之下，所以技能树内自带一份 `UColdSteelProgressNotification`，打开期间折叠 HUD 那份。

## 快捷栏与法杖魔法轮盘（2026-11-16）

- 旧抽屉技能页退役（无入口，源码暂留）。快捷栏与轮盘都在技能树里配置：底部 13 格快捷栏条复用 `UColdSteelQuickSlot`，右栏「魔法轮盘」复用 `UColdSteelMagicWheel` 配置模式；存档字段与绑定规则不变。
- 嵌入的 UMG 控件按 UMG 单位（px / PixelScale）自排版，技能树根是像素级 `SDPIScaler(1/PixelScale)`，所以嵌入处要再套一层 `SDPIScaler(PixelScale)` 抵消。
- 技能树打开时 `StartQuickDrag` 不改抽屉、不抢焦点；`EndQuickDrag` 把焦点还给技能树；`DropMagicDrag` 在技能树打开时也接受。

- 自绘画布必须 `SetClipping(EWidgetClipping::ClipToBounds)`：平移/缩放后的内容按偏移绘制，不裁剪会在滚动时画到标题栏、图例和快捷栏上（2026-11-16 用户反馈）。 原因：平移后的绘制坐标可以超出控件区域，裁剪负责保护周边固定界面。

## 右栏版式（2026-11-17 用户反馈：太挤、要更宽、删掉规则长段）

- 右栏宽度用 `UColdSteelSkillTreeScreen::DetailWidth()`（视口宽 40%，480–760 px），不要再写死宽度；嵌入旧详情页时把 `Inner + 32` 传给 `ShowEmbeddedDetail`，页内 `PageWidth ≥ 480` 才用横排三列数值行。 原因：文字方向、宽度和字体覆盖决定可读性，窄列逐字换行会破坏信息层级。
- 嵌入详情只放数值。新加的玩法规则、公式、修炼规则段落用 `UColdSteelSkillPage::Note`（嵌入时返回 Collapsed 的 SBox）；只有规则段的小标题或卡片用 `if(!bEmbedded)` 跳过。Collapsed 子项在 SScrollBox / SVerticalBox 中连槽位 padding 一起不计入。
- 技能简介只在技能树头部显示一次（skills.json `description`），嵌入页不再重复。 原因：嵌入页面与树头展示的是同一简介，重复显示会占用空间而不提供新信息。
- 用 Python 改 CRLF 源文件时按二进制读写，或读写都指定 `newline=''`；默认通用换行会把整文件改成 LF。

## 联机同步（2026-11-17 检查）

- 习得与专精由客机本地决定，随档案上传，主机 `SanitizeGuestProfile`（`ColdSteelPlayerProfileAdmission.cpp`）→ `ColdSteelSkillTree::Sanitize` 清洗；主机施法入口（`ColdSteelPlayerSpellCast.cpp`）按影子档案 `IsSkillLearned` 判定。新增技能树相关的客机自有字段时，记得同时加进客机镜像合并处（`Multiplayer/ColdSteelPlayerProfileSync.cpp` 的 `OnRep_MirrorBlob` 里保留 `CurrentInventory` 字段的那一组），否则在途旧镜像会回滚它。
- 主机生效有延迟：客机改动后最多 2 秒开始上传，加上传输时间；这期间施放刚习得的魔法会被拒绝并退蓝。

## 发布与仓库边界（2026-11-19）

- 本批发布见 `Docs/Publication/SkillTree20261117/README.md`：11 个技能树专属源文件与 `skill-tree.json` 直接提交；共享宿主（`ColdSteelStatusModel.h`、`ColdSteelInventoryTypes.h`、`ColdSteelProfileRuntime.cpp`、快捷栏／提示／火球模型等）只出 HEAD 相对补丁。别把整份共享宿主当本批产物提交。 原因：并行会话在同一宿主里留有未发布的工作，整文件提交会连带他人内容。
- 切分工具：`Work/pubaudit/slice.py` + `skilltree_spec.py`（未命中默认 `theirs`，按关键字规则认领本批 hunk），产物在 `Work/pubaudit/out/*.patch`；核对 `.result` 里的关键声明是否留下。 原因：关键字规则漏认领会静默产出空补丁或丢掉接口声明。
- 本仓库工作树约 3.6 万索引项，`git log/show/diff-tree` 单次可能数十秒；批量重放用临时索引脚本（`skilltree_replay.py`：`read-tree origin/main` → 逐项 `update-index --cacheinfo` → `write-tree` → `commit-tree -p origin/main`），不要反复手工调用。 原因：重复慢速调用会持续超时。
- 本地 `main` 可能落后 `origin/main`，且工作树带大量未提交改动导致 `git merge --ff-only` 被拒；不要强推，也不要 stash 他人改动。用 `commit-tree -p origin/main` 生成重放提交后 `git push origin <sha>:main`。 原因：工作树是多会话共享状态，任何整树操作都会破坏他人未提交工作。
