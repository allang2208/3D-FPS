"""Shared production settings for the original leather glove equipment."""
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/ModularOutfit20260927/OriginalLeatherV1'
DEST = '/Game/Characters/ModularOutfit20260927/OriginalLeatherV1'
ITEM = 'ue_original_gloves'
ICON = 'Icons/ModularOutfit20260927/ue_original_gloves.png'
DESCRIPTION = '沿用旧式战术手套的棕皮革，贴合掌指，掌面防滑，腕口以卷边和缝线收束。可单独穿戴，也可搭配上衣；脱下后露出双手。'
PARAMETERS = {
    'TintAmount': 0.0,
    'LeatherNormalStrength': 0.32,
    'PalmGrainScale': 0.22,
    'LeatherAOAmount': 0.22,
    'LeatherCavityAmount': 0.14,
    'WearAmount': 0.35,
    'GloveSpecular': 0.32,
}


def read(path):
    import json
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
