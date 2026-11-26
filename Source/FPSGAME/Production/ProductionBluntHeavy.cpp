#include "ProductionToolComponent.h"
#include "ProductionBluntCombo.h"
#include "WarhammerHeavyMotion.h"
#include "../Skills/LeapStrikeMotion.h"
#include "ThunderHammerCallIntent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"

void UProductionToolComponent::BeginPrimaryAttack()
{
    if(IsLeapStrikeActive()||IsPojunChainOccupied()||IsQuickCombatActive())return;
    if(HandleThunderPrimary())return;
    if(Character.IsValid()&&Character->RuneSword&&Character->RuneSword->IsToolGuardRequested())return;
    if(PojunAttack==PojunGrip::EAttack::Tengyun){BeginUse();return;}
    if(bBluntWhirlwind||bBluntUppercut||ThunderCatchAge>=0.f||ThunderCallReleaseAge>=0.f)return;
    if(Kind!=TEXT("warhammer")){BeginUse();return;}
    if(Elapsed>=0.f){BeginUse();return;}
    if(bBluntCharging||bBluntReturningCharge||EquipElapsed>=0.f||!CanUse()||!HasReadyPresentation()||
        Character->IsCastBlockingLeftHandAction())return;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item)return;
    ApplyToolStats(Item,Profile);
    if(Profile->Stamina()<=0.f||(!bThunderCallSeat&&!Profile->CanSpendStamina(float(ToolStats.StaminaCost))))return;
    bThunderCallHoldConfirmed=false;
    bBluntCharging=true;bBluntHeavy=bBluntSprintAttack=false;bQueuedBluntAttack=false;
    BluntSprintSeconds=0.f;
    BluntChargeStartedAt=GetWorld()->GetTimeSeconds();
    ++BluntAttackId;
    if(bThunderCallSeat)bThunderCallCharging=false; // TapPending: input ownership only, no charge pose/FX.
    if(GetNetMode()!=NM_Standalone)ServerBeginBluntCharge(BluntAttackId,EquippedId);
}

float UProductionToolComponent::BluntChargeResume(float Held) const
{
    if(bThunderThrowSeat||bThunderCallSeat)return 0.f;
    if(bFinalTollHead)
        return ProductionBluntCombo::RealForWindupClip(
            FinalTollHeavy::ChargeSource(Held/FMath::Max(.01f,BluntChargeSeconds)),
            RealContactSeconds(),ContactSeconds,RateScale,0);
    if(Held<=.20f)return 0.f;
    const float Source=WarhammerHeavy::ChargeSource(Held*WarhammerHeavy::ChargeSeconds/BluntChargeSeconds);
    float Low=0.f,High=ContactSeconds;
    for(int32 I=0;I<18;++I)
    {
        const float Mid=(Low+High)*.5f;
        if(ProductionBluntCombo::ChargeResumeSourceTime(Mid,ContactSeconds,SwingSeconds)<Source)Low=Mid;else High=Mid;
    }
    return (Low+High)*.5f/RateScale;
}

void UProductionToolComponent::ReleasePrimaryAttack()
{
    if(Kind!=TEXT("warhammer")||!bBluntCharging)return;
    if(!CanUse(true)||Character->IsCastBlockingLeftHandAction()){CancelUse();return;}
    if(const auto* Profile=ColdSteelAuthority::ForPawn(Character.Get());Profile&&Profile->Stamina()<=0.f)
    {CancelHeavyCharge();return;}
    const float Held=float(GetWorld()->GetTimeSeconds()-BluntChargeStartedAt);
    if(bThunderCallSeat)
    {
        const auto Phase=ThunderHammerCallIntent::Phase(Held,BluntChargeSeconds);
        if(Phase==ThunderHammerCallIntent::EPhase::Ready){ReleaseThunderCall();return;}
        // Once the lift has begun, an early release returns to grip instead of
        // splicing the one-handed charge pose into a two-handed normal attack.
        if(Phase==ThunderHammerCallIntent::EPhase::Charging){CancelHeavyCharge();return;}
    }
    bBluntCharging=false;bBluntReleaseCharge=true;
    bBluntHeavy=Held>=BluntChargeSeconds;
    if(!bThunderCallSeat&&Held>.20f)NextBluntStage=0;
    if(bThunderThrowSeat&&!bBluntHeavy)HandOffBluntPose();
    if(bThunderCallSeat){bThunderCallCharging=false;ClearThunderCallVisual();FinishThunderCallResources();}
    BeginUse();
    if(PojunAttack!=PojunGrip::EAttack::Ordinary){bBluntReleaseCharge=false;return;}
    if(Elapsed<0.f){bBluntCharging=true;CancelUse();return;}
    bBluntReleaseCharge=false;
    if(!bBluntHeavy)Elapsed=BluntChargeResume(Held);
}

