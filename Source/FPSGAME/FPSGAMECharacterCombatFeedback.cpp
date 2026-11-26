#include "FPSGAMECharacter.h"
#include "Weapons/JingangRuneComponent.h"
#include "Monsters/MonsterCombatComponent.h"
#include "UI/ColdSteelDamageNumberSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void AFPSGAMECharacter::NotifyConfirmedWeaponHit(AActor* Target, float AppliedDamage,const FWeaponDamageResult* DamageResult,bool bFirearmHit,bool bForwardToOwner)
{
    if (Target == this || !Cast<APawn>(Target) || AppliedDamage <= 0.f || !GetWorld()) return;
    const float MagicApplied=DamageResult?DamageResult->Applied.MagicPortion(AppliedDamage):0.f;
    if(auto* Rune=FindComponentByClass<UJingangRuneComponent>())Rune->ConfirmAttack(Target,AppliedDamage);
    if(HasAuthority()&&!IsLocallyControlled())
    {
        const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        const bool bKilled=(DamageResult&&DamageResult->bKilled)||(Combat&&Combat->IsDead());
        if(bForwardToOwner)ClientWeaponHitFeedback(Target,AppliedDamage,DamageResult&&DamageResult->bCritical,
            bKilled,bFirearmHit,MagicApplied);
        return;
    }
    LastConfirmedWeaponHitTime = GetWorld()->GetTimeSeconds();
    LastMonsterHit = FMonsterHitFeedback();
    const auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>();
    if (!Combat || !Combat->GetVitals(LastMonsterHit.Health, LastMonsterHit.MaxHealth, LastMonsterHit.Name)) return;
    LastMonsterHit.Toughness = Combat->DisplayToughness();
    LastMonsterHit.ToughnessThreshold = Combat->ToughnessThreshold;
    LastMonsterHit.ToughnessPhase = Combat->GetToughnessPhase();
    LastMonsterHit.ToughnessPhaseRemaining = Combat->ToughnessPhaseSecondsRemaining();
    LastMonsterHit.Target = Target;
    LastMonsterHit.Damage = AppliedDamage;
    if(DamageResult)LastMonsterHit.DamageResult=*DamageResult;
    LastMonsterHit.bKilled = (DamageResult&&DamageResult->bKilled)||Combat->IsDead();
    if(auto* GI=GetGameInstance())
        if(auto* Numbers=GI->GetSubsystem<UColdSteelDamageNumberSubsystem>())
        {
            // Follow the visible mesh top so a moving/ragdolling monster keeps the
            // number directly above its body instead of leaving it at the old impact.
            const FVector Anchor=UColdSteelDamageNumberSubsystem::TargetTopAnchor(Target);
            const bool bBig=AppliedDamage>=80.f||(LastMonsterHit.MaxHealth>0.f&&AppliedDamage>=LastMonsterHit.MaxHealth*.10f);
            if(auto* PC=Cast<APlayerController>(GetController()))
                Numbers->PushDamageNumber(Target,PC,Anchor,AppliedDamage,
                    LastMonsterHit.DamageResult.bCritical,LastMonsterHit.bKilled,bBig,true,MagicApplied);
        }
    // Firearms report at the impact itself (the impact FX subsystem plays S_GunHit
    // where the round lands), so the shared monster-hit tick is not stacked on a gun
    // hit. Melee and Cold Steel skills keep that tick as their confirm cue.
    if(!bFirearmHit)PlayMeleeHitConfirmation();
}

void AFPSGAMECharacter::ClientBallistaHit_Implementation(bool bKilled)
{
    if(!IsLocallyControlled() || !GetWorld())return;
    // The server already resolved the bolt. Give the shooter the cue even if the victim despawned.
    LastConfirmedWeaponHitTime=GetWorld()->GetTimeSeconds();
    LastMonsterHit=FMonsterHitFeedback{};
    LastMonsterHit.bKilled=bKilled;
    PlayMeleeHitConfirmation();
}

void AFPSGAMECharacter::PlayMeleeHitConfirmation() const
{
    if (IsLocallyControlled() && ConfirmedMonsterHitSound)
        UGameplayStatics::PlaySound2D(this, ConfirmedMonsterHitSound, 1.f, 1.f);
}

void AFPSGAMECharacter::ClientWeaponHitFeedback_Implementation(AActor* Target,float AppliedDamage,bool Critical,bool Killed,bool Firearm,float MagicApplied)
{
    if(!IsLocallyControlled()||HasAuthority())return;
    FWeaponDamageResult Result;Result.bResolved=true;Result.bCritical=Critical;Result.bKilled=Killed;
    Result.Applied=FWeaponDamageParts::FromChannels(AppliedDamage,MagicApplied);
    NotifyConfirmedWeaponHit(Target,AppliedDamage,&Result,Firearm);
}

float AFPSGAMECharacter::GetHitMarkerOpacity() const
{
    if (!GetWorld()) return 0.f;
    const double Age = GetWorld()->GetTimeSeconds() - LastConfirmedWeaponHitTime;
    // Hold for 60 ms, then fade over 180 ms. Repeated hits refresh the same marker.
    return .65f * FMath::Clamp(static_cast<float>((.24 - Age) / .18), 0.f, 1.f);
}

bool AFPSGAMECharacter::GetMonsterHitFeedback(FMonsterHitFeedback& Out) const
{
    if (!GetWorld() || LastMonsterHit.MaxHealth <= 0.f) return false;
    const double Age = GetWorld()->GetTimeSeconds() - LastConfirmedWeaponHitTime;
    Out = LastMonsterHit;
    Out.Opacity = FMath::Clamp(static_cast<float>((4. - Age) / .5), 0.f, 1.f);
    if (const auto* Target = Out.Target.Get())
        if (const auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>())
        {
            Combat->GetVitals(Out.Health, Out.MaxHealth, Out.Name);
            Out.Toughness = Combat->DisplayToughness();
            Out.ToughnessThreshold = Combat->ToughnessThreshold;
            Out.ToughnessPhase = Combat->GetToughnessPhase();
            Out.ToughnessPhaseRemaining = Combat->ToughnessPhaseSecondsRemaining();
            // Keep the authoritative receipt kill through replicated-health lag.
            Out.bKilled = Out.bKilled || Combat->IsDead();
        }
    // Keep the current target visible through its timed break/refill window.
    const bool ActivePoisePhase=Out.Target.IsValid()&&!Out.bKilled&&Out.ToughnessPhaseRemaining>0.f&&
        (Out.ToughnessPhase==EMonsterToughnessPhase::Broken||Out.ToughnessPhase==EMonsterToughnessPhase::Recovering);
    if(ActivePoisePhase)Out.Opacity=1.f;
    else if(Age>=4.)return false;
    return true;
}
