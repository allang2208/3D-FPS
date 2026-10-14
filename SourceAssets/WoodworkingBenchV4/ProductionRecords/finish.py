from pathlib import Path
import json,hashlib,shutil,datetime
W=Path(__file__).resolve().parent;P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/WoodworkingBenchV4';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((W/'register_exit.json').read_text())['exitCode']==0
reg=json.loads((W/'palette_readback.json').read_text());assert reg['unique_woodworking_id'] and reg['category']=='other'
baseline=json.loads((W/'baseline.json').read_text());unchanged=[]
for rel,data in baseline.items():
    if rel.startswith('Content/Building/WoodworkingBenchV2/') or rel in ['Content/ColdSteelData/woodworking.json','SourceAssets/WoodworkingBenchV2/registration.json']:
        assert sha(P/rel)==data['sha256'],('Protected asset/config changed',rel);unchanged.append(rel)
code=json.loads((W/'code_publish_receipt.json').read_text())
for item in code['files']:assert sha(P/item['path'])==item['sha256'],('Concurrent code change after build',item['path'])
assets=json.loads((W/'installed_assets.json').read_text())
for item in assets['assets']:assert sha(P/item['path'])==item['sha256'],('Installed V4 package changed',item['path'])
logs=['Saved/BuildSurvival20261003/FPSGAMEEditor-20261008-223036.log','Saved/BuildSurvival20261003/FPSGAME-20261008-223056.log']
builds=[]
for rel in logs:
    p=P/rel;s=p.read_text(encoding='utf-8',errors='replace');assert 'Result: Succeeded' in s
    builds.append({'log':rel,'sha256':sha(p),'modified_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'result':'Succeeded'})
binaries=[]
for rel in ['Binaries/Win64/UnrealEditor-FPSGAME.dll','Binaries/Win64/FPSGAME.exe']:
    p=P/rel;binaries.append({'path':rel,'sha256':sha(p),'bytes':p.stat().st_size,'modified_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()})
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'registration':reg,'builds':builds,'binaries_observed_at_completion':binaries,'protected_files_unchanged':unchanged,'asset_files':len(assets['assets']),'asset_bytes':sum(x['bytes'] for x in assets['assets']),'gameplay_tested':False,'visual_acceptance_run':False,'maps_saved':False,'user_savegames_written':False,'git_commit_push':False,'warnings':['Source Blender 5.2 evaluated in Blender 5.1.2; source object/triangle counts match.','432 zero-area source triangles omitted by UE; confirmed by static source audit.','427 nonzero-area triangles have degenerate UVs: 415 original table material faces, 12 props atlas faces. Import warns of near-zero tangent/binormal; rendered appearance has not been validated.','Transparent guard is a game translucent approximation of source transmission; no rendered acceptance.','Initial Editor build failed during concurrent dungeon PreSave change; after the external definition appeared, Editor and Game succeeded. No dungeon files edited by this task.']}
(W/'completion_audit.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
records=R/'ProductionRecords';records.mkdir(exist_ok=True)
for p in W.iterdir():
    if p.is_file() and p.suffix in {'.py','.ps1','.json','.log'}:shutil.copy2(p,records/p.name)
for rel in logs:shutil.copy2(P/rel,records/Path(rel).name)
for name in ['WoodworkingSawVisualComponent.h','WoodworkingSawVisualComponent.cpp']:shutil.copy2(P/'Source/FPSGAME/Building'/name,records/name)
doc=P/'Docs/Building/woodworking-bench-v4-import-20261008.md';assert not doc.exists()
doc.write_text('''# 木工工作台 V4 台锯接入（2026-10-08）

用户放入固定 Input 目录的 Core.zip 已确认是 V4：1,972,105 字节，SHA256 `1153eadc9aea9b22edb40b46da816b437b5cd1b022f25a09a074f9cea0941781`。本轮从完整 `WoodworkingBench_Editable.blend` 接入，不以仅新增机构的 Assembly 文件覆盖桌体；未恢复已否决的 V3 手锯收纳架。

## 来源与资产

- 原始 ZIP、两个既有纹理 ZIP 和解包母版：`SourceAssets/WoodworkingBenchV4/Input`、`Source`。原始母版保持未改写。
- 完整母版 423 个对象、168,432 个评估三角面。保留开槽桌板、铝制台面、下置电机、封闭传动和透明护罩。
- 游戏导出：`SourceAssets/WoodworkingBenchV4/GameReady`，包含可编辑游戏版、三套 FBX × 三级 LOD、19 张贴图和 `game_manifest.json`。
- 正式资产：`/Game/Building/WoodworkingBenchV4`，29 个包（19 纹理、7 材质、3 网格），旧 V2 包全部保留。
- `SM_WoodworkingBench` 是带静止锯片的完整预览/加载回退；`SM_WoodworkingBenchBody` 是去锯片主体；`SM_WoodworkingSawBlade` 是独立锯片。
- 五个原桌体材质保留原纹理和图表参数；程序材质烘焙为 BaseColor、切线 Normal、ORM、Emissive。法线导入翻转绿色通道。三片透明罩使用独立半透明表面，opacity=.12、roughness=.08；这是游戏转换，不声称与离线折射完全一致。

## 装配与放置

- Blender 米 → UE 厘米，静态轴向读回确认 X→X、Y→−Y、Z→Z。主网格约 241.822×264.753×180.115 cm，与 V2 相同；占地 13×14×10 格，沿用 20 cm 格合同。
- 锯片直径 32.4 cm，厚 .4 cm；原点移至源枢轴 (.865,0,.888)m。主网格 `WoodworkingSawPivot` 挂点为 (86.5,0,88.8)cm，沿本地 X 旋转，随摆放四向旋转和父组件移动。
- 桌板和插板保留真实 2.5×37.5 cm 开槽。23 个凸碰撞分体保留 L 形内侧净空、腿和架层，并分开锯槽两侧；独立锯片无碰撞，主体保持 SimpleAndComplex 以支持现有脱落物理。
- 正式调色板 `Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset` 中仍只有一个 `woodworking_bench`，入口为 B → 其他 → 木工工作台。其余条目保持，正式登记前备份位于 `SourceAssets/WoodworkingBenchV4/RegistrationReceipts`。

## 运行代码

`Building/WoodworkingSawVisualComponent.*` 只负责单机本地表现。构件放置后异步预载去锯片主体和独立锯片，资源齐全才替换完整预览，缺失时保留完整静态回退；闲置无 Tick，开机时每秒最多 60 次更新。绑定真实挂点，不使用世界硬编码位置。关闭/放弃窗口、失去组件或构件开始物理下落时停转；销毁时取消加载并释放组件。

`ColdSteelWoodworkingWidget` 将现有 `MotorRunning()` 状态同步给该构件。既有像素裁切、时间/质量、撤销、奖励事务与 woodworking.json 本轮不改；开发练习面板没有真实工作台时不会驱动场景锯片。该组件不声明多人复制，也不把视觉转速作为切割判定。

## 完成证据与边界

ProductionRecords 保存本轮源包、导入、LOD 最终落盘、注册读回、代码安装及编译回执。完整主网格 UE LOD 三角数为 168000/92204/39990，去片主体为 166720/91500/39683，锯片保持 1280/1280/1280；屏幕阈值 1/.45/.18。432 个源零面积三角面由 UE 省略，与静态几何审计相符，没有以该数值宣称主动近景减面。

Editor 构建日志 `Saved/BuildSurvival20261003/FPSGAMEEditor-20261008-223036.log`、Game 构建日志 `FPSGAME-20261008-223056.log` 均为 Succeeded。首次构建受到并行地牢 PreSave 定义变动影响，其他工作补齐该定义后重建成功；本轮未修改地牢源码。

仍有 427 个非零面积三角面的 UV 退化（原桌体材质 415、烘焙图集 12），导入记录近零切线/副法线告警。未运行渲染，不能将静态尺寸、材质连接和编译通过视作视觉验收。源文件来自 Blender 5.2，使用本机 5.1.2 评估时有新版本提示，已核对对象/面数与母版一致。

本轮未启动游戏或 PIE，未执行交互/性能测试、截图或真实存档写入，未保存地图，未进行 Git 提交或推送。V2 备份和修改前源码位于本次执行目录 `woodworking_v4_import_20261008/Before`；正式登记脚本已转为 V4 防止后续注册恢复到 V2。
''',encoding='utf-8')
print('V4_COMPLETE',json.dumps({'doc':str(doc),'asset_files':29,'protected_unchanged':len(unchanged),'builds':builds},ensure_ascii=False))
