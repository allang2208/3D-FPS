#include "StaffOffhandMeleeComponent.h"
#include "StaffOffhandQuickMotion.h"
#include "StaffWeaponComponent.h"
#include "StaffChargeFlow.h"
#include "../Kukri/OffhandKukriComponent.h"
#include "../Kukri/OffhandKukriAuthoredPose.h"
#include "../Kukri/KukriArmsMeshComponent.h"
#include "../Kukri/KukriOffhandDraw.h"
#include "../Kukri/OffhandAxeQuickMotion.h"
#include "../Kukri/OffhandQuickClearance.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"

bool UStaffOffhandMeleeComponent::CanQuickCombat() const
{
    return CanQuickCombat(false);
}

bool UStaffOffhandMeleeComponent::CanQuickCombat(bool Uppercut) const
{
    const bool RigReady=bDrawHatchet&&!Uppercut?HasNativeChop():StrikeArms&&StrikeArms->GetSkeletalMeshAsset();
    const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();
    return Staff&&Staff->HasMeleeMoveset()&&IsEquipped()&&!IsEquipping()&&!IsActionPresentationActive()&&
        RigReady&&Blade&&Blade->GetStaticMesh();
}

void UStaffOffhandMeleeComponent::CaptureActionEntry()
{
    if(const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())
    {
        ActionStaffEntry=Staff->ActionPoseInCamera();
        bActionEntryCharge=!Staff->IsPrimaryAttacking()&&StaffChargeFlow::UsesKeys(ActionStaffEntry);
    }
    // Capture before the priority interrupt cancels consumables/casts. Blend the live left pose while lowering it.
    if(Arms)Arms->CaptureEntry(StaffOffhandQuickMotion::Entry*.5f);
}

void UStaffOffhandMeleeComponent::BeginActionPresentation(bool Uppercut,bool bUseHatchetChop)
{
    bUpperPresentation=Uppercut;
    bShadowStepPresentation=bShadowStepStage2Presentation=false;
    bHatchetChopPresentation=!Uppercut&&bUseHatchetChop;
    ActionLength=Uppercut?OffhandKukriUpper::Length:bHatchetChopPresentation?OffhandAxeQuickMotion::Length:OffhandKukriStrike::Length;
    bActionPresentation=true;ActionReturnAge=-1.f;ActionTime=-StaffOffhandQuickMotion::Entry;
    bQuickSupportReturn=false;
    bWasPresenting=true;
    if(bHatchetChopPresentation)
    {
        ActionTime=0.f;
        Arms->ClearEntry();
        Arms->CaptureLeftEntry(.08f);
        Arms->bMirrorRightToLeft=false;
    }
}

void UStaffOffhandMeleeComponent::BeginShadowStepPresentation(bool bStage2)
{
    bUpperPresentation=false;
    bHatchetChopPresentation=false;
    bShadowStepPresentation=true;
    bShadowStepStage2Presentation=bStage2;
    ActionLength=bStage2?OffhandShadowStepMotion::Stage2Length:OffhandShadowStepMotion::Stage1Length;
    bActionPresentation=true;ActionReturnAge=-1.f;
    ActionTime=bStage2?0.f:-StaffOffhandQuickMotion::Entry;
    bQuickSupportReturn=false;
    bWasPresenting=true;
}

bool UStaffOffhandMeleeComponent::UsesStrikeRig() const
{
    if(bHatchetChopPresentation)return false;
    if(ActionReturnAge>=0.f)return bReturnFromStrike&&ActionReturnAge<StaffOffhandQuickMotion::CancelReturn*.5f;
    if(bWhirlwindPresentation)return false;
    return bActionPresentation&&StaffOffhandQuickMotion::StrikeRig(ActionTime,ActionLength);
}

bool UStaffOffhandMeleeComponent::QuickStaffClearance(FVector& Offset,FQuat& Rotation) const
{
    namespace M=StaffOffhandQuickMotion;
    if(ActionReturnAge>=0.f&&bQuickSupportReturn)
    {
        const float Return=M::Ease(0.f,M::CancelReturn,ActionReturnAge);
        Offset=QuickSupportReturnOffset*(1.f-Return);
        Rotation=FQuat::Slerp(QuickSupportReturnRotation,FQuat::Identity,Return).GetNormalized();
        return true;
    }
    if(!bActionPresentation||bUpperPresentation||bShadowStepPresentation||bWhirlwindPresentation)return false;
    const float Progress=bHatchetChopPresentation?ActionTime/ActionLength:
        (ActionTime+M::Entry)/(ActionLength+M::Entry+M::Return);
    const auto Pose=OffhandQuickClearance::Staff(Progress,bHatchetChopPresentation);
    Offset=Pose.Offset;
    Rotation=FRotator(Pose.Angles.X,Pose.Angles.Y,Pose.Angles.Z).Quaternion();
    return true;
}

