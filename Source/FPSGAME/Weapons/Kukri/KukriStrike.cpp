#include "KukriWeaponComponent.h"
#include "../../Combat/FPSAttackQuery.h"
#include "SwiftFalconHeavy.h"
#include "KukriRhythm.h"
#include "HatchetChopRhythm.h"
#include "HatchetDualChopRhythm.h"
#include "../FPSImpactFXSubsystem.h"
#include "../MeleeSmallTargetQuery.h"
#include "GameFramework/PlayerController.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/MonsterCombatComponent.h"
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
    if(bFalconHeavy&&bHeavyAttack)
    {
        static const KukriRhythm::FStrike Chop={SwiftFalconHeavy::ChopAt,.026f,1.2f,1.8f,-1.2f,0.f,1.6f,0.f,-.8f,true};
        static const KukriRhythm::FStrike Pull={SwiftFalconHeavy::PullAt,.024f,.7f,-1.7f,1.15f,0.f,-.55f,0.f,.25f,true};
        return Shot.MeleeDamagePhase==1?Pull:Chop;
    }
    if(bDualThrust)return IsHatchetDualChop()?HatchetDualChopRhythm::Strike:KukriRhythm::DualThrustStrike;
    if(bDualHeavy&&bHeavyAttack)return KukriRhythm::DualHeavyStrike;
    if(IsHatchetChop())return HatchetChopRhythm::Strike;
    return KukriRhythm::Strikes[Stage];
}

// The hatchet's last combo hit is its own overhead chop (2026-11-02): only the clip and its presentation change; the
// stage keeps KukriRhythm's gameplay clock (static_asserts in HatchetChopRhythm.h), so receipts and windows match.
bool UKukriWeaponComponent::IsHatchetChop() const
{
    return bHatchetChop&&bAttacking&&Stage==HatchetChopRhythm::Stage&&!bDualThrust&&!bDualSweep;
}

// Two hatchets: the double thrust becomes both hatchets chopping down together; it keeps the double thrust's gameplay
// clock (KukriRhythm::DualThrust*, static_assert in HatchetDualChopRhythm.h), only the clip and presentation change.
// A hatchet + kukri pair (2026-11-04) chops with the hatchet hand only: the chop's impact feel, whoosh and that head's
// crescent, the camera half and half with the double thrust (PairChopCamera).
bool UKukriWeaponComponent::IsHatchetDualChop() const
{
    return bDualThrust&&(bChopRight||bChopLeft);
}

void UKukriWeaponComponent::PairChopCamera(float T,FRotator& Rotation,float& Fov,FVector* Location) const
{
    HatchetDualChopRhythm::Camera(T,Rotation,Fov,Location);
    if(bChopRight&&bChopLeft)return;
    FRotator Thrust;float ThrustFov=0.f;
    KukriRhythm::DualThrustCamera(T,Thrust,ThrustFov);
    Rotation=(Rotation+Thrust)*.5f;Fov=(Fov+ThrustFov)*.5f;
    if(Location)*Location*=.5f;
}

const KukriRhythm::FSwing& UKukriWeaponComponent::SwingProfile() const
{
    // The dual chop takes the single chop's row for its swing pitch and viewmodel kick (its windows are the dual thrust's).
    return IsHatchetChop()||IsHatchetDualChop()?HatchetChopRhythm::Swing:KukriRhythm::Swings[Stage];
}

const KukriRhythm::FRift& UKukriWeaponComponent::RiftProfile() const
{
    return IsHatchetChop()?HatchetChopRhythm::Rift:KukriRhythm::Rifts[Stage];
}

