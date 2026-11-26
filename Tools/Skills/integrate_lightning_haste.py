"""One-time source wiring for the approved Lightning Haste skill."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
BACKUP=ROOT/'SourceAssets/LightningHaste20261019/source-before'
PROGRESS=BACKUP.parent/'core-integration-progress.json'
COMPLETED=json.loads(PROGRESS.read_text(encoding='utf-8')) if PROGRESS.exists() else []

def edit(path,fn):
    if path in COMPLETED:return
    p=ROOT/path;s=p.read_text(encoding='utf-8-sig');result=fn(s)
    backup=BACKUP/path
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_text(s,encoding='utf-8')
    p.write_text(result,encoding='utf-8')
    COMPLETED.append(path)
    PROGRESS.write_text(json.dumps(COMPLETED,indent=2),encoding='utf-8')

def replace(s,old,new):
    if old not in s:raise RuntimeError('Missing source anchor: '+old[:100])
    return s.replace(old,new)

def add_lines(s,needle):
    return '\n'.join(line+'\n'+line.replace('IceArmor','LightningHaste').replace('iceArmor','lightningHaste') if needle in line else line for line in s.split('\n'))

def run():
    edit('Source/FPSGAME/Skills/ColdSteelSkillTypes.h',lambda s:replace(replace(s,'#include "IceArmorTypes.h"','#include "IceArmorTypes.h"\n#include "LightningHasteTypes.h"'),'    FIceArmorTuning IceArmor;','    FIceArmorTuning IceArmor;\n    FLightningHasteTuning LightningHaste;'))
    edit('Source/FPSGAME/UI/ColdSteelInventoryTypes.h',lambda s:add_lines(add_lines(s,'UPROPERTY() float IceArmorCooldown ='),'UPROPERTY() float IceArmorCooldownDuration ='))
    def model(s):
        s=replace(s,'    FColdSteelSkillDefinition IceArmorSkill;','    FColdSteelSkillDefinition IceArmorSkill;\n    FColdSteelSkillDefinition LightningHasteSkill;')
        return replace(s,'    void FinishIceArmorTraining(int32 Experience);','''    void FinishIceArmorTraining(int32 Experience);
    const FColdSteelSkillDefinition& LightningHasteDefinition() const{return LightningHasteSkill;}
    FLightningHasteCast LightningHasteStats(int32 AtLevel=-1) const;
    float LightningHasteCooldown() const{return HasNoAbilityCooldown()?0.f:Current.LightningHasteCooldown;}
    float LightningHasteCooldownDuration() const{return Current.LightningHasteCooldownDuration;}
    bool BeginLightningHasteCast(const FLightningHasteCast& Spell);
    void CommitLightningHasteCast(const FLightningHasteCast& Spell);
    void FinishLightningHasteTraining(int32 Experience);''')
    edit('Source/FPSGAME/UI/ColdSteelStatusModel.h',model)
    for file,needles in {
        'Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp':['IceArmorSkill=','Current.IceArmorCooldown='],
        'Source/FPSGAME/UI/ColdSteelProfileRecovery.h':['Into.IceArmorCooldown='],
        'Source/FPSGAME/Skills/ColdSteelFireballModel.cpp':['else if(Skill==TEXT("iceArmor"))'],
        'Source/FPSGAME/Development/ColdSteelDevelopmentTuning.cpp':['Current.IceArmorCooldown='],
    }.items():
        def apply(s):
            for needle in needles:s=add_lines(s,needle)
            return s
        edit(file,apply)
    def rules(s):
        s=replace(s,'#include "ColdSteelSkillRules.h"','#include "ColdSteelSkillRules.h"\n#include "FPSLightningHasteComponent.h"')
        s=replace(s,'    if(Id==TEXT("iceArmor"))\n    {','''    if(Id==TEXT("lightningHaste"))
    {
        auto& T=D.LightningHaste;
        T.MoveBase=Num(TEXT("moveSpeedBase"),T.MoveBase);T.MovePerLevel=Num(TEXT("moveSpeedPerLevel"),T.MovePerLevel);
        T.ActionBase=Num(TEXT("actionSpeedBase"),T.ActionBase);T.ActionPerLevel=Num(TEXT("actionSpeedPerLevel"),T.ActionPerLevel);
        T.DurationBase=Num(TEXT("durationBase"),T.DurationBase);T.DurationPerLevel=Num(TEXT("durationPerLevel"),T.DurationPerLevel);
        T.ManaBase=Num(TEXT("manaBase"),T.ManaBase);T.ManaPerLevel=Num(TEXT("manaPerLevel"),T.ManaPerLevel);T.Cooldown=Num(TEXT("cooldown"),T.Cooldown);
        T.CastExperience=Num(TEXT("castExperience"),T.CastExperience);T.KillExperience=Num(TEXT("killExperience"),T.KillExperience);
        T.Kill6Bonus=Num(TEXT("kill6Bonus"),T.Kill6Bonus);T.Kill11Bonus=Num(TEXT("kill11Bonus"),T.Kill11Bonus);
    }
    if(Id==TEXT("iceArmor"))
    {''')
        s=replace(s,'    if (P.SkillProgressVersion >= 23) return false;','''    if (P.SkillProgressVersion >= 24) return false;
    P.Skills.FindOrAdd(TEXT("lightningHaste"));P.LightningHasteCooldown=P.LightningHasteCooldownDuration=0;
    if(P.SkillProgressVersion==23){P.SkillProgressVersion=24;return true;}''')
        s=s.replace('P.SkillProgressVersion=23','P.SkillProgressVersion=24').replace('P.SkillProgressVersion>23','P.SkillProgressVersion>24')
        s=replace(s,'    if(P.SkillProgressVersion>=23&&','''    if(P.SkillProgressVersion>=24&&(!P.Skills.Contains(TEXT("lightningHaste"))||!FMath::IsFinite(P.LightningHasteCooldown)||!FMath::IsFinite(P.LightningHasteCooldownDuration)||P.LightningHasteCooldown<0||P.LightningHasteCooldownDuration<P.LightningHasteCooldown||P.LightningHasteCooldownDuration>300)){Reason=TEXT("雷电迅捷进度或冷却无效");return false;}
    if(P.SkillProgressVersion>=23&&''')
        return replace(s,'    if(Model)Model->ApplyKillStaminaRecovery(Victim);','    if(Model)Model->ApplyKillStaminaRecovery(Victim);\n    if(auto* Haste=Killer->FindComponentByClass<UFPSLightningHasteComponent>())Haste->ObserveKill(Victim);')
    edit('Source/FPSGAME/Skills/ColdSteelSkillRules.cpp',rules)
    edit('Source/FPSGAME/Skills/ColdSteelSpellMana.cpp',lambda s:add_lines(s,'else if(Id==TEXT("iceArmor"))Cost='))
    def char_header(s):
        return replace(s,'    UPROPERTY(VisibleAnywhere, Category="Skills") TObjectPtr<class UFPSQuickCombatComponent> QuickCombatPistol;','''    UPROPERTY(VisibleAnywhere, Category="Skills") TObjectPtr<class UFPSQuickCombatComponent> QuickCombatPistol;
    UPROPERTY(VisibleAnywhere, Category="Skills") TObjectPtr<class UFPSLightningHasteComponent> LightningHasteSkill;
    class UFPSLightningHasteComponent* GetLightningHaste() const{return LightningHasteSkill;}''')
    edit('Source/FPSGAME/FPSGAMECharacter.h',char_header)
    def character(s):
        s=replace(s,'#include "Skills/FPSIceArmorComponent.h"','#include "Skills/FPSIceArmorComponent.h"\n#include "Skills/FPSLightningHasteComponent.h"')
        s=replace(s,'    CreateDefaultSubobject<UFPSIceArmorComponent>(TEXT("IceArmorSkill"));','    CreateDefaultSubobject<UFPSIceArmorComponent>(TEXT("IceArmorSkill"));\n    LightningHasteSkill=CreateDefaultSubobject<UFPSLightningHasteComponent>(TEXT("LightningHasteSkill"));')
        s=add_lines(s,'if(auto* IceArmor=FindComponentByClass<UFPSIceArmorComponent>())IceArmor->Cancel();')
        return replace(s,'||(FindComponentByClass<UFPSIceArmorComponent>()&&FindComponentByClass<UFPSIceArmorComponent>()->HasQueuedAction());','||(FindComponentByClass<UFPSIceArmorComponent>()&&FindComponentByClass<UFPSIceArmorComponent>()->HasQueuedAction())||(LightningHasteSkill&&LightningHasteSkill->HasQueuedAction());')
    edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
    def gesture(s):
        s=replace(s,'#include "FPSIceArmorComponent.h"','#include "FPSIceArmorComponent.h"\n#include "FPSLightningHasteComponent.h"')
        s=add_lines(s,'else if(auto* IceArmor=GetOwner()->FindComponentByClass<UFPSIceArmorComponent>();')
        return add_lines(s,'if(auto* IceArmor=GetOwner()->FindComponentByClass<UFPSIceArmorComponent>())IceArmor->Cancel();')
    edit('Source/FPSGAME/Skills/FPSFireballComponent.cpp',gesture)
    for file in ['Source/FPSGAME/Multiplayer/ColdSteelCampfireRequests.cpp','Source/FPSGAME/Multiplayer/ColdSteelTeamTravel.cpp']:
        edit(file,lambda s:add_lines(add_lines(s,'#include "../Skills/FPSIceArmorComponent.h"'),'Ice->FinishForRemoval();'))
    edit('Source/FPSGAME/UI/ColdSteelMagicQuickCast.cpp',lambda s:add_lines(replace(s,'Skill==TEXT("holyLight")||Skill==TEXT("iceArmor")','Skill==TEXT("holyLight")||Skill==TEXT("lightningHaste")||Skill==TEXT("iceArmor")'),'if(Skill==TEXT("iceArmor"))return'))
    def quickbar(s):
        s=add_lines(s,'#include "../Skills/FPSIceArmorComponent.h"')
        s=replace(s,'&&B.Skill!=TEXT("iceArmor")','&&B.Skill!=TEXT("lightningHaste")&&B.Skill!=TEXT("iceArmor")')
        s=replace(s,'if(Id==TEXT("iceArmor"))return &IceArmorSkill;','if(Id==TEXT("lightningHaste"))return &LightningHasteSkill;if(Id==TEXT("iceArmor"))return &IceArmorSkill;')
        return add_lines(s,'if(Skill==TEXT("iceArmor"))if(auto* Ability=')
    edit('Source/FPSGAME/UI/ColdSteelQuickBarModel.cpp',quickbar)
    edit('Source/FPSGAME/Development/ColdSteelDevelopmentTools.cpp',lambda s:add_lines(replace(s,'TEXT("iceArmor"),TEXT("dragonBreath")','TEXT("iceArmor"),TEXT("lightningHaste"),TEXT("dragonBreath")'),'if(Id==TEXT("iceArmor"))return'))
    edit('Source/FPSGAME/Skills/ColdSteelSkillModel.cpp',lambda s:replace(replace(s,'&FlameArmorSkill,&IceArmorSkill,','&FlameArmorSkill,&IceArmorSkill,&LightningHasteSkill,'),'        if(Definition->Id==TEXT("iceArmor"))','        if(Definition->Id==TEXT("lightningHaste")){const auto C=LightningHasteStats(New->Level);N.Detail=FString::Printf(TEXT("移速 +%.1f%% · 动作 +%.1f%% · 持续 %.1f 秒"),C.MoveBonus*100,C.ActionBonus*100,C.Duration);}\n        if(Definition->Id==TEXT("iceArmor"))'))
    # Skills remain ordinary saved profile data, independent of transient buff state.
    edit('Content/ColdSteelData/skills.json',lambda s:json.dumps(dict(json.loads(s),lightningHaste={
        'name':'雷电迅捷','description':'电弧环绕双手与双脚，提高移动和所有动作速度。无需法杖，换武器后继续生效；施法与持续期间的有效击杀可修炼。',
        'icon':'Skills/lightning_haste_cold_steel.png','experiencePerLevel':100,'requiresStaff':False,
        'moveSpeedBase':.1,'moveSpeedPerLevel':.01,'actionSpeedBase':.05,'actionSpeedPerLevel':.005,
        'durationBase':20,'durationPerLevel':.5,'manaBase':40,'manaPerLevel':2,'cooldown':50,
        'castExperience':1,'killExperience':3,'kill6Bonus':15,'kill11Bonus':40,
        'balanceRevision':'2026-10-19: K=level-1; one action multiplier; strict kills>5/>10; highest streak bonus only'
    }),ensure_ascii=False,indent=2)+'\n')
    print('Saved core definitions, profile migration, player component, input, and cleanup wiring.')

if __name__=='__main__':run()