FStaffCastPose UStaffOffhandMeleeComponent::ActionStaffPose(const FStaffCastPose& Carry) const
{
    namespace M=StaffOffhandQuickMotion;
    if(ActionReturnAge>=0.f)return StaffCastMotion::Blend(ActionStaffRecovery,Carry,M::Ease(0.f,M::CancelReturn,ActionReturnAge));
    if(!bActionPresentation&&!bWhirlwindPresentation)return Carry;
    const float Entry=bWhirlwindPresentation?M::Ease(0.f,FMath::Min(.18f,WhirlwindReady),WhirlwindTime):
        bHatchetChopPresentation?M::Ease(0.f,.16f,ActionTime):M::Ease(-M::Entry,.08f,ActionTime);
    FStaffCastPose Pose=StaffCastMotion::Blend(ActionStaffEntry,Carry,Entry);
    FVector QuickOffset;FQuat QuickTurn;
    if(QuickStaffClearance(QuickOffset,QuickTurn))
    {
        Pose.Contact.AddToTranslation(QuickOffset);
        Pose.Contact.SetRotation((QuickTurn*Pose.Contact.GetRotation()).GetNormalized());
        Pose.Shoulder+=QuickOffset*.12;Pose.Elbow+=QuickOffset*.50;
        return Pose;
    }
    const float Avoid=bWhirlwindPresentation?
        M::Ease(0.f,WhirlwindReady*.68f,WhirlwindTime)*(1.f-M::Ease(WhirlwindReady+WhirlwindSpin+WhirlwindRecover*.5f,
            WhirlwindReady+WhirlwindSpin+WhirlwindRecover,WhirlwindTime)):
        bShadowStepPresentation?M::ShadowStepEvade(bShadowStepStage2Presentation,ActionTime):
        M::UpperEvade(ActionTime);
    // The long staff clears the centre early: move the full arm/shaft together and tip the head outward.
    // This is deliberately independent of the donor pistol's 60 cm sideways gun-frame sweep.
    const FVector Offset=bWhirlwindPresentation?FVector(-12.f,32.f,-18.f):bShadowStepPresentation?FVector(-6.f,28.f,-10.f):bUpperPresentation?FVector(-6.f,30.f,-12.f):FVector(-4.f,26.f,-9.f);
    const FQuat Outward(FVector::ForwardVector,FMath::DegreesToRadians(bWhirlwindPresentation?-26.f:bShadowStepPresentation?-22.f:bUpperPresentation?-24.f:-18.f)*Avoid);
    Pose.Contact.AddToTranslation(Offset*Avoid);
    Pose.Contact.SetRotation((Outward*Pose.Contact.GetRotation()).GetNormalized());
    Pose.Shoulder+=Offset*Avoid;Pose.Elbow+=Offset*Avoid;
    return Pose;
}

void UStaffOffhandMeleeComponent::EndActionPresentation(bool Interrupted)
{
    if(!bActionPresentation)return;
    if(Interrupted)
    {
        bQuickSupportReturn=QuickStaffClearance(QuickSupportReturnOffset,QuickSupportReturnRotation);
        if(const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())
            ActionStaffRecovery=ActionStaffPose(Staff->CarryPoseInCamera());
        bReturnFromStrike=UsesStrikeRig();
        ReturnFromLower=bHatchetChopPresentation?0.f:bReturnFromStrike?StaffOffhandQuickMotion::StrikeLower(ActionTime,ActionLength):StaffOffhandQuickMotion::NativeLower(ActionTime,ActionLength);
        ActionReturnAge=0.f;
    }
    else {ActionReturnAge=-1.f;bQuickSupportReturn=false;Arms->ClearEntry();}
    if(bHatchetChopPresentation)
    {
        if(Interrupted)Arms->CaptureLeftEntry(.12f);
        Arms->PlayAnimation(Idle,true);
        Arms->SetPlayRate(0.f);
        bHatchetChopPresentation=false;
    }
    bActionPresentation=false;
    bShadowStepPresentation=bShadowStepStage2Presentation=false;
}

FTransform UStaffOffhandMeleeComponent::SampleHatchetBlade(float Time)
{
    Arms->SetRelativeLocation(OffhandAxeQuickMotion::StaffOffset);
    if(Time>=OffhandAxeQuickMotion::CarryStart)
    {
        Arms->ClearEntry();
        if(Time<OffhandAxeQuickMotion::CarryEnd)
        {
            // Both endpoints are sampled on this frame. Keeping the native
            // recovery moving avoids a freeze at the start of a static blend.
            OffhandAxeQuickMotion::Sample(*Arms,HatchetChop,Time*OffhandAxeQuickMotion::ClipRate);
            Arms->CaptureLeftEntry(1.f,(Time-OffhandAxeQuickMotion::CarryStart)/(OffhandAxeQuickMotion::CarryEnd-OffhandAxeQuickMotion::CarryStart));
        }
        OffhandAxeQuickMotion::Sample(*Arms,Idle,Age);
    }
    else OffhandAxeQuickMotion::Sample(*Arms,HatchetChop,Time*OffhandAxeQuickMotion::ClipRate);
    const FTransform Frame=BladeFit*OffhandAxeQuickMotion::BladeWorld(*Arms);
    Blade->SetRelativeTransform(BladeFit*KukriOffhandDraw::Grip());
    return Frame;
}

