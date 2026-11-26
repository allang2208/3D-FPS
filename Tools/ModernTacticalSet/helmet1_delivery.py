"""Record the actual saved helmet delivery; no gameplay or acceptance run."""
import json, hashlib
from pathlib import Path
from datetime import datetime

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ModernTacticalSet20261113/HelmetDetailR1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'saved.json');published=read(R/'published.json');art=read(R/'artwork.json')
if not all(d['completed'] for d in [saved,published,art]):
    raise RuntimeError('Finish saving and publishing before writing delivery receipt')
models=[read(R/f'authored-{rig}-{stage}.json') for rig in ['Jason','Kaitlin'] for stage in ['GAME','HIGH']]
record=dict(completed=True,completed_at=datetime.now().astimezone().isoformat(),revision='HelmetDetailR1',
    item='ue_modern_tactical_helmet',models=models,meshes=saved['meshes'],materials=saved['materials'],
    textures=saved['textures'],icon=art['icon'],publication=str(R/'published.json'),
    asset_save_log=str(P/'SourceAssets/ModernTacticalSet20261113/Integration/Logs/helmet1-save-uvfinish-20261115-1238.log'),
    asset_host=str(R/'AssetHost/HelmetAssetHost.uproject'),
    source_scripts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (P/'Tools/ModernTacticalSet').glob('helmet1_*') if p.suffix in ['.py','.ps1']},
    tests_performed=False,gameplay_tested=False,editor_started=False,inventory_regrant=False)
(R/'delivered.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {m['rig']} | {m['stage']} | {m['triangles']:,} | {len(m['parts'])} |" for m in models)
assets='\n'.join(f"- {k}: `{v['asset']}`" for k,v in saved['meshes'].items())
text=f'''# TS01 战术头盔精修 HelmetDetailR1

已在后台制作、导入、保存并接入现有物品 `ue_modern_tactical_helmet`。维持套装的土棕色方案。

## 制作内容

- 连续复合盔壳具有 0.65 cm 实体厚度、开放的头腔与连续橡胶包边。
- 两侧导轨具有实际贯穿槽、滑轨唇边、定位刻线和内六角螺钉。
- 前方三点支座具有真实开口、凹入接收部、金属导向件与锁扣。
- 曲面绒面布贴、包边、七块内垫、四点悬挂织带、带扣、下颏垫及后脑调节旋钮。
- 布贴直线边也沿盔壳细分贴合，避免长弦陷入曲面形成缺口。
- 织带先展开经纬贴图再生成厚度，正反面保持完整布纹，厚度边缘单独展开。
- Jason 与 Kaitlin 使用各自当前原生头部和身体 head 骨坐标独立制作，佩戴资产写入原生 head 局部空间。

## 模型与材质

| 头型 | 源模型用途 | 三角面 | 独立部件 |
| --- | --- | ---: | ---: |
{rows}

`Models` 保留 GAME 和 HIGH Blender 源文件；`Exports` 保留两套 GAME FBX/GLB。
七组 PBR 材质分别描述复合壳体、聚合物、橡胶、织带、绒面布贴、网布内垫与金属。
复合壳体使用 2048 像素贴图，其余材质使用 1024 像素贴图；每组包含 BaseColor、NormalGL、ORM。
微表面源保存在 `SurfaceSources`。这是按物理尺寸制作的微高度材质，不是扫描材质，也不是整盔 HIGH 到 GAME 烘焙。
UE 法线按 DirectX 方向导入，保留源模型法线并生成切线，三档 LOD 的目标比例为 100% / 70% / 45%。

## 接入和图标

{assets}

标准背包图标为实际空头盔模型制作的 320×320 RGBA 图，保持 2×2 格，使用已有标准相机和 91% 构图填充。
同步更新背包静态图、三维预览模型、掉落模型和两个角色的头盔挂接引用。
物品 ID、属性数值、装备槽位与现有背包内容保持原样，没有重复发放。

`saved.json` 记录实际 UE 保存结果，`published.json` 记录配置发布，`before.json` 保留原引用。
本轮未启动交互式 UE、PIE 或游戏，未进行测试或验收；交由用户在游戏中体验。
'''
(R/'README.md').write_text(text,encoding='utf-8')
print('HELMET_DETAIL_DELIVERED',flush=True)
