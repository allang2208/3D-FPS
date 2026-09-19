from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

HOST = Path('D:/FPS3D/FPSGAME')
REPO = Path('E:/3d/publish-ue5-m4-20260910')
AUDIT = HOST / 'Docs/repository-ue5-root-20260910'
BASE = 'a56dd1dbf562fd66c09e00908b0256c4edb707f4'
assert subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD']).decode().strip() == BASE
manifest = []

def write(relative, text):
    p = REPO / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + '\n', encoding='utf8', newline='\n')

def copy(p):
    raw = p.read_bytes()
    relative = p.relative_to(HOST).as_posix()
    # Preserve content; normalize only line endings/terminal blank lines for Git.
    normalized = raw.decode('utf-8-sig').replace('\r\n', '\n').rstrip() + '\n'
    write(relative, normalized)
    manifest.append(dict(path=relative, host_bytes=len(raw), host_sha256=hashlib.sha256(raw).hexdigest(),
                         repository_bytes=len(normalized.encode()), repository_sha256=hashlib.sha256(normalized.encode()).hexdigest()))

for root in ['Source', 'Config', 'Tools', 'ThirdPartyNotices']:
    for p in sorted((HOST / root).rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:
            continue
        if p.name == 'DefaultEditorPerProjectUserSettings.ini':
            continue
        if p.suffix.lower() in {'.cpp', '.h', '.cs', '.ini', '.json', '.py', '.ps1', '.md', '.gd'}:
            copy(p)
for p in sorted((HOST / 'Content/ColdSteelData').glob('*.json')):
    copy(p)
copy(HOST / 'FPSGAME.uproject')
for p in sorted((HOST / 'Docs').glob('*.md')):
    copy(p)
for p in sorted((HOST / 'Docs/UI').glob('*.md')):
    copy(p)
# Same reviewed authoring dependency set as the preceding M4 publication.
for p in sorted((REPO / 'unreal/m4-arms/SourceAssets').rglob('*')):
    if p.is_file():
        copy(HOST / p.relative_to(REPO / 'unreal/m4-arms'))
for p in sorted((HOST / 'skills').rglob('*')):
    if p.is_file():
        copy(p)

write('.gitignore', '''# Unreal generated/local state
/Binaries/
/DerivedDataCache/
/Intermediate/
/Saved/
/Build/
/.vs/
/.idea/
/.codex/
*.sln
*.suo
*.opensdf
*.sdf
*.VC.db
*.VC.opendb
*.log
__pycache__/
*.py[cod]
/trash/
# External licensed binary content and authoring files remain local.
# A reviewed, redistributable asset can be explicitly allowlisted later.
/Content/*
!/Content/README.md
!/Content/ColdSteelData/
/Content/ColdSteelData/*
!/Content/ColdSteelData/*.json
/Plugins/
*.uasset
*.umap
*.ubulk
*.uexp
*.blend
*.blend1
*.fbx
/SourceAssets/**/*.png
/SourceAssets/**/*.jpg
/SourceAssets/**/*.wav
/SourceAssets/**/*.ogg
/SourceAssets/**/*.mp3
/SourceAssets/**/*.mp4
/SourceAssets/**/*.glb
/SourceAssets/**/*.gltf
/SourceAssets/**/*.bin
/Config/DefaultEditorPerProjectUserSettings.ini
''')
write('.gitattributes', '''* text=auto
*.cpp text eol=lf
*.h text eol=lf
*.cs text eol=lf
*.ini text eol=lf
*.uproject text eol=lf
*.py text eol=lf
*.ps1 text eol=lf
*.json text eol=lf
*.md text eol=lf
*.yaml text eol=lf
*.png binary
*.jpg binary
*.uasset binary
*.umap binary
''')
write('.editorconfig', '''root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
''')
write('README.md', '''# 无尽轮回 3D FPS · Unreal Engine 5

当前项目入口是根目录 **[FPSGAME.uproject](FPSGAME.uproject)**，基于 UE **5.8.2**。2026-09-10 起，`main` 已从旧 Godot 原型切换为 UE5 工程源码。

仓库包含当前宿主的完整 `FPSGAME` C++ 模块、Editor/Game targets、配置、库存与枪匠 JSON 数据、开发工具及工作流。原始模型、贴图、音频、地图等本地 Content 尚未纳入公开源码，恢复这些依赖后才能得到本机的完整游戏效果。当前源码状态和迁移记录见 [仓库迁移](Docs/RepositoryMigration.md)。

| 目录 | 用途 |
| --- | --- |
| `Source/` | 当前游戏代码：角色、枪械、UI/库存、天气、场景与怪物 |
| `Config/` | 工程、输入、渲染、CommonUI 与打包配置 |
| `Content/ColdSteelData/` | 当前物品、枪匠、仓库及提示数据 |
| `Tools/` | 导入、检查、运行验收与场景工具 |
| `SourceAssets/` | 当前 M4 抓握、甩匣、拍击的作者脚本和参数；二进制源在本机 |
| `Docs/` | 当前工作说明、功能验收记录和资源恢复说明 |
| `skills/` | UE5 枪械、手臂动画、C++、调试及天气标准 |
| `ThirdPartyNotices/` | 已记录的第三方来源说明 |
| `unreal/` | 迁移期间的历史快照；当前代码以根目录 `Source/` 为准 |

先读 [开发与发布规则](WORKFLOW.md) 和 [资源恢复](Docs/AssetSetup.md)。本机完整宿主仍位于 `D:/FPS3D/FPSGAME`，不要用历史快照覆盖它。

安装 UE 5.8.2 及其 Windows C++ 工具链，在 PowerShell 中编译：

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$((Get-Location).Path)/FPSGAME.uproject" -WaitMutex
```

修改实际引擎路径，并从仓库根目录执行。工程启用了 CommonUI、EnhancedInput、Niagara 相关运行模块和 PCG；`ModelContextProtocol`、`AllToolsets` 是当前宿主额外安装的编辑器工具，详见资源恢复说明。

- [枪械与手臂工作流](WEAPON-WORKFLOW.md)
- [M4 当前动作合同](skills/ue5-fps-arms-animation/references/m4-baseline.md)
- [UI 与库存记录](Docs/UI/README.md)
- [雨效](Docs/RAIN_UPGRADE_20260910.md)、[雷雨云层](Docs/STORM_CLOUDS_20260910.md)

旧 Godot 项目的完整历史保留在 [archive/godot-before-ue5-20260910](https://github.com/allang2208/3D-FPS/tree/archive/godot-before-ue5-20260910)。它不再是当前开发入口。少量 `Tools` 中的 `.gd` 只是迁移参考导出器，仓库不再包含 Godot 游戏工程。
''')
write('WORKFLOW.md', '''# UE5 开发与仓库发布规则

## 1. 当前工程

根目录 `FPSGAME.uproject` 和 `Source/FPSGAME` 是当前源码真源。UE 5.8.2；完整本机宿主 `D:/FPS3D/FPSGAME`。新功能使用 UE5，旧 Godot 仅通过归档标签取回作为迁移参考。`unreal/` 保留历史证据，不是用于覆盖当前模块的第二份实现。

## 2. 修改与验证

先核对实际文件、运行加载和并行修改。维护角色、UI、库存、弹药和存档合同，按明确范围提交。原生源码用 Editor/Game 对应目标编译；改动玩法时运行相应 `Tools` 验收并检查真实游戏画面。编译成功不代表动画、素材恢复或打包验收。仅整理仓库和文档时，检查来源散列、结构、链接、脚本语法和 diff。

## 3. 枪械与动画

读 [枪械技能](skills/ue5-weapon-workflow/SKILL.md) 和 [手臂技能](skills/ue5-fps-arms-animation/SKILL.md)。先查看原有动画，再记录姿态、接触和音效时序；保留用户选定枪型，使用独立候选验证后接入。完整可编辑源及已许可素材留在本机，发布文件清单明确缺失依赖。

## 4. 目录及归档

正式 C++ 放 `Source/`，工具放 `Tools/`，作者脚本/参数放 `SourceAssets/`，说明和结果放 `Docs/`。确认退役的文件移到 `trash/<task>/`，记录原路径、目标、大小、SHA-256、原因和保留替代物。移动前验证所有绝对路径属于本次授权范围，移动后读回校验。不要凭旧日期或候选名判断废案。

## 5. 内容依赖

按 [资源恢复](Docs/AssetSetup.md) 管理 Content。商用授权和原始资产再分发许可分开检查。默认不提交未核准二进制、引擎、插件、字体、缓存、日志和 `trash`；需要新增合法资产时，核准来源后精确更新忽略规则。完整本机工程的备份不等于公开 Git 源码发布。

## 6. 技能与文档

维护相关 UE5 技能，个人技能和工程镜像同步；当前入口使用仓库相对链接。案例日期和历史验收不能写成当前重新测试结果。Godot 的旧命令和旧标准留在归档历史。

## 7. 并行工作

不 stash/reset/clean 共享目录，不覆盖他人未提交修改或暂存区。`E:/3d/3-dfps` 仍是旧共享本机 checkout，其 master 不代表远端 main；不要为让它“干净”而强行切换。发布目录与可运行宿主分别记录，迁移快照保存取样时间与散列。

## 8. 仓库整理与推送

1. 核对仓库根、origin、远端默认分支和授权 URL。当前目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。
2. 推送前 fetch 并检查目标分支到 HEAD 的所有提交。共享脏目录或历史分叉时，在基于远端 main 的隔离工作区发布当前明确范围。
3. 使用精确路径清单暂存。禁止全库 `git add -A`、`git add .`、`git clean`、`reset --hard`，不夹带其他未发布历史。
4. 检查完整暂存差异、`git diff --cached --check`、大小、敏感信息、许可及与改动相关的验证。文档更新不用跑旧 Godot 测试。
5. 仓库换引擎时先保留旧主线归档标签，再用普通新提交替换当前树，不使用 orphan 或强推抹去历史。
6. 只普通非强制推送，显式指定 `HEAD:main`。拒绝后重新 fetch 审查差异，不覆盖新增提交。
7. 成功后通过 `git ls-remote` 回读分支及归档标签，记录提交 SHA、发布目录、验证和剩余内容依赖。
''')
write('AGENTS.md', '''# 当前开发方向

当前工程为根目录 `FPSGAME.uproject`（UE 5.8.2）。用户已指定后续全面转向 UE5；Godot 只作为归档参考。完整本机宿主为 `D:/FPS3D/FPSGAME`，Git main 的当前源码直接位于根目录，不再仅发布 `unreal/<topic>` 摘录。

- 开发和发布先读 [WORKFLOW.md](WORKFLOW.md)，仓库整理、归档与推送遵守第 8 节。
- 枪械读 [ue5-weapon-workflow](skills/ue5-weapon-workflow/SKILL.md)，手臂和 MAT 读 [ue5-fps-arms-animation](skills/ue5-fps-arms-animation/SKILL.md)。先参考现有动作，核对实际运行加载，再修改。
- 天气读 [ue5-weather-workflow](skills/ue5-weather-workflow/SKILL.md)，调试读 [ue5-debug-validation](skills/ue5-debug-validation/SKILL.md)。
- 保留动画时序、UI、库存、存档和并行修改。源码编译与真实运行验收分别报告。
- 本机宿主尚无独立 Git；旧共享 `E:/3d/3-dfps` 不得 reset/clean 或直接推送其分叉 master。使用基于远端 main 的发布工作区。
- 退役文件放 `trash/<task>/` 并记录散列。二进制资源及恢复边界见 [AssetSetup](Docs/AssetSetup.md)，未审核再分发许可的原始资源不公开提交。
''')
write('WEAPON-WORKFLOW.md', '''# UE5 枪械与手臂标准

当前工程入口为根目录 `FPSGAME.uproject`，完整本机宿主 `D:/FPS3D/FPSGAME`。

- [枪械标准](skills/ue5-weapon-workflow/SKILL.md)：模型/许可、骨架/挂点、ADS、枪匠、装备与存档。
- [手臂动画](skills/ue5-fps-arms-animation/SKILL.md)：自然抓握、甩匣、取弹插入、拉栓、MAT 和音效。
- [当前 M4 合同](skills/ue5-fps-arms-animation/references/m4-baseline.md)：参数应用前核对实际 C++ 加载。
- [发布规则](WORKFLOW.md#8-仓库整理与推送) 与 [资产恢复](Docs/AssetSetup.md)。

普通/空仓都甩掉旧弹匣、镜头外取新匣、左手包握插入。普通装好直接待机，空仓保留加速拍击及枪身轻震；装备在对应腰射位置播放拉栓。其他枪型重新校准接触和时序，不照搬 M4 数值。个人技能源与工程镜像保持同步。
''')
write('Docs/UI/README.md', '''# 当前 UE5 UI 与库存

实现位于 `Source/FPSGAME/UI/`，物品与枪匠数据位于 `Content/ColdSteelData/`。以下是按主题保留的实现记录，具体状态以当前代码及相应运行验收为准：

''' + '\n'.join(f'- [{p.stem}]({p.name})' for p in sorted((REPO/'Docs/UI').glob('*.md')) if p.name!='README.md'))
write('Content/README.md', '''# 本地 UE 资源

当前公开目录仅包含 `ColdSteelData/*.json`。本机模型、动画、贴图、声音、UI、场景和地图仍在完整 FPSGAME 宿主中。

按 [资源恢复](../Docs/AssetSetup.md) 恢复已获许可内容及原有 `/Game/...` 路径。勿把缺失资源误认为仓库可以直接复现完整游戏。
''')
write('Docs/AssetSetup.md', '''# 恢复完整 UE5 内容

源码来自 2026-09-10 的本机 `D:/FPS3D/FPSGAME`。此次换引擎整理保留完整模块与配置，未公开整套本地 Content 和二进制作者源。许可证及图片 provenance 只说明已有记录，不自动授予原始文件公开分发权。

## 本机继续开发

本机原工程未移动，仍打开 `D:/FPS3D/FPSGAME/FPSGAME.uproject`。如使用新的 Git checkout，在确认拥有使用许可后，从完整宿主复制 `Content`，保持相对路径和 World Partition 的 `__ExternalActors__`/`__ExternalObjects__` 成套；不要用旧快照覆盖当前源码。复制前处理目标同名文件的差异，不批量覆盖新工作。

作者编辑还需要本机 `SourceAssets` 中的 Blend、FBX、声音和引用源；仓库只包含当前 M4 三段依赖链的作者脚本及记录，恢复本地源目录可补齐其输入。`Tools` 中部分旧参考导出器仍指向本机 Godot 归档，不参与 UE 游戏运行。历史工具带绝对宿主路径，运行前检查其输入和输出路径。

## 主要资源依赖

| 内容 | 当前恢复位置/说明 |
| --- | --- |
| 启动地图 | `/Game/GameMaps/DayNight_Lighting`；按 Config 的真实路径恢复 |
| 枪械/手臂 | `Content/Weapons`，包括 M4HK416Replica、M4WrapGripFinal、M4SlapImpactFinal、M4TacticalTossFinal 及枪匠配件 |
| 声音 | 枪械 HK416 派生音效和天气资源；具体引用见当前源码及已有来源说明 |
| UI/物品图标 | `Content/ColdSteelUI`、`Content/UI`、`Content/ColdSteelData/Icons`；JSON provenance 不等于图标授权 |
| 天气/场景 | `Content/Weather`、PWL_Light_Manager、Lighting、SceneTests 及相关地图和场景包 |
| 怪物 | `Content/Monsters`、`Content/ZombieFemale`；用户提供包的许可尚需独立确认 |
| 作者源与 MAT | 本机 `SourceAssets` 与原 MAT 工具资产；MAT 不是本次公开发布的插件包 |

`ContentInventory.json` 列出宿主各内容目录的文件数和大小，供检查恢复范围；它不是每个资源的授权证明。

## 插件和构建

保留宿主原 `FPSGAME.uproject`。CommonUI、EnhancedInput、PCG、PythonScriptPlugin、EditorScriptingUtilities、ModelingToolsEditorMode 等按描述符启用。`ModelContextProtocol` 与 `AllToolsets` 是额外编辑器工具，需要安装兼容 UE 5.8 的版本；不需要这些工具时可以在自己的 checkout 中关闭这两个 Editor 插件，再生成工程，切勿因此移除游戏模块依赖。

C++ 编译不需要先公开地图素材；成功编译也不意味着缺失地图/动画可以运行。恢复资源后用对应 `Tools` 脚本和真实游戏镜头验证；重建原生模块后启动新编辑器进程，避免旧模块仍在内存。

Windows 系统字体及其派生字体仅按工具中的本地用途处理，不随本仓库公开发布。现有天气来源说明见 [ThirdPartyNotices](../ThirdPartyNotices/WEATHER_ASSETS.md)。
''')
write('unreal/README.md', '''# UE5 历史迁移快照

2026-09-10 起，当前 UE 工程已移到仓库根目录：[FPSGAME.uproject](../FPSGAME.uproject)、[Source](../Source)。本目录保留此前迁移的脚本、来源及验收证据；不要把这里的旧 C++ 覆盖当前模块。

- [天气](weather-migration/README.md)
- [场景](scene-tests/README.md)
- [历史 AKM](akm-migration/README.md)
- [M4 手臂](m4-arms/README.md)

当前开发和发布规则见 [WORKFLOW](../WORKFLOW.md)。这些记录中的测试日期、宿主路径及源码散列属于对应历史批次。
''')
write('Docs/RepositoryMigration.md', f'''# UE5 仓库根目录切换 · 2026-09-10

基于远端 main `{BASE}`，用普通提交将当前文件树从 Godot 切换到 UE5；旧历史保留在 `archive/godot-before-ue5-20260910`，无强推或历史重写。

旧 Godot 工程、脚本、资源、测试及旧技能等 6199 个文件（4,551,481,865 字节）已从隔离发布目录移入本机 `E:/3d/trash/repository-ue5-root-20260910`。目录下的 `archive-manifest.json` 记录原路径、去向、大小和 SHA-256。原共享 `E:/3d/3-dfps` 和完整 UE 宿主保持原位置及运行内容。

当前根目录收录 UE 宿主的完整源码模块、targets、描述符、项目配置、JSON 数据及开发工具；忽略用户设置、缓存、插件/资源二进制和 trash。新增源码取样散列见 [SourceSnapshot.json](SourceSnapshot.json)，资源范围见 [AssetSetup](AssetSetup.md)。取样后的并行宿主修改不会自动进入此次提交。

保留 `unreal/` 作为迁移证据，当前可编译代码以根目录 `Source` 为准。此次不改变换弹动作或音效；此前动画结果属于既有验收，不能替代未来改动的真实音画检查。

本次验证结果见 [RepositoryValidation.json](RepositoryValidation.json)。旧 Godot 工程已退出当前分支；历史对象仍保留，因此正常完整 clone 的历史体积不会因为此提交立即缩小，可按需使用浅克隆。
''')

inventory=[]
for folder in sorted((HOST/'Content').iterdir()):
    if folder.is_dir():
        fs=[p for p in folder.rglob('*') if p.is_file()]
        inventory.append(dict(directory=folder.name, files=len(fs), bytes=sum(p.stat().st_size for p in fs)))
write('Docs/ContentInventory.json', json.dumps(inventory, ensure_ascii=False, indent=2))
write('Docs/SourceSnapshot.json', json.dumps(dict(captured_at=datetime.datetime.now().astimezone().isoformat(), host=str(HOST), base_commit=BASE, files=manifest),ensure_ascii=False,indent=2))
(AUDIT/'copied-source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(copied_files=len(manifest), copied_bytes=sum(r['repository_bytes'] for r in manifest)),ensure_ascii=False))