FTransform UStaffOffhandMeleeComponent::ActionBladeInCamera(float Time) const
{
    FVector Wrist,Shoulder,Pole;FQuat Hand;FTransform Frame;
    const float SampleTime=FMath::Clamp(Time,0.f,ActionLength);
    if(bShadowStepPresentation)
    {
        OffhandShadowStepMotion::SamplePose(bShadowStepStage2Presentation,SampleTime,Wrist,Hand,Shoulder,Pole,Frame);
        const FTransform WristFrame(Hand,StaffOffhandQuickMotion::DonorRightHandShadowStep(bShadowStepStage2Presentation,Time)+Wrist);
        const bool Forward=OffhandShadowStepMotion::UsesForwardGrip(bShadowStepStage2Presentation,SampleTime);
        const FTransform Grip=Forward?OffhandShadowStepMotion::KukriInHand:OffhandKukriPose::KukriInHand;
        return BladeFit*Grip*WristFrame;
    }
    if(bUpperPresentation)OffhandKukriUpper::SamplePose(SampleTime,Wrist,Hand,Shoulder,Pole,Frame);
    else OffhandKukriStrike::SamplePose(SampleTime,Wrist,Hand,Shoulder,Pole,Frame);
    const FTransform WristFrame(Hand,StaffOffhandQuickMotion::DonorRightHand(Time,bUpperPresentation)+Wrist);
    const bool Forward=bUpperPresentation&&SampleTime>=OffhandKukriUpper::DigitsAt&&SampleTime<=OffhandKukriUpper::DigitsEnd;
    // Contact query and visible knife consume exactly the same authored frame, never last tick's socket.
    const FTransform Grip=Forward?OffhandKukriUpper::KukriInHand:OffhandKukriPose::KukriInHand;
    return BladeFit*Grip*WristFrame;
}

void UStaffOffhandMeleeComponent::SampleActionPose()
{
    namespace M=StaffOffhandQuickMotion;
    if(!Arms||!StrikeArms||!Blade||!Camera.IsValid())return;
    if(bHatchetChopPresentation&&bActionPresentation)
    {
        SampleHatchetBlade(ActionTime);
        return;
    }
    const bool Strike=UsesStrikeRig();
    float Lower=Strike?M::StrikeLower(ActionTime,ActionLength):M::NativeLower(ActionTime,ActionLength);
    if(ActionReturnAge>=0.f)
    {
        if(Strike)Lower=FMath::Lerp(ReturnFromLower,1.f,M::Ease(0.f,M::CancelReturn*.5f,ActionReturnAge));
        else if(bReturnFromStrike)Lower=1.f-M::Ease(M::CancelReturn*.5f,M::CancelReturn,ActionReturnAge);
        else Lower=ReturnFromLower*(1.f-M::Ease(0.f,M::CancelReturn,ActionReturnAge));
    }
    if(Strike)
    {
        const float Clamped=FMath::Clamp(ActionTime,0.f,ActionLength);
        StrikeArms->StrikeTime=(bUpperPresentation||bShadowStepPresentation)?-1.f:Clamped;
        StrikeArms->UppercutTime=bUpperPresentation?Clamped:-1.f;
        StrikeArms->ShadowStepTime=bShadowStepPresentation?Clamped:-1.f;
        StrikeArms->bShadowStepStage2=bShadowStepStage2Presentation;
        StrikeArms->RightHandInCamera=bShadowStepPresentation?
            M::DonorRightHandShadowStep(bShadowStepStage2Presentation,ActionTime):
            M::DonorRightHand(ActionTime,bUpperPresentation);
        const auto* OffhandCtrl=GetOwner()?GetOwner()->FindComponentByClass<UOffhandKukriComponent>():nullptr;
        const FVector Press=bShadowStepPresentation&&OffhandCtrl?OffhandCtrl->ShadowStepPressOffset():FVector::ZeroVector;
        StrikeArms->PresentationOffset=M::HiddenOffset*Lower+Press;
        StrikeArms->TickAnimation(0.f,false);StrikeArms->RefreshBoneTransforms();
        FTransform Frame=ActionBladeInCamera(ActionTime);Frame.AddToTranslation(M::HiddenOffset*Lower+Press);
        Blade->SetWorldTransform(Frame*Camera->GetComponentTransform());
    }
    else
    {
        // Freeze the idle phase across the action; return to that same native grasp without replaying Equip.
        Arms->SetRelativeLocation(FVector(2.f,-4.f,-1.f)+M::HiddenOffset*Lower);
        Arms->SetPosition(Age,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
        Blade->SetRelativeTransform(BladeFit*KukriOffhandDraw::Grip());
    }
}
