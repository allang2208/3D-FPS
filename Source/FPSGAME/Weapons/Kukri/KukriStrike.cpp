#include "KukriWeaponComponent.h"
#include "KukriRhythm.h"
#include "../FPSImpactFXSubsystem.h"
#include "../../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

// Impact moment (V12c stab, user 2026-10-22: "still too fast, no 顿挫, no weight"; no knockback; V12d on all three
// stages).  KukriRhythm::Strikes[Stage].At is the frame the blade arrives -- the stab on the crosshair, the slashes
// across the screen centre.  There the view gets a short real-time accent whether or not it hits, and a miss freezes
// MissStop.  Contacts found earlier keep their damage but hold their cue (hit-stop, sound, blood) for that frame, so
// the stop, the sound and the blood land where the blade is.

const KukriRhythm::FStrike& UKukriWeaponComponent::StrikeProfile() const
{
    if(bDualThrust)return KukriRhythm::DualThrustStrike;
    if(bDualHeavy&&bHeavyAttack)return KukriRhythm::DualHeavyStrike;
    return KukriRhythm::Strikes[Stage];
}

void UKukriWeaponComponent::ResetStrike()
{
    bStrikeDone=false;bPendingFlesh=false;bPendingWall=false;bPressIn=false;bRiftStarted=false;
    PendingFX.Reset();
}

void UKukriWeaponComponent::ArriveStrike()
{
    bStrikeDone=true;
    // The arrival accent is real time: it keeps going through the hit-stop that freezes the author clock.
    StrikeAge=0.f;
    if(bPendingFlesh){bPendingFlesh=false;ConfirmImpact(PendingFleshHit,false);}
    else if(bPendingWall){bPendingWall=false;ConfirmImpact(PendingWallHit,true);}
    else if(!bImpactConfirmed&&!bWallHit)
    {
        // A miss still stops dead: a short freeze and a light jolt instead of the flesh hit-stop.
        HitStop=FMath::Max(HitStop,StrikeProfile().MissStop);
        ImpactAge=0.f;ImpactKick=KukriRhythm::StrikeKick;bPressIn=false;
    }
    for(const auto& Pending:PendingFX)SpawnContactFX(Pending.Hit,Pending.bWorld);
    PendingFX.Reset();
}

void UKukriWeaponComponent::QueueContactFX(const FHitResult& Hit,bool bWorld)
{
    if(StrikeProfile().At>0.f&&!bStrikeDone){PendingFX.Add({Hit,bWorld});return;}
    SpawnContactFX(Hit,bWorld);
}

void UKukriWeaponComponent::SpawnContactFX(const FHitResult& Hit,bool bWorld) const
{
    auto* FX=GetWorld()?GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>():nullptr;
    if(!FX||!Camera)return;
    // Melee query hits (object-type sweeps) are cosmetic input here: the subsystem only draws blocking hits, and the
    // kukri plays its own hit / wall cue, so no bullet impact sound and no bullet-hole decal.
    FHitResult Contact=Hit;Contact.bBlockingHit=true;
    if(Contact.ImpactNormal.IsNearlyZero())
        if(const auto* P=Pawn())Contact.ImpactNormal=-P->GetMeleeAimTransform().GetUnitAxis(EAxis::X);
    FX->SpawnImpact(Contact,Camera,false,false);
}

FVector UKukriWeaponComponent::StrikeViewmodelOffset() const
{
    // A confirmed hit carries the blade on through the hit-stop (stab: pressed in; slashes: dragged along the cut),
    // then lets go.
    if(!bPressIn||bDashAttack||ImpactAge<0.f)return FVector::ZeroVector;
    const auto& K=StrikeProfile();
    const float A=ImpactAge<PressStop?FMath::SmoothStep(0.f,PressStop,ImpactAge):FMath::Exp(-(ImpactAge-PressStop)*12.f);
    // The dual sweep's left blade drags the other way along its cut.
    return FVector(K.PressX,bOffhandSwing?-K.PressY:K.PressY,K.PressZ)*A;
}
