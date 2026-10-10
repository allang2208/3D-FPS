"""Current staff copy standard; apply without regenerating models or gameplay data."""
import json
from pathlib import Path

COPY = {
    'frozen_crystal': ('白色冰晶保留冷硬棱面与清晰冰脊。', []),
    'magma_core': ('不规则熔岩球以深色岩壳包裹炽热裂隙。', []),
    'jade_spirit_crystal': ('翠绿晶体嵌入杖头，棱面映出柔和灵光。', [
        '续疗｜圣光治疗友方后附加1层续疗，并增加3秒持续时间；每层每秒恢复1%最大生命。']),
    'storm_core': ('紫色晶壳包裹不断变幻的闪电核心。', []),
    'spike_crown': ('冰刺沿杖冠向外生长，形成尖锐轮廓。', [
        '冰系共鸣｜匹配冰系杖头时，冰系法术伤害+25%。']),
    'current_crown': ('金属杖冠环绕细密电光。', [
        '电系共鸣｜匹配电系杖头时，电系法术伤害+25%。']),
    'wreath_crown': ('花环沿杖冠交织，流露柔和圣光。', [
        '光系共鸣｜匹配光系杖头时，光系法术治疗量+25%。']),
    'heat_crown': ('杖冠边缘泛出炽热的熔光。', [
        '火系共鸣｜匹配火系杖头时，火系法术伤害+25%。']),
    'eagle_eye_rune': ('鹰眼纹样沿杖身展开。', []),
    'crit_rune': ('锐利符纹刻入杖身表面。', []),
    'storm_rune': ('旋转风暴纹样刻入杖身。', []),
    'alloy_grip': ('合金衬片包覆握柄，边缘保留细密金属纹理。', []),
    'pine_grip': ('松木握柄保留清晰木纹。', [
        '链式强化｜施法后获得1层强化并增加10秒持续时间；下次施法消耗已有层数，每层使法术伤害+2%、耗蓝+5%。']),
    'sandalwood_grip': ('深色檀木包覆握柄，表面温润细密。', [
        '余韵加速｜施法后获得1层移动加速，并增加5秒持续时间。']),
    'ice_soul_pendant': ('冰晶尾坠悬于杖尾，透出冷色微光。', [
        '寒冷｜冰系法术造成伤害时附加1层寒冷，并增加3秒持续时间；每层使移速-5%。']),
    'thunder_bell': ('金属铃坠环绕细微电光。', [
        '震慑｜电系法术造成伤害时附加0.25秒眩晕；目标已眩晕时延长0.25秒。']),
    'purification_vine': ('净化藤蔓沿杖尾缠绕垂落。', [
        '净化加速｜光系法术治疗友方时赋予2层移动加速；每层增加5秒持续时间。']),
    'flame_pendant': ('炽红尾坠包裹暗色金属边框。', [
        '灼伤｜火系法术造成伤害时附加灼伤，持续3秒。']),
    'chain_mana': ('链式导魔纹路沿杖身交错延伸。', []),
    'direct_mana': ('笔直导魔纹路贯穿杖身。', []),
}


def apply_copy(catalog):
    for column in catalog['columns']:
        for option in column['options']:
            copy = COPY.get(option['id'])
            if copy is not None:
                option['description'], effects = copy
                option['special_effects'] = list(effects)
    return catalog


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[2] / 'Content/ColdSteelData/staff-gunsmith.json'
    catalog = json.loads(path.read_text(encoding='utf-8-sig'))
    apply_copy(catalog)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Staff attachment descriptions saved; gameplay values and asset paths preserved.')
