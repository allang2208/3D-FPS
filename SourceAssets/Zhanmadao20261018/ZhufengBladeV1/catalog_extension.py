"""Keep Zhufeng gameplay tuning on its rune when republishing older sources."""
def extend(catalog):
    catalog['slots']['blade_1'].pop('zhufeng', None)
    catalog.pop('zhufeng_blade_revision', None)
    return catalog

def extend_option(entry):
    entry.update(id='zhufeng_rune',name='逐风符文',tier='legendary',weapons=['ue_zhanmadao'],stats={'range_mult':1.2,'physical_damage_mult':1.1,'whirlwind_damage_add':0.5},
        description='斩马刀专属传说符文。青碧的逐风二字纵铭于刀身中段，随旋风斩泛起青色剑气。',
        effects=[{'text':'攻击距离+20%','benefit':1},{'text':'物理伤害+10%','benefit':1}],
        special_effects=[
            '逐风旋斩｜冲刺攻击释放向前匀速推进的次级旋风，只旋转一圈，旋转速度+50%；旋转结束或受阻时停止推进，每个目标仅命中一次。',
            '次级旋风｜伤害与体力消耗沿用冲刺攻击，满足冲刺攻击释放条件即可施放；无冷却，与主动大旋风冷却独立。',
            '旋风强化｜主动大旋风伤害倍率+0.5；主动与次级旋风均显现青色剑气。'])
    return entry
