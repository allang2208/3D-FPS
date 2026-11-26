"""Task-scoped melee mastery integration; preserve unrelated shared edits."""
from pathlib import Path
import json
ROOT=Path('D:/FPS3D/FPSGAME')
WORK=ROOT/'SourceAssets/MeleeMasteries20261019'
PROGRESS=WORK/'source-progress.json'
DONE=json.loads(PROGRESS.read_text(encoding='utf-8')) if PROGRESS.exists() else []
def rep(s,a,b):
    if a not in s:raise RuntimeError('Missing edit anchor: '+a[:150])
    return s.replace(a,b)
def inc(s,path):
    line=f'#include "{path}"\n'
    if line in s:return s
    end=s.index('\n',s.index('#include '))+1
    return s[:end]+line+s[end:]
def edit(rel,fn):
    if rel in DONE:return
    path=ROOT/rel;s=path.read_text(encoding='utf-8-sig');out=fn(s)
    backup=WORK/'source-before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_text(s,encoding='utf-8')
    path.write_text(out,encoding='utf-8');DONE.append(rel)
    PROGRESS.write_text(json.dumps(DONE,ensure_ascii=False,indent=2),encoding='utf-8')

def run():
    def config(s):
        data=json.loads(s);sword=data['swordMastery']
        sword['name']='刀剑精通';sword['description']='熟练使用双手刀剑，提高对应武器的固定伤害与普通攻击速度；命中、同次多目标命中和直接击杀可修炼。'
        sword['icon']='Skills/blade_mastery_cold_steel.png'
        sword['balanceRevision']='2026-10-19: two-handed swords and sabers only; preserve swordMastery progress; no cross-family flat damage'
        blunt=dict(sword);blunt.update(name='钝器精通',description='熟练使用钝器武器，包括双手战锤，提高固定伤害与普通攻击速度；命中、同次多目标命中和直接击杀可修炼。',icon='Skills/blunt_mastery_cold_steel.png',source='FPSGAME: parallel progression to swordMastery',balanceRevision='2026-10-19: all weapon_melee/blunt weapons; separate progress; ordinary attack interval only')
        data['bluntMastery']=blunt
        return json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    edit('Content/ColdSteelData/skills.json',config)
    def rules_h(s):
        return rep(s,'    FPSGAME_API bool IsCriticalHit(const FHitResult& Hit);','    FPSGAME_API bool IsCriticalHit(const FHitResult& Hit);\n    inline bool IsMeleeMastery(FName Id){return Id==TEXT("swordMastery")||Id==TEXT("bluntMastery");}\n    FPSGAME_API bool IsMasteryTrainingTarget(AActor* Shooter,AActor* Target);')
    edit('Source/FPSGAME/Skills/ColdSteelSkillRules.h',rules_h)
    def rules(s):
        s=inc(s,'../Monsters/MonsterCombatComponent.h')
        s=rep(s,'if (P.SkillProgressVersion >= 24) return false;','if (P.SkillProgressVersion >= 25) return false;\n    P.Skills.FindOrAdd(TEXT("bluntMastery"));\n    if(P.SkillProgressVersion==24){P.SkillProgressVersion=25;return true;}')
        s=s.replace('P.SkillProgressVersion=24;','P.SkillProgressVersion=25;').replace('P.SkillProgressVersion>24','P.SkillProgressVersion>25')
        s=rep(s,'    if(P.SkillProgressVersion>=24&&','    if(P.SkillProgressVersion>=25&&!P.Skills.Contains(TEXT("bluntMastery"))){Reason=TEXT("钝器精通进度缺失");return false;}\n    if(P.SkillProgressVersion>=24&&')
        s=rep(s,'if(D.Id==TEXT("swordMastery")||D.Id==TEXT("machineGunMastery")','if(IsMeleeMastery(D.Id)||D.Id==TEXT("machineGunMastery")')
        s+='\nbool ColdSteelSkills::IsMasteryTrainingTarget(AActor* Shooter,AActor* Target)\n{\n    const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;\n    return Combat&&!Combat->IsDead()&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"))\n        &&UFPSMeleeLightningComponent::IsEnemy(Target,Shooter);\n}\n'
        return s
    edit('Source/FPSGAME/Skills/ColdSteelSkillRules.cpp',rules)
    edit('Source/FPSGAME/UI/ColdSteelStatusModel.h',lambda s:rep(s,'    FName WeaponMastery(const FColdSteelItem* Item) const;','    FName WeaponMastery(const FColdSteelItem* Item) const;\n    float MeleeMasteryIntervalMultiplier(const FColdSteelItem& Item) const;'))
    def masteries(s):
        s=rep(s,'FName(TEXT("swordMastery")),FName(TEXT("machineGunMastery"))','FName(TEXT("swordMastery")),FName(TEXT("bluntMastery")),FName(TEXT("machineGunMastery"))')
        s=rep(s,'if(Type==TEXT("sword")||Item->Definition==TEXT("ue_rune_sword"))return TEXT("swordMastery");','if(ColdSteelInventory::IsTwoHandedSword(*Item))return TEXT("swordMastery");\n    if(Type==TEXT("blunt")&&ColdSteelInventory::Text(*Item,TEXT("category"))==TEXT("weapon_melee"))return TEXT("bluntMastery");')
        s=rep(s,'    // Source computeWeaponAttack adds sword mastery before category-specific mastery.\n    const double FlatScale=ColdSteelBow::DamageCoefficientScale(Item);\n    Damage+=MasteryEffect(TEXT("swordMastery")).FlatDamage*FlatScale;\n    const FName Id=WeaponMastery(&Item);','    const double FlatScale=ColdSteelBow::DamageCoefficientScale(Item);\n    const FName Id=WeaponMastery(&Item);\n    if(ColdSteelSkills::IsMeleeMastery(Id))return Damage+MasteryEffect(Id).FlatDamage;')
        return s+'\nfloat UColdSteelStatusModel::MeleeMasteryIntervalMultiplier(const FColdSteelItem& Item) const\n{\n    const FName Id=WeaponMastery(&Item);\n    return ColdSteelSkills::IsMeleeMastery(Id)?FMath::Max(.05f,1.f-MasteryEffect(Id).CooldownReduction):1.f;\n}\n'
    edit('Source/FPSGAME/Skills/ColdSteelAdditionalMasteries.cpp',masteries)
    def enhancement(s):
        s=inc(s,'../Skills/ColdSteelSkillRules.h')
        return rep(s,'    if(ColdSteelInventory::IsBow(I))\n    {\n        Result=CoreCombatFormula::Round(Result*(1+CraftEffect(I,TEXT("damagePercent"))));\n        const auto* P=Profile?Profile:GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();', '    const auto* P=Profile?Profile:GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();\n    if(ColdSteelInventory::IsBow(I)||ColdSteelSkills::IsMeleeMastery(P->WeaponMastery(&I)))\n    {\n        Result=CoreCombatFormula::Round(Result*(1+CraftEffect(I,TEXT("damagePercent"))));')
    edit('Source/FPSGAME/UI/ColdSteelEnhancementSystem.cpp',enhancement)
    edit('Source/FPSGAME/Weapons/MeleeWeaponStats.cpp',lambda s:rep(s,'(Profile?1-Profile->MasteryEffect(TEXT("swordMastery")).CooldownReduction:1.)','(Profile?Profile->MeleeMasteryIntervalMultiplier(Item):1.)'))
    edit('Source/FPSGAME/Production/ProductionToolStats.cpp',lambda s:rep(s,'FMath::Max(.1,Enhancement?Enhancement->Effect(Item,TEXT("attackIntervalMul"),1):1.),.2,4.);','FMath::Max(.1,Enhancement?Enhancement->Effect(Item,TEXT("attackIntervalMul"),1):1.),.2,4.)/\n            (Profile?Profile->MeleeMasteryIntervalMultiplier(Item):1.f);'))
    edit('Source/FPSGAME/Production/ProductionToolComponent.h',lambda s:rep(rep(s,'    float HasteActionRate=1.f;','    float HasteActionRate=1.f,BluntMasteryInterval=1.f;'),'return bBluntSprintAttack?HasteActionRate:RateScale;','return bBluntSprintAttack?HasteActionRate:bBluntHeavy?RateScale*BluntMasteryInterval:RateScale;'))
    edit('Source/FPSGAME/Production/ProductionToolComponent.cpp',lambda s:rep(s,'    RateScale=float(ToolStats.RateScale);','    RateScale=float(ToolStats.RateScale);\n    BluntMasteryInterval=Item&&Profile?Profile->MeleeMasteryIntervalMultiplier(*Item):1.f;'))
    edit('Source/FPSGAME/Production/ProductionBluntAuthority.cpp',lambda s:rep(s,'const float ActionRate=bSprintAttack?HasteActionRate:RateScale;','const float ActionRate=bSprintAttack?HasteActionRate:Heavy?RateScale*BluntMasteryInterval:RateScale;'))
    def model(s):
        s=rep(s,'&MasteryDefinition(TEXT("swordMastery")),','&MasteryDefinition(TEXT("swordMastery")),&MasteryDefinition(TEXT("bluntMastery")),')
        s=rep(s,'if(Definition->Id==TEXT("swordMastery")){const auto E=ColdSteelSkills::Effect(*Definition,New->Level);N.Detail=FString::Printf(TEXT("剑精通固定伤害 +%.0f · 攻速 +%.0f%%"),E.FlatDamage,','if(ColdSteelSkills::IsMeleeMastery(Definition->Id)){const auto E=ColdSteelSkills::Effect(*Definition,New->Level);N.Detail=FString::Printf(TEXT("%s固定伤害 +%.0f · 普攻速度 +%.1f%%"),*Definition->Name,E.FlatDamage,')
        return rep(s,'&& (Mastery!=TEXT("bowMastery") || bBowEnemy);','&& (Mastery!=TEXT("bowMastery") || bBowEnemy)\n        && (!ColdSteelSkills::IsMeleeMastery(Mastery)||ColdSteelSkills::IsMasteryTrainingTarget(Shooter,Victim));')
    edit('Source/FPSGAME/Skills/ColdSteelSkillModel.cpp',model)
    edit('Source/FPSGAME/Development/ColdSteelDevelopmentTools.cpp',lambda s:rep(s,'TEXT("rifleMastery"),TEXT("pistolMastery"),TEXT("swordMastery"),','TEXT("rifleMastery"),TEXT("pistolMastery"),TEXT("swordMastery"),TEXT("bluntMastery"),'))
    def ui(s):
        s=rep(s,'return Id==TEXT("swordMastery")||Id==TEXT("machineGunMastery")','return ColdSteelSkills::IsMeleeMastery(Id)||Id==TEXT("machineGunMastery")')
        s=rep(s,'FName(TEXT("swordMastery")),FName(TEXT("machineGunMastery"))','FName(TEXT("swordMastery")),FName(TEXT("bluntMastery")),FName(TEXT("machineGunMastery"))')
        s=rep(s,'Tags=Id==TEXT("swordMastery")?TEXT("剑术 / 近战 / 被动"):','Tags=Id==TEXT("swordMastery")?TEXT("双手刀剑 / 近战 / 被动"):Id==TEXT("bluntMastery")?TEXT("钝器 / 近战 / 被动"):')
        s=s.replace('if(SelectedSkill!=TEXT("swordMastery"))','if(!ColdSteelSkills::IsMeleeMastery(SelectedSkill))')
        s=rep(s,'if(SelectedSkill==TEXT("swordMastery")||SelectedSkill==TEXT("bowMastery"))','if(ColdSteelSkills::IsMeleeMastery(SelectedSkill)||SelectedSkill==TEXT("bowMastery"))')
        s=rep(s,'EffectRow(TEXT("攻击速度提升"),3)','EffectRow(ColdSteelSkills::IsMeleeMastery(SelectedSkill)?TEXT("普通攻击速度提升"):TEXT("攻击速度提升"),3)')
        s=rep(s,'return FString::Printf(TEXT("+%.0f%%"),(1.f/FMath::Max(.05f,1.f-E.CooldownReduction)-1.f)*100);','return FString::Printf(TEXT("+%.1f%%"),(1.f/FMath::Max(.05f,1.f-E.CooldownReduction)-1.f)*100);')
        s=rep(s,'[Paragraph(SelectedSkill==TEXT("machineGunMastery")','[Paragraph(ColdSteelSkills::IsMeleeMastery(SelectedSkill)\n                ?TEXT("仅对应武器生效：刀剑精通适用双手刀剑，钝器精通适用所有钝器武器（包括双手锤）。1级固定伤害+1、普攻间隔−1%；每级再增加同等收益。20级固定伤害+20、普攻间隔−20%，等效普攻速度+25%。武技按自身公式继承武器伤害，动作、蓄力、冷却沿用独立规则；精通不缩短武技动作。两个精通独立成长，装备更换后按武器类型取值。")\n                :SelectedSkill==TEXT("machineGunMastery")')
        return rep(s,'        AddReward(TEXT("对应武器击杀"),D.KillExperience);','        AddReward(TEXT("对应武器击杀"),D.KillExperience);\n        if(ColdSteelSkills::IsMeleeMastery(SelectedSkill))Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(FString::Printf(TEXT("有效命中、直接击杀和同次多目标奖励可叠加；同一目标同次攻击不重复计数，多目标奖励每次仅一次。挥空、尸体、友方、召唤物和采集资源不计修炼。升下一级需要当前等级×%d经验，上限%d级。刀剑旧进度保留，钝器从1级独立修炼；无需魔法，无主动冷却。"),D.ExperiencePerLevel,D.MaxLevel),12,ColdSteelUI::TextTertiary,PageWidth-76)];')
    edit('Source/FPSGAME/UI/ColdSteelSkillPage.cpp',ui)
    def restore(s):
        return rep(s,'\ndef main():','\n_melee = PROJECT / "SourceAssets/MeleeMasteries20261019/manifest.json"\nif _melee.is_file():\n    for entry in json.loads(_melee.read_text(encoding="utf-8"))["icons"]:\n        ICONS[entry["file"]] = "SourceAssets/MeleeMasteries20261019/Selected/" + entry["file"]\n\ndef main():')
    edit('Tools/UI/prepare_cold_steel_skill_icons.py',restore)
    print('Integrated mastery definitions, scope, damage, speed, UI, migration and icon restoration.')

if __name__=='__main__':run()