void UKukriWeaponComponent::StageSwingCamera(int32 InStage,float T,FRotator& Rotation,float& Fov,FVector* Location) const
{
    if(bHatchetChop&&InStage==HatchetChopRhythm::Stage&&!bDualThrust&&!bDualSweep)HatchetChopRhythm::Camera(T,Rotation,Fov,Location);
    else KukriRhythm::SwingCamera(InStage,T,Rotation,Fov,Location);
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

void UKukriWeaponComponent::SpawnContactFX(const FHitResult& Hit,bool bWorld)
{
    auto* FX=GetWorld()?GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>():nullptr;
    if(FX)FX->SpawnBladeContact(Hit,Camera,bWorld);
    if(bWorld)PresentBladeScenery(Hit);
}

void UKukriWeaponComponent::SampleSkillBladeWall(const FTransform& From,const FTransform& To,const FVector& Base,const FVector& Tip,int32 Beat)
{
    if(Beat==LastSkillWallBeat)return;
    FHitResult Hit;
    for(int32 Lane=0;Lane<3;++Lane)
    {
        const FVector Edge=FMath::Lerp(Base,Tip,Lane*.5f);
        if(MeleeSmallTargets::BladeScenery(GetWorld(),GetOwner(),From.TransformPosition(Edge),To.TransformPosition(Edge),Hit))
        {LastSkillWallBeat=Beat;SpawnContactFX(Hit,true);return;}
    }
}

bool UKukriWeaponComponent::PublishBladeHit(AActor* Attacker,const FHitResult& Hit,const FColdSteelSkillShot& Outcome)
{
    if(!Attacker||!Attacker->HasAuthority()||Outcome.bRicochet||
        (Outcome.ItemDefinition!=TEXT("ue_tactical_hatchet")&&Outcome.ItemDefinition!=TEXT("ue_kukri"))||
        !Hit.GetActor()||!Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>())return false;
    if(auto* Executor=Attacker->FindComponentByClass<UKukriWeaponComponent>())
    {Executor->MulticastBladeTargetFX(Hit);return true;}
    return false;
}

namespace
{
UCameraComponent* ObserverBladeCamera(UWorld* World)
{
    auto* PC=World?World->GetFirstPlayerController():nullptr;
    auto* View=PC?PC->GetViewTarget():nullptr;
    return View?View->FindComponentByClass<UCameraComponent>():nullptr;
}
}
void UKukriWeaponComponent::PresentBladeScenery(const FHitResult& Hit)
{
    auto* P=Pawn();
    if(!P||!P->IsLocallyControlled()||GetNetMode()==NM_Standalone)return;
    if(P->HasAuthority())MulticastBladeScenery(Hit);
    else ServerBladeScenery(Hit.ImpactPoint,Hit.ImpactNormal);
}

void UKukriWeaponComponent::ServerBladeScenery_Implementation(FVector_NetQuantize10 Point,FVector_NetQuantizeNormal Normal)
{
    auto* P=Pawn();auto* World=GetWorld();
    if(!P||!World||Point.ContainsNaN()||Normal.ContainsNaN()||Normal.IsNearlyZero())return;
    const double Now=World->GetTimeSeconds();
    if(Now-LastServerScenery<.055)return;
    LastServerScenery=Now;
    const auto* Profile=ColdSteelAuthority::ForPawn(P);
    if(!Profile||Profile->ActiveProductionTool())return;
    const auto* Main=Profile->Equipped();
    const auto* HeldBlade=Profile->ActiveKukriWeapon();
    const auto* Off=Main?Profile->Equipped(Main==Profile->Equipped(6)?8:11):nullptr;
    if(!(HeldBlade&&IsKukri(*HeldBlade))&&!(Off&&IsKukri(*Off)))return;
    const FVector Eye=P->GetMeleeAimTransform().GetLocation();
    if(FVector::DistSquared(Eye,Point)>FMath::Square(175.f))return;
    FHitResult Contact;
    if(!MeleeSmallTargets::BladeScenery(World,P,Point+Normal*12.,Point-Normal*12.,Contact))return;
    FHitResult Blocker;FFPSAttackQuery Q(SCENE_QUERY_STAT(BladeSceneryCover),false,P);
    if(World->LineTraceSingleByChannel(Blocker,Eye,Contact.ImpactPoint+Contact.ImpactNormal*2.,ECC_Visibility,Q)
        &&FVector::DistSquared(Blocker.ImpactPoint,Contact.ImpactPoint)>FMath::Square(10.f))return;
    MulticastBladeScenery(Contact);
}

void UKukriWeaponComponent::MulticastBladeScenery_Implementation(const FHitResult& Hit)
{
    if(!Pawn()||Pawn()->IsLocallyControlled()||GetNetMode()==NM_DedicatedServer)return;
    if(auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())
        FX->SpawnBladeContact(Hit,ObserverBladeCamera(GetWorld()),true);
}

void UKukriWeaponComponent::PresentOwnerBladeHit(const FHitResult& Hit,uint32 Swing,uint8 Phase)
{
    if(!Pawn()||!Pawn()->IsLocallyControlled())return;
    if(Swing&&bShadowStep&&Shot.MasteryAttackSerial==Swing)
    {ConfirmShadowStepImpact(Hit,false,false);QueueShadowStepFX(Hit,false);return;}
    if(Swing&&(bAttacking||bHeavyAttack||bUppercut)&&Shot.MasteryAttackSerial==Swing&&Shot.MeleeDamagePhase==Phase)
    {ConfirmImpact(Hit,false);QueueContactFX(Hit,false);return;}
    SpawnContactFX(Hit,false);
}

void UKukriWeaponComponent::MulticastBladeTargetFX_Implementation(const FHitResult& Hit)
{
    if(!Pawn()||Pawn()->IsLocallyControlled()||GetNetMode()==NM_DedicatedServer)return;
    if(auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())
        FX->SpawnBladeContact(Hit,ObserverBladeCamera(GetWorld()),false);
}

FVector UKukriWeaponComponent::StrikeViewmodelOffset() const
{
    if(bShadowStep)return ShadowStepViewmodelOffset();
    // A confirmed hit carries the blade on through the hit-stop (stab: pressed in; slashes: dragged along the cut),
    // then lets go.
    if(!bPressIn||bDashAttack||ImpactAge<0.f)return FVector::ZeroVector;
    const auto& K=StrikeProfile();
    const float A=ImpactAge<PressStop?FMath::SmoothStep(0.f,PressStop,ImpactAge):FMath::Exp(-(ImpactAge-PressStop)*12.f);
    // The dual sweep's left blade drags the other way along its cut.
    return FVector(K.PressX,bOffhandSwing?-K.PressY:K.PressY,K.PressZ)*A;
}
