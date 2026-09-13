#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::RifleProgress() const
{ const auto* P=Current.Skills.Find(RifleSkill.Id); return P?*P:FColdSteelSkillProgress(); }
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
    Training.bEligible=Shot.bRifle && Combat && !Combat->IsDead() && !Victim->ActorHasTag(TEXT("Summoned")) && !Victim->ActorHasTag(TEXT("NoSkillTraining"));
    Training.bCritical=Hit.BoneName.ToString().Contains(TEXT("head"),ESearchCase::IgnoreCase);
    const float Amount=Damage*(Shot.bRifle && Training.bCritical?1+Shot.WeakpointPercent:1);
    TGuardValue<FTrainingHit*> HitScope(ActiveTrainingHit,&Training);
    const float Applied=UGameplayStatics::ApplyPointDamage(Victim,Amount,Direction,Hit,Pawn?Pawn->GetController():nullptr,Shooter,nullptr);
    // Lethal rewards are committed together with the monster's AwardKill transaction.
    if (Applied>0 && Training.bEligible && Training.bCritical && !Training.bKillAttempted && RifleProgress().Level<RifleSkill.MaxLevel)
    { SyncRuntime(); auto P=Snapshot(); ColdSteelSkills::AddExperience(P,RifleSkill,RifleSkill.CriticalExperience); CommitState(P); }
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
    const auto* Old=Before.Skills.Find(RifleSkill.Id); const auto* New=After.Skills.Find(RifleSkill.Id);
    if (Old && New && New->Level>Old->Level)
    {
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("%s升级   Lv.%d → %d"),*RifleSkill.Name,Old->Level,New->Level);
        N.Detail=ColdSteelSkills::EffectSummary(ColdSteelSkills::Effect(RifleSkill,New->Level)); N.Icon=RifleSkill.Icon;
        ProgressNotices.Add(MoveTemp(N));
    }
}
bool UColdSteelStatusModel::PopProgressNotice(FColdSteelProgressNotice& Out)
{ if (ProgressNotices.IsEmpty()) return false; Out=MoveTemp(ProgressNotices[0]); ProgressNotices.RemoveAt(0); return true; }
