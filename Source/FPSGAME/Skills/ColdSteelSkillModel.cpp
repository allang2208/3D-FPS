#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::RifleProgress() const
{ const auto* P=Current.Skills.Find(RifleSkill.Id); return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillProgress UColdSteelStatusModel::CriticalStrikeProgress() const
{ const auto* P=Current.Skills.Find(CriticalStrikeSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillEffect UColdSteelStatusModel::CriticalStrikeEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(CriticalStrikeSkill,AtLevel<0?CriticalStrikeProgress().Level:AtLevel); }
FColdSteelSkillProgress UColdSteelStatusModel::PistolProgress() const
{ const auto* P=Current.Skills.Find(PistolSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillEffect UColdSteelStatusModel::PistolEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(PistolSkill,AtLevel<0?PistolProgress().Level:AtLevel); }
float UColdSteelStatusModel::PistolWeaponDamage(const FColdSteelItem& Item,float WeaponDamage) const
{
    if(!ColdSteelSkills::IsPistol(&Item))return WeaponDamage;
    const auto E=PistolEffect();return FMath::RoundToFloat(WeaponDamage*(1+E.DamagePercent)+E.FlatDamage);
}
float UColdSteelStatusModel::PistolMovementMultiplier() const
{ return ColdSteelSkills::IsPistol(Equipped())&&!ActiveProductionTool()?1.f+PistolEffect().MoveSpeed:1.f; }
FColdSteelSkillProgress UColdSteelStatusModel::DodgeProgress() const
{ const auto* P=Current.Skills.Find(DodgeSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillProgress UColdSteelStatusModel::DexterousHandsProgress() const
{ const auto* P=Current.Skills.Find(DexterousHandsSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillEffect UColdSteelStatusModel::DexterousHandsEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(DexterousHandsSkill,AtLevel<0?DexterousHandsProgress().Level:AtLevel); }
float UColdSteelStatusModel::ReloadSpeedMultiplier() const
{ return 1.f+DexterousHandsEffect().ReloadSpeed; }
FColdSteelSkillEffect UColdSteelStatusModel::DodgeEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(DodgeSkill,AtLevel<0?DodgeProgress().Level:AtLevel); }
float UColdSteelStatusModel::DodgeStaminaCost() const
{ return StaminaTuning.DodgeCost*(1.f-DodgeEffect().DodgeCostReduction); }
bool UColdSteelStatusModel::TrainDodge(int32 Amount)
{
    if(Amount<=0||DodgeProgress().Level>=DodgeSkill.MaxLevel)return false;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,DodgeSkill,Amount);return CommitState(P);
}
FColdSteelSkillEffect UColdSteelStatusModel::RifleEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(RifleSkill,AtLevel<0?RifleProgress().Level:AtLevel); }
float UColdSteelStatusModel::RifleWeaponDamage(const FColdSteelItem& Item,float WeaponDamage) const
{
    if (!ColdSteelSkills::IsRifle(&Item)) return WeaponDamage;
    const auto E=RifleEffect(); return FMath::RoundToFloat(WeaponDamage*(1+E.DamagePercent)+E.FlatDamage);
}
float UColdSteelStatusModel::ApplySkillWeaponHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot)
{
    AActor* Victim=Hit.GetActor(); const auto* Pawn=Cast<APawn>(Shooter);
    const auto* Combat=Victim?Victim->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    FTrainingHit Training; Training.Victim=Victim;
    const FName Mastery=Shot.MasteryId.IsNone()?(Shot.bPistol?FName(TEXT("pistolMastery")):(Shot.bRifle?FName(TEXT("rifleMastery")):NAME_None)):Shot.MasteryId;
    const auto& Skill=MasteryDefinition(Mastery);
    Training.SkillId=Mastery;Training.ExtraExperience=Shot.ExtraMasteryExperience;
    Training.bEligible=Combat && !Combat->IsDead() && !Victim->ActorHasTag(TEXT("Summoned")) && !Victim->ActorHasTag(TEXT("NoSkillTraining"));
    const bool Weakpoint=ColdSteelSkills::IsCriticalHit(Hit);
    Training.bCritical=Weakpoint||(Combat&&FMath::FRand()*100<CoreCombatFormula::CriticalChance(Shot.CriticalChance,CombatFormulaRuntime::MonsterCriticalResistance(Victim)));
    float Amount=Damage*(Shot.bRifle && Weakpoint?1+Shot.WeakpointPercent:1);
    if(Training.bCritical&&Shot.CriticalDamageBonus>0)Amount=FMath::FloorToFloat(Amount*(1+Shot.CriticalDamageBonus));
    TGuardValue<FTrainingHit*> HitScope(ActiveTrainingHit,&Training);
    const double Penetration=Shot.ArmorPenetration;
    TGuardValue<const double*> ArmorScope(CombatFormulaRuntime::ActivePhysicalPenetration,&Penetration);
    const float Applied=UGameplayStatics::ApplyPointDamage(Victim,Amount,Direction,Hit,Pawn?Pawn->GetController():nullptr,Shooter,nullptr);
    // Lethal rewards are committed together with the monster's AwardKill transaction.
    if (Applied>0 && Training.bEligible && !Training.bKillAttempted)
    {
        SyncRuntime();auto P=Snapshot();bool Trained=false;
        auto Train=[&](const FColdSteelSkillDefinition& D,int32 Experience){
            const auto* Progress=P.Skills.Find(D.Id);
            if(Progress&&Progress->Level<D.MaxLevel&&Experience>0){ColdSteelSkills::AddExperience(P,D,Experience);Trained=true;}
        };
        if(!Training.SkillId.IsNone())Train(Skill,Skill.HitExperience+Training.ExtraExperience+(Training.bCritical?Skill.CriticalExperience:0));
        if(Training.bCritical)Train(CriticalStrikeSkill,CriticalStrikeSkill.CriticalHitExperience);
        if(Trained)CommitState(P);
    }
    return Applied;
}
void UColdSteelStatusModel::QueueProgressNotices(const FColdSteelProfile& Before,const FColdSteelProfile& After)
{
    if (After.Level>Before.Level)
    {
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("角色升级   Lv.%d → %d"),Before.Level,After.Level);
        N.Detail=FString::Printf(TEXT("获得 %d 点属性点 · 打开角色状态进行分配"),After.Points-Before.Points);
        ProgressNotices.Add(MoveTemp(N));
    }
    const FColdSteelSkillDefinition* NoticeDefinitions[]={&RifleSkill,&PistolSkill,&CriticalStrikeSkill,&FireballSkill,&DodgeSkill,&DexterousHandsSkill,&MasteryDefinition(TEXT("swordMastery")),&MasteryDefinition(TEXT("machineGunMastery")),&MasteryDefinition(TEXT("shotgunMastery")),&MasteryDefinition(TEXT("bowMastery")),&MasteryDefinition(TEXT("heavyStrike"))};
    for(const auto* Definition:NoticeDefinitions)
    {
    const auto* Old=Before.Skills.Find(Definition->Id); const auto* New=After.Skills.Find(Definition->Id);
    if (Old && New && New->Level>Old->Level)
    {
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("%s升级   Lv.%d → %d"),*Definition->Name,Old->Level,New->Level);
        N.Detail=ColdSteelSkills::EffectSummary(ColdSteelSkills::Effect(*Definition,New->Level)); N.Icon=Definition->Icon;
        if(Definition->Id==TEXT("fireball"))N.Detail=FString::Printf(TEXT("火球威力提升 · 爆炸半径 %.2f 米"),FireballStats(New->Level).Radius/100);
        ProgressNotices.Add(MoveTemp(N));
    }
    }
}
bool UColdSteelStatusModel::PopProgressNotice(FColdSteelProgressNotice& Out)
{ if (ProgressNotices.IsEmpty()) return false; Out=MoveTemp(ProgressNotices[0]); ProgressNotices.RemoveAt(0); return true; }