float UProductionToolComponent::BluntChargePoseSeconds() const
{
    if(bBluntReturningCharge)
        return BluntChargeReturnFrom*(1.f-FMath::SmoothStep(0.f,BluntChargeReturnDuration,BluntChargeReturnAge));
    const float Held=float(GetWorld()->GetTimeSeconds()-BluntChargeStartedAt);
    const float Progress=bThunderCallSeat?ThunderHammerCallIntent::Progress(Held,BluntChargeSeconds):
        FMath::Clamp(Held/BluntChargeSeconds,0.f,1.f);
    return Progress*WarhammerHeavy::ChargeSeconds;
}

void UProductionToolComponent::CancelHeavyCharge()
{
    if(!IsHeavyCharging())return;
    if(Character->HasAuthority()&&!Character->IsLocallyControlled())
    {
        ServerCancelBluntAttack_Implementation(BluntServerAttackId);
        ClientBluntAttackResult(BluntServerAttackId,0,false,false,false);return;
    }
    const float From=bThunderCallSeat&&CurrentMotion!=Motions.FindRef(TEXT("ThunderCallCharge"))?
        0.f:BluntChargePoseSeconds();
    CancelUse();
    if(bThunderCallSeat&&From<=UE_SMALL_NUMBER)return; // No lift occurred during a pending click.
    // Return along the charge pose that was actually presented.
    bBluntReturningCharge=true;BluntChargeReturnFrom=From;BluntChargeReturnAge=0.f;
    BluntChargeReturnDuration=FMath::Clamp(From*.25f,.1f,.45f);
}

void UProductionToolComponent::AdvanceBluntCharge(float Delta)
{
    if((bBluntCharging||bBluntReturningCharge)&&(!CanUse(true)||Character->IsCastBlockingLeftHandAction()))
    {CancelUse();return;}
    if(bBluntReturningCharge)
    {
        BluntChargeReturnAge=FMath::Min(BluntChargeReturnDuration,BluntChargeReturnAge+Delta*HasteActionRate);
        if(BluntChargeReturnAge>=BluntChargeReturnDuration){bBluntReturningCharge=false;VisualTime=0.f;}
    }
}

float UProductionToolComponent::HeavyChargeFraction() const
{
    return Kind==TEXT("warhammer")&&bBluntCharging&&IsEquipped()&&CanUse()&&
        !Character->IsCastBlockingLeftHandAction()?
        FMath::Clamp(float(GetWorld()->GetTimeSeconds()-BluntChargeStartedAt)/BluntChargeSeconds,0.f,1.f):0.f;
}

bool UProductionToolComponent::GetGroundSlamCameraPitch(float& Pitch,float& Weight) const
{
    if(bLeapStrike)
    {Pitch=LeapStrike::ViewPitch;Weight=LeapStrike::GroundWeight(LeapAge);return Weight>0.f;}
    if(!IsGroundSlamActive()||!bBluntFloorTarget||!CanUse(true))return false;
    // A fixed, higher presentation pitch leaves the hammer below centre.
    // Do not look at the impact point or steer the player's viewing yaw.
    Pitch=WarhammerHeavy::PlantedViewPitch;
    Weight=WarhammerHeavy::ViewWeight(AuthoredElapsed());return Weight>0.f;
}

bool UProductionToolComponent::IsGroundSlamActive() const
{
    return (bBluntHeavy&&!UsesFinalTollHeavy()&&!UsesThunderThrowHeavy()&&Elapsed>=0.f)||(Character.IsValid()&&Character->HasAuthority()&&
        GetWorld()&&GetWorld()->GetTimeSeconds()<BluntServerGroundSlamUntil);
}

bool UProductionToolComponent::GetGroundSlamCameraLocation(FVector& Point) const
{
    if(bLeapStrike)return GetLeapStrikeCameraLocation(Point);
    if(!bBluntHeavy||UsesFinalTollHeavy()||UsesThunderThrowHeavy()||Elapsed<0.f||!CanUse(true))return false;
    const float Time=AuthoredElapsed();
    // A posture displacement, not recoil: do not scale it by camera shake or
    // feed the posed chest clearance back into this committed eye anchor.
    Point=FMath::Lerp(Character->GetMeleeAimTransform().GetLocation(),BluntSlamEye,WarhammerHeavy::AnchorWeight(Time))
        +BluntSlamRotation.RotateVector(WarhammerHeavy::EyeOffset(Time));
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(WarhammerBendCamera),false,Character.Get());
    if(GetWorld()->SweepSingleByChannel(Hit,BluntSlamEye,Point,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(6.f),Query))
        Point=FMath::Lerp(BluntSlamEye,Point,FMath::Max(0.f,Hit.Time-.02f));
    return true;
}
