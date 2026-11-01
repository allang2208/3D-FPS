"""Idempotent M24-only optional bipod catalog recipe."""
import copy
ID='m24_foldable_bipod'
OPTIONS=[{'id':'false','name':'不安装脚架','description':'保留原装枪管与护木。','effects':[],'stats':{},'special_effects':[]},
 {'id':ID,'name':'M24 折叠脚架','description':'双腿金属脚架，收起时沿枪管下侧前折，夹环固定在护木前方。',
 'effects':[],'stats':{},'special_effects':['架枪｜静止靠近有效支撑面时瞄准，由左手展开脚架并落位；取消瞄准时收起。',
 '架设状态｜后坐力-66%，稳定性+66%，散布-45%；展开和收起期间不可开火。']}]
def apply(row):
    if 'bipod' not in row['allowed']:row['allowed'].append('bipod')
    row['default_parts']['bipod']='false';row['options']['bipod']=copy.deepcopy(OPTIONS)
