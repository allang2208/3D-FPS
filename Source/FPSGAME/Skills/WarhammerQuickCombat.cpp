#include "FPSQuickCombatComponent.h"
#include "ColdSteelSkillRules.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/WarhammerQuickCombatMotion.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/MeleeSmallTargetQuery.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void UFPSQuickCombatComponent::ConfigureForWarhammer()
{
    Style=EQuickCombatStyle::Warhammer;
    ClipLength=AttackEnd=WarhammerQuickCombat::Length;
    ReleaseEnd=.035f;CockEnd=WarhammerQuickCombat::Prepare;
    ContactTime=WarhammerQuickCombat::Contact;FollowEnd=WarhammerQuickCombat::Follow;
}

void UFPSQuickCombatComponent::ContactWarhammer(AFPSGAMECharacter* Player,UColdSteelStatusModel* Profile)
{
    auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();
    const auto* Item=Profile->ActiveProductionTool();
    if(!Tool||!Tool->IsQuickCombatActive()||!Item||!ColdSteelInventory::IsTwoHandedBlunt(*Item))return;
    if(auto* Capture=Player->FindComponentByClass<UBoundCongregateCaptureComponent>();Capture&&Capture->HitRestraintWithQuickMelee())
    {
        ImpactAge=0.f;ImpactStrength=1.f;Player->RefreshQuickCombatCamera();
        return;
    }
    FVector HeadContact;
    if(!Tool->GetQuickCombatStrikeProbe(HeadContact,ContactTime))return;
    const auto Stats=Profile->QuickCombatStats();
    const auto Aim=Player->GetMeleeAimTransform();
    const FVector Direction=Aim.GetUnitAxis(EAxis::X);
    // Use the head's height/lateral lane, sweeping from the eye plane. Starting
    // beyond the whole extended hammer would skip close blockers and add its
    // length to the skill's configured reach.
    const float HeadAdvance=FVector::DotProduct(HeadContact-Aim.GetLocation(),Direction);
    const FVector Origin=HeadContact-Direction*FMath::Max(0.f,HeadAdvance);
    auto Shot=ColdSteelSkills::Snapshot(Player,Item,false);
    Shot.bMelee=true;Shot.bMeleeStrike=true;Shot.bRifle=Shot.bPistol=false;
    Shot.AttackForm=EMonsterAttackForm::Blunt;Shot.AttackMeta=0x80;Shot.WeakpointPercent=0.f;
    Shot.ToughnessDamageMultiplier=Stats.ToughnessMultiplier;
    TArray<FHitResult> Hits;
    if(Stats.bAreaHit)Hits=MeleeSmallTargets::QueryQuickAreaContacts(GetWorld(),Player,Aim,Origin,Stats.RangeCM,WarhammerQuickCombat::QueryRadiusCM);
    else
    {
        FHitResult Hit;
        if(MeleeSmallTargets::QueryQuickContact(GetWorld(),Player,Aim,Origin,Stats.RangeCM,WarhammerQuickCombat::QueryRadiusCM,Hit))Hits.Add(Hit);
    }
    ImpactAge=0.f;Player->RefreshQuickCombatCamera();
    TSet<TWeakObjectPtr<AActor>> Seen;
    for(const auto& Hit:Hits)
    {
        AActor* Target=Hit.GetActor();
        if(!Target||Seen.Contains(Target))continue;
        Seen.Add(Target);
        if(UWardBreakableGlass::BreakHit(Hit,Direction)){ImpactStrength=1.f;continue;}
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat||Combat->IsDead())continue;
        FWeaponDamageResult Result;
        const float Applied=ColdSteelSkills::ApplyHit(Player,Hit,Stats.Damage,Direction,Shot,&Result);
        const bool Killed=Combat->IsDead();
        if(Applied<=0.f&&!Killed)continue;
        ImpactStrength=1.f;
        Player->NotifyConfirmedWeaponHit(Target,Applied,&Result,false);
        Combat->ReceiveMeleeKnockback(Player,Stats.KnockbackCM);
        if(Player->HasAuthority()&&!Killed&&Stats.BleedChance>0.f&&FMath::FRand()<Stats.BleedChance)
            if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddBleeding(Player,1);
        if(Killed&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))bKillPending=true;
    }
    // The sword's quick-strike cue is emitted once at release by AdvanceAction.
    // Keep the ordinary confirmed-hit feedback, without stacking this cue again.
}
