# 腰射散布翻倍与曳光光段改造：发布记录（2026-09-21）

范围：本轮武器会话的两个改动——非手枪腰射扩散翻倍、曳光由"每帧一段"改为"每发子弹一条常驻段"——加上技能沉淀与仓库整理。诊断与方案见 [曳光升级方案](tracer-upgrade-plan-20260921.md)，配件数值口径见 [配件数值总表](attachment-values-20260921.md)。

## 提交与回读

| 提交 | 摘要 | 文件数 |
| --- | --- | --- |
| `49b626e` | Double hip-fire spread on rifles and publish attachment value audit | 8 |
| `91a8e44` | Rebuild tracers as per-round streaks and stop TSR ghosting | 10 |
| `0322451` | Sink tracer, hip-spread and blocked-build lessons into the UE5 skills | 5 |

- 推送：`git push origin HEAD:main`（普通非强制，`d96558e..0322451`）。
- 回读：`git ls-remote origin refs/heads/main` = `032245141a1cd55aeb340c3f7015682287178f9a`，与本地 HEAD 一致。
- 发布目录：`D:/FPS3D/FPSGAME` 仓库根——源码 `Source/`、工具 `Tools/`、作者脚本与材质源 `SourceAssets/`、说明 `Docs/`、技能 `skills/`。

## 精确暂存（共享工作区）

工作区同时躺着约 529 项其他会话的未提交改动，本轮只暂存自己的内容：

- 混合文件用新工具 `Tools/Weapons/stage_weapon_hunks.py` 逐 hunk 分拣（本轮补了 `--keep-contains` 只保留模式）：`Content/ColdSteelData/gunsmith.json`、`GunsmithSystem.h/.cpp`、`FPSWeaponFXComponent.cpp`、`FPSBallisticsComponent.cpp`，以及被其他会话整体重写的 `skills/ue5-debug-validation/references/live-coding-vs-full-build.md`。
- 共排除 11 个属于其他会话的 hunk：PKM 目录块（1）、近战 `BlockStamina` / `CooldownReduceSecondsPerHit`（2）、PKM 资产分支（3）、`FWeaponDamageResult` 命中签名（1）、技能重写（4）。保留的全部为本次改动。
- 丢弃后复核四项全部通过：暂存 diff 内对方标记数为 0、`git diff --cached --check` 无告警、暂存版 JSON 能 `json.load` 且武器 id 集合与 HEAD 一致（8 把，不含 `ue_pkm`）、暂存代码不引用被丢掉的字段与头文件。

## 发布检查

- `git diff --check origin/main..HEAD` 通过；待推 23 个文件全为文本，最大对象 `Content/ColdSteelData/gunsmith.json`（118 KB）；无二进制——`Content/*` 由 `.gitignore` 覆盖，V13 材质只留本机。
- 敏感信息扫描（`sk-` / `AKIA` / `ghp_` / 私钥块 / `api_key=` / `Bearer`）无命中；5 个 Python 作者工具的 `ast.parse` 全部通过；两份新文档没有相对链接，无需链接修复。
- 技能同步：4 份工程镜像更新后复制到个人目录 `C:/Users/allan/.codex/skills/`，两侧 `git hash-object --path` 一致（`c8a91a5c60`、`1cffd41fde`、`a506ff2f65`、`5d4c3ecbeb`）。

## 剩余内容依赖与未完成

- **本轮 C++ 尚未进入二进制**：完整 `FPSGAMEEditor` 构建被另一个会话未提交的 `Source/FPSGAME/Weapons/RuneGoldMaterialCommandlet.cpp` 挡住（先 include `UObject/SaveLoose.h`、改一版后换成 `EditorAssetLibrary.h`，两者在本引擎/本模块都不存在），UBT 在第一个编译动作 fatal、未链接。三个改动文件的 `-SingleFile` 编译均 `Result: Succeeded`——这只说明各 TU 能编过，不等于链接或运行验收。对方文件能编过后执行 `powershell -NoProfile -File Tools/Build/Build-Editor.ps1`。
- **PKM 的 `spread_mult: 2`** 落在对方未提交的 `ue_pkm` 武器块内，随对方提交一起落地；本轮提交的目录仍是 8 把枪（其中 6 把带 `spread_mult: 2`）。
- **材质**：`M_BallisticTracerVisibleV13` 已在编辑器内生成、编译、保存并回读（`responsive=1` 接常量 1.0、taper 已写入、`BLEND_ADDITIVE`、`responsive_aa=True`），属本机 Content，不公开提交。
- **已知残留**：单段几何无法同时满足"不断线"与"不成光柱"——M1911（253 m/s）与 DW715（420 m/s）在 ≤60 fps 仍有空隙。
- **未测试**：本轮没有运行游戏、没有画面验收、没有执行 `r.AntiAliasingMethod` 对照或 `t.MaxFPS` 扫描，全部交由用户测试。