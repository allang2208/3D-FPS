#include "StaffOffhandMeleeComponent.h"
#include "StaffWeaponComponent.h"
#include "../Kukri/KukriArmsMeshComponent.h"
#include "../Kukri/KukriWeaponComponent.h"
#include "../Kukri/KukriOffhandDraw.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"

bool UStaffOffhandMeleeComponent::CanWhirlwind() const
{
    const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();
    return Staff&&Staff->CanBeginCast()&&IsEquipped()&&!IsEquipping()&&!IsActionPresentationActive()&&OwnsLeftHand()&&
        Arms&&Arms->GetSkeletalMeshAsset()&&Blade&&Blade->GetStaticMesh()&&Whirlwind;
}

void UStaffOffhandMeleeComponent::BeginWhirlwindPresentation()
{
    CaptureActionEntry();
    Arms->ClearEntry();Arms->CaptureLeftEntry(.11f);
    bWhirlwindPresentation=true;bWasPresenting=true;ActionReturnAge=-1.f;
    WhirlwindTime=WhirlwindClipTime=0.f;
    bQuickSupportReturn=false;
    Arms->bMirrorRightToLeft=true;
    Arms->PlayAnimation(Whirlwind,false);Arms->SetPlayRate(0.f);
}

void UStaffOffhandMeleeComponent::SetWhirlwindPose(float Time,float ClipTime,float Ready,float Spin,float Recover)
{
    WhirlwindTime=Time;WhirlwindClipTime=ClipTime;
    WhirlwindReady=Ready;WhirlwindSpin=Spin;WhirlwindRecover=Recover;
}

void UStaffOffhandMeleeComponent::SampleWhirlwindPose()
{
    Arms->SetRelativeLocation(FVector(2.f,-4.f,-1.f));
    Arms->SetPosition(WhirlwindClipTime,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    Blade->SetRelativeTransform(BladeFit*KukriOffhandDraw::Grip());
    // Publish the trail from the same displayed left grip, after the shared controller's camera turn.
    if(auto* Kukri=GetOwner()->FindComponentByClass<UKukriWeaponComponent>())
        Kukri->PublishStaffWhirlwindBlade(Blade->GetComponentTransform());
}

void UStaffOffhandMeleeComponent::EndWhirlwindPresentation(bool Interrupted)
{
    if(!bWhirlwindPresentation)return;
    if(Interrupted)
    {
        if(const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())
            ActionStaffRecovery=ActionStaffPose(Staff->CarryPoseInCamera());
        ActionReturnAge=0.f;bReturnFromStrike=false;ReturnFromLower=0.f;
    }
    bWhirlwindPresentation=false;
    Arms->ClearEntry();Arms->CaptureLeftEntry(.18f);
    Arms->bMirrorRightToLeft=false;
    Arms->PlayAnimation(Idle,true);Arms->SetPlayRate(0.f);
}
