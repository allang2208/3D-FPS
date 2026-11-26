"""Record completed, actual local garment and backpack production receipts."""
import json,hashlib
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR2';B=P/'SourceAssets/BackpackFit20261024/ModernTacticalShirtR220261114'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
wear=read(R/'saved.json');art=read(R/'artwork-saved.json');published=read(R/'published.json');packs=read(B/'published.json');pack_saved=read(B/'saved_assets.json')
if not all([wear.get('completed'),art.get('completed'),published.get('completed'),pack_saved.get('completed'),packs.get('status')=='saved_and_integrated']):raise RuntimeError('Complete actual saves and local integrations before delivery')
record=dict(completed=True,completed_at=datetime.now().astimezone().isoformat(),revision=R.name,wear_assets=len(wear['wear']),materials=len(wear['materials']),display_and_drop_assets=4,inventory_icons=2,backpack_pairs=packs['variants'],backpack_statics=packs['statics'],inventory_regrant=False,source_game_models=['TS01_CombatShirt_Jason.blend','TS01_CombatShirt_Kaitlin.blend','TS01_CombatTrousers_Jason.blend','TS01_CombatTrousers_Kaitlin.blend'],native_first_person_profiles=len(read(R/'fp-authored.json')['rows']),gameplay_tested=False,network_tested=False,concept_identical=False,concept_differences=['Higher native-fit neckline','Less relaxed fold density than the concept'],calf_reference_pose={rig:read(R/'Review'/f'lower-{rig}-after.json') for rig in ['Jason','Kaitlin']},artwork_sha256={name:hashlib.sha256((R/'Icons'/name).read_bytes()).hexdigest() for name in ['ue_modern_kevlar_vest.png','ue_modern_tactical_pants.png']},receipts=dict(garments=str(R/'saved.json'),artwork=str(R/'artwork-saved.json'),local_config=str(R/'published.json'),backpacks=str(B/'published.json')))
(R/'delivered.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
overview=S/'README.md';text=overview.read_text(encoding='utf-8')
heading='## CombatShirt R2：配套上衣与裤靴覆盖重制'
if heading not in text:
    text+='\n'+heading+'\n\n'
    text+='配套土棕色作战上衣已建模并随原防弹衣物品接入。新版源文件、贴图和说明位于 `CombatShirtR2/`；旧的无袖 `body_only` 登记已替换为原生衣袖路线，原手套修复继续保留。裤装改用连续身体变形场，保留既有裤腰并新增战术靴专用搭接。\n\n'
    text+=f"已保存 {record['wear_assets']} 个穿戴资产、4 个掉落／图标展示模型及两张标准透明图标。七款背包在男女身体上的 {record['backpack_pairs']} 个配对已保存并按字段接入，见 `CombatShirtR2/delivered.json`。原物品 ID 和库存保留，没有重复发放。\n\n"
    text+='这版仍不是概念图的 100% 复刻：原生贴合领口较高，松褶数量较少。已完成用户要求的裤靴参考姿态缺陷处理；未启动游戏或 PIE，动作和联机效果由用户测试。\n'
    overview.write_text(text,encoding='utf-8')
print('TS01_COMBAT2_DELIVERED',record['wear_assets'],record['backpack_pairs'],flush=True)
