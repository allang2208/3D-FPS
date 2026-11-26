"""Record actual production and integration, without implying gameplay testing."""
import json,hashlib
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';B=P/'SourceAssets/BackpackFit20261024/ModernTacticalShirtR320261114'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
if (R/'CuffRepairR1/pending.json').exists() and not (R/'CuffRepairR1/published.json').exists():raise RuntimeError('First-person cuff refinement remains in progress')
wear=read(R/'saved.json');art=read(R/'artwork-saved.json');release=read(R/'published.json');packs=read(B/'published.json');pack_saved=read(B/'saved_assets.json')
if not all([wear.get('completed'),art.get('completed'),release.get('completed'),pack_saved.get('completed'),packs.get('status')=='saved_and_integrated']):raise RuntimeError('Asset production and local integration remain incomplete')
record=dict(completed=True,completed_at=datetime.now().astimezone().isoformat(),revision=R.name,wear_assets=len(wear['wear']),materials=len(wear['materials']),display_and_drop_assets=4,inventory_icons=2,backpack_pairs=packs['variants'],backpack_statics=packs['statics'],native_first_person_profiles=len(read(R/'fp-authored.json')['rows']),inventory_regrant=False,gameplay_tested=False,network_tested=False,runtime_cloth_simulation=False,concept_identical=False,necklines={rig:read(R/'Authored'/f'shirt_detail_{rig}.json')['neckline'] for rig in ['Jason','Kaitlin']},textile_sources=['https://polyhaven.com/a/stretch_poplin','https://polyhaven.com/a/bi_stretch'],license='CC0',shading='UE Cloth shading model, photographic textile normal and roughness, authored ripstop reinforcement',artwork_sha256={name:hashlib.sha256((R/'Icons'/name).read_bytes()).hexdigest() for name in ['ue_modern_kevlar_vest.png','ue_modern_tactical_pants.png']},cuff_revision='CuffRepairR1',receipts=dict(cuffs=str(R/'CuffRepairR1/published.json'),garments=str(R/'saved.json'),artwork=str(R/'artwork-saved.json'),local_config=str(R/'published.json'),backpacks=str(B/'published.json')))
(R/'delivered.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'README.md').write_text('''# TS01 CombatShirt R3 — 低圆领与实体布料褶皱

本轮重新制作男女上衣的袖片褶皱、裤腿褶皱和低圆领。原生身体及各武器手臂分别作为离线布料碰撞面，以裁片余量、缝边固定和重力得到实体褶皱，再将结果回写原生蒙皮；游戏中没有新增实时布料模拟。内外布层、缝线和附着口袋随同一变形场移动。24 套第一人称路线均重新读取当前原生裸臂，Body 路线也使用自己的实际原生皮肤。袖口固定点不再使用会移动目标位置的 rest shape key；布料余量通过弹簧长度设置施加在自由袖身。输入完全相同的网格、碰撞面和约束才复用离线计算结果。

第一人称袖口还按当前各型号手套的腕带外缘重新裁制，绕开腕带扣并保留覆盖；26 套手套将悬空腕带贴合到各自实际手套表面，并修正这部分的前臂支撑权重。Body 和 Super90 路线另外按各自当前原生皮肤修整了过宽的手套腕筒。全身上衣保留原生腕口覆盖长度；内外布层和缝线配对，腕口以跟随前臂为主，边缘少量跟随手腕，不受手指骨骼牵拉。实际保存的袖口几何从 LOD 0、1、2 渲染网格读回，蒙皮权重从已保存的 LOD 0 源模型读取，结果见 `CuffRepairR1/Review/Saved/`。引擎的渲染网格读取接口不提供蒙皮属性，因此没有将源模型权重记为渲染权重。这些是源网格和保存后资产的局部检查，不是动作或游戏验收。正式生产入口已切换到固定腕口流程。

领口从原贴颈高度降低为前低后略高的圆领。裤腰保留原生贴合范围；普通裤及四类裤靴衔接继续使用原来的配对高度，避免褶皱移动已解决的覆盖区域。服装沿用原物品 ID，未重复发放。

材质以 Poly Haven 的 Stretch Poplin 和 Bi Stretch 摄影织物 PBR 为来源，统一染为土棕色及深棕弹力布，另制作防撕裂双加强线。原始摄影织物资料、许可证和来源记录位于 `Sources/`，六组 2K 游戏贴图位于 `Textures/`，物理高度场位于 `Bakes/`。纹理实物尺度为 28.8 cm；现有 8 cm UV 合约通过 8/28.8 倍率接入。UE 使用 Cloth 着色模型，NormalGL 导入时翻转绿通道，粗糙度和金属度从 ORM 读取，织物金属度为零。

来源：<https://polyhaven.com/a/stretch_poplin>、<https://polyhaven.com/a/bi_stretch>；CC0：<https://polyhaven.com/license>。摄影来源并非原始防撕裂扫描，加强线为本轮制作。

`Models/`、`Exports/` 保存男女原生游戏模型及作者高模，`Simulation/` 保存离线布料源文件。`Icons/` 的 480×480 上衣防弹衣图标、320×480 裤子图标由实际空服装模型制作，保持透明背景与原背包格数。

实际已保存资产与接入回执见 `delivered.json`。未启动 UE 编辑器、PIE 或游戏进行测试；动作、第一人称观感及联机表现由用户测试。此交付不声称与概念图像素级一致。
''',encoding='utf-8')
overview=S/'README.md';text=overview.read_text(encoding='utf-8');heading='## CombatShirt R3：低圆领、实体褶皱与织物材质'
if heading not in text:
    text+='\n'+heading+'\n\n新版以离线布料裁片余量、原生碰撞面和缝边约束制作褶皱，降低领口并将摄影织物 PBR 接入 UE Cloth 材质。已保存并接入男女服装、24 套原生第一人称袖子、裤靴配对、标准背包图标及七款背包配对。实际回执与来源见 `CombatShirtR3/delivered.json` 和 `CombatShirtR3/README.md`。未启动游戏测试。\n';overview.write_text(text,encoding='utf-8')
print('TS01_COMBAT3_DELIVERED',record['wear_assets'],record['backpack_pairs'],flush=True)
