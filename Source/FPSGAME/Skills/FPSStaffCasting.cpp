#include "FPSFireballComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "Camera/CameraComponent.h"

void UFPSFireballComponent::BeginStaffGesture()
{
    auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();
    bStaffGesture=false;CastingStaff.Reset();
    if(!Staff||!Staff->CanBeginCast())return;
    // Capture the actual carry/sprint pose before selecting the new gesture.
    StaffEntry=Staff->CarryPoseInCamera();CastingStaff=Staff;bStaffGesture=true;
    bPowerFistGesture=false; // Self-cast magic also uses the held staff.
}

void UFPSFireballComponent::CaptureStaffRecovery()
{
    if(bStaffGesture&&CastingStaff.IsValid())
        StaffRecoveryEntry=SampleStaffMotion(CastingStaff->CarryPoseInCamera());
}

FStaffCastPose UFPSFireballComponent::SampleStaffMotion(const FStaffCastPose& Current) const
{
    if(!IsStaffCasting())return Current;
    switch(HandPhase)
    {
    case EFireballHandPhase::Raising:
    case EFireballHandPhase::ReadyingRelease:
        return StaffCastMotion::Raise(StaffEntry,HandPhaseFraction());
    case EFireballHandPhase::Releasing:
    {
        auto Pose=StaffCastMotion::Swing(PhaseAge);
        for(const float Contact:ReleaseImpactAges)Pose=StaffCastMotion::WithImpact(Pose,PhaseAge-Contact);
        return Pose;
    }
    case EFireballHandPhase::Recovering:
        return StaffCastMotion::Recover(StaffRecoveryEntry,Current,HandPhaseFraction());
    default:return Current;
    }
}

bool UFPSFireballComponent::TryStaffCastOrigin(FVector& OutOrigin) const
{
    if(!IsStaffCasting()||!CastingStaff.IsValid()||!CastingStaff->IsEquipped())return false;
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return false;
    // Sample the same phase as the shaft, not a previous-frame hand socket.
    OutOrigin=Camera->GetComponentTransform().TransformPosition(StaffCastMotion::Tip(
        SampleStaffMotion(CastingStaff->CarryPoseInCamera())));return true;
}

float UFPSFireballComponent::GesturePhaseDuration(EFireballHandPhase Phase) const
{
    if(bStaffGesture)
    {
        switch(Phase)
        {
        case EFireballHandPhase::Raising:return FMath::Max(.01f,RaiseDuration);
        case EFireballHandPhase::ReadyingRelease:return StaffCastMotion::ReadySeconds;
        case EFireballHandPhase::Releasing:return StaffCastMotion::SwingSeconds;
        default:return StaffCastMotion::RecoverSeconds;
        }
    }
    if(bPowerFistGesture)
        return FMath::Max(.01f,Phase==EFireballHandPhase::ReadyingRelease?PowerFistSettings.ClenchStart:
            Phase==EFireballHandPhase::Releasing?PowerFistSettings.RecoverStart-PowerFistSettings.ClenchStart:PowerFistSettings.RecoveryDuration());
    return FMath::Max(.01f,Phase==EFireballHandPhase::Raising?RaiseDuration:
        Phase==EFireballHandPhase::Releasing?ReleaseDuration/FireballCastMotion::ReleasePushSpeed:
        Phase==EFireballHandPhase::ReadyingRelease?ReleaseEntryDuration/FireballCastMotion::ReleaseEntrySpeed:RecoveryDuration);
}

float UFPSFireballComponent::ReleaseContactAge() const
{
    if(bStaffGesture)return StaffCastMotion::ContactSeconds;
    if(bPowerFistGesture)return PowerFistSettings.ClenchEnd-PowerFistSettings.ClenchStart;
    return FMath::Clamp(LaunchContactTime,0.f,FMath::Max(.01f,ReleaseDuration))/FireballCastMotion::ReleasePushSpeed;
}

float UFPSFireballComponent::ReleaseEndAge() const
{
    if(bStaffGesture)return FMath::Max(StaffCastMotion::SwingSeconds+StaffCastMotion::HoldSeconds*GestureSpeed,ReleaseHoldEndAge);
    if(bPowerFistGesture)return PowerFistSettings.RecoverStart-PowerFistSettings.ClenchStart;
    const float Push=FMath::Max(.01f,ReleaseDuration)/FireballCastMotion::ReleasePushSpeed;
    const float Entry=FMath::Max(.01f,ReleaseEntryDuration)/FireballCastMotion::ReleaseEntrySpeed;
    const float Hold=FMath::Max(0.f,FireballCastMotion::ReleaseTotalSeconds-Entry-Push-FMath::Max(.01f,RecoveryDuration));
    return FMath::Max(Push+Hold*GestureSpeed,ReleaseHoldEndAge);
}
