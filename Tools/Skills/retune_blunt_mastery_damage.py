"""Replace blunt mastery flat damage with 1.25 percentage points per level."""
from pathlib import Path
import json
ROOT=Path('D:/FPS3D/FPSGAME')
WORK=ROOT/'SourceAssets/BluntMasteryDamage20261019'
PROGRESS=WORK/'source-progress.json'
DONE=json.loads(PROGRESS.read_text(encoding='utf-8')) if PROGRESS.exists() else []
def replace(s,a,b):
    if a not in s:raise RuntimeError('Missing edit anchor: '+a[:120])
    return s.replace(a,b)
def edit(rel,fn):
    if rel in DONE:return
    path=ROOT/rel;source=path.read_text(encoding='utf-8-sig');updated=fn(source)
    backup=WORK/'source-before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_text(source,encoding='utf-8')
    path.write_text(updated,encoding='utf-8');DONE.append(rel)
    PROGRESS.write_text(json.dumps(DONE,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    def data(s):
        root=json.loads(s);skill=root['bluntMastery']
        skill['damagePercentPerLevel']=.0125;skill['flatDamagePerLevel']=0
        skill['description']='熟练使用钝器武器，包括双手战锤。每级钝器武器伤害增加1.25%，20级增加25%；同时提升普通攻击速度。命中、同次多目标命中和直接击杀可修炼。'
        skill['balanceRevision']='2026-10-19: replace flat damage with 1.25% weapon damage per level, level 20 +25%; keep ordinary attack speed and training'
        return json.dumps(root,ensure_ascii=False,indent=2)+'\n'
    edit('Content/ColdSteelData/skills.json',data)
    edit('Source/FPSGAME/Skills/ColdSteelAdditionalMasteries.cpp',lambda s:replace(s,
        'if(ColdSteelSkills::IsMeleeMastery(Id))return Damage+MasteryEffect(Id).FlatDamage;',
        'if(ColdSteelSkills::IsMeleeMastery(Id))\n    {const auto E=MasteryEffect(Id);return Damage*(1.f+E.DamagePercent)+E.FlatDamage;}'))
    def notice(s):
        old='if(ColdSteelSkills::IsMeleeMastery(Definition->Id)){const auto E=ColdSteelSkills::Effect(*Definition,New->Level);N.Detail=FString::Printf(TEXT("%s固定伤害 +%.0f · 普攻速度 +%.1f%%"),*Definition->Name,E.FlatDamage,(1.f/FMath::Max(.05f,1.f-E.CooldownReduction)-1.f)*100);}'
        new='''if(ColdSteelSkills::IsMeleeMastery(Definition->Id))
        {
            const auto E=ColdSteelSkills::Effect(*Definition,New->Level);
            const float Speed=(1.f/FMath::Max(.05f,1.f-E.CooldownReduction)-1.f)*100;
            N.Detail=Definition->Id==TEXT("bluntMastery")?
                FString::Printf(TEXT("钝器伤害 +%.2f%% · 普攻速度 +%.1f%%"),E.DamagePercent*100,Speed):
                FString::Printf(TEXT("%s固定伤害 +%.0f · 普攻速度 +%.1f%%"),*Definition->Name,E.FlatDamage,Speed);
        }'''
        return replace(s,old,new)
    edit('Source/FPSGAME/Skills/ColdSteelSkillModel.cpp',notice)
    def ui(s):
        s=replace(s,'if(Index==0)return FString::Printf(TEXT("+%.0f%%"),E.DamagePercent*100);','if(Index==0)return SelectedSkill==TEXT("bluntMastery")?FString::Printf(TEXT("+%.2f%%"),E.DamagePercent*100):FString::Printf(TEXT("+%.0f%%"),E.DamagePercent*100);')
        s=replace(s,'if(!ColdSteelSkills::IsMeleeMastery(SelectedSkill))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("武器伤害倍率"),0)];','if(SelectedSkill!=TEXT("swordMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(SelectedSkill==TEXT("bluntMastery")?TEXT("钝器伤害增加"):TEXT("武器伤害倍率"),0)];')
        s=replace(s,'if(SelectedSkill!=TEXT("shotgunMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("固定伤害"),1)];','if(SelectedSkill!=TEXT("shotgunMastery")&&SelectedSkill!=TEXT("bluntMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("固定伤害"),1)];')
        old='''            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(ColdSteelSkills::IsMeleeMastery(SelectedSkill)
                ?TEXT("仅对应武器生效：刀剑精通适用双手刀剑，钝器精通适用所有钝器武器（包括双手锤）。1级固定伤害+1、普攻间隔−1%；每级再增加同等收益。20级固定伤害+20、普攻间隔−20%，等效普攻速度+25%。武技按自身公式继承武器伤害，动作、蓄力、冷却沿用独立规则；精通不缩短武技动作。两个精通独立成长，装备更换后按武器类型取值。")
                :SelectedSkill==TEXT("machineGunMastery")
                ?TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。精通加的力量计入角色属性；武器面板按原始分配与装备属性结算。持机枪类武器时移动速度 ×0.67（减速 33%），收起武器或改持其他武器即恢复。")
                :TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。精通加的属性计入角色属性；武器面板按原始分配与装备属性结算。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];'''
        new='''            FString Explanation;
            if(SelectedSkill==TEXT("bluntMastery"))
            {
                const auto& D=Definition(SelectedSkill);
                Explanation=FString::Printf(TEXT("适用所有钝器武器（包括双手锤）。伤害加成＝等级×%.2f%%：1级+%.2f%%，每升一级增加%.2f个百分点，%d级+%.2f%%；替换原固定伤害加成。普通攻击间隔每级减少%.1f%%，%d级等效普攻速度+%.1f%%。武技按原公式继承武器伤害，动作、蓄力和冷却继续使用独立规则。原等级与经验保留，无需重新修炼。"),
                    D.DamagePercentPerLevel*100,D.DamagePercentPerLevel*100,D.DamagePercentPerLevel*100,D.MaxLevel,D.DamagePercentPerLevel*D.MaxLevel*100,
                    D.CooldownReductionPerLevel*100,D.MaxLevel,(1.f/FMath::Max(.05f,1.f-D.CooldownReductionPerLevel*D.MaxLevel)-1.f)*100);
            }
            else if(SelectedSkill==TEXT("swordMastery"))
                Explanation=TEXT("仅双手刀剑生效。1级固定伤害+1、普攻间隔−1%；每级再增加同等收益。20级固定伤害+20、普攻间隔−20%，等效普攻速度+25%。武技按自身公式继承武器伤害，动作、蓄力、冷却沿用独立规则；精通不缩短武技动作。与钝器精通独立成长，装备更换后按武器类型取值。");
            else if(SelectedSkill==TEXT("machineGunMastery"))
                Explanation=TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。精通加的力量计入角色属性；武器面板按原始分配与装备属性结算。持机枪类武器时移动速度 ×0.67（减速 33%），收起武器或改持其他武器即恢复。");
            else Explanation=TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。精通加的属性计入角色属性；武器面板按原始分配与装备属性结算。");
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(Explanation,12,ColdSteelUI::TextTertiary,PageWidth-44)];'''
        return replace(s,old,new)
    edit('Source/FPSGAME/UI/ColdSteelSkillPage.cpp',ui)
    print('Updated blunt mastery damage growth, gameplay formula, skill details and upgrade notices.')

if __name__=='__main__':main()
