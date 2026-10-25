"""Owned delivery settings for the two detailed combat belts."""
import hashlib,json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/CombatBeltsIntegration20261025'
BELTS={
    'melee':dict(key='ue_melee_combat_belt',name='破阵近战腰带',stem='MeleeCombatBelt',family='MeleeCombatBelt20261025',
        description='由近战巡卫使用的分段护腰，暗红棕皮革与炭黑织带承托斜切扣具、双点刀鞘挂架和磨刀石袋。它帮助使用者保持出手节奏、节省连续挥击的体力，侧挂组件为装备结构，不提供额外收纳格。'),
    'arcane':dict(key='ue_arcane_conduit_belt',name='星律导能腰带',stem='ArcaneConduitBelt',family='ArcaneConduitBelt20261025',
        editable_directory=str(P/'SourceAssets/ArcaneConduitBelt20261025/ModelR2/Exports'),
        description='星律研究会为随队术士制作的导能腰带，以靛蓝皮革承托双环星盘与凹嵌紫晶，侧置符片匣和卷轴筒。符文回路缩短魔法冷却并节省施法法力，适合持续施法；侧挂容器为外观组件，不增加收纳格。')}

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def source(row):return P/'SourceAssets'/row['family']/'ModelR1'
def destination(row):return '/Game/Characters/ModularOutfit20260924/'+row['family']+'/IntegrationR1'
