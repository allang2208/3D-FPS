#include "SpellbookComponent.h"
#include "SpellbookFocusMotion.h"
#include "SpellbookFocusInterruptMotion.h"
#include "SpellbookAuthoredGrip.h"
#include "SpellbookBookOrientation.h"
#include "../Staff/StaffWeaponComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Skills/FPSFireballComponent.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../../Combat/CombatStatusFormula.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "SpellbookReturnDebug.inl"

namespace
{
void ApplyClosingPages(USkeletalMeshComponent& Mesh,const TArray<FTransform>& Deltas,float Weight)
{
    // Preserve the live page-turn shape at entry, then converge onto the
    // reverse opening clip as the covers close. Hinge/root tracks stay exact.
    const auto& Ref=Mesh.GetSkeletalMeshAsset()->GetRefSkeleton();
    const auto Local=Mesh.GetBoneSpaceTransformsView();
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    for(int32 I=0;I<Pose.Num();++I)
    {
        Pose[I]=Local[I];
        if(Deltas.IsValidIndex(I))
        {
            Pose[I].SetRotation((FQuat::Slerp(FQuat::Identity,Deltas[I].GetRotation(),Weight)*Local[I].GetRotation()).GetNormalized());
            Pose[I].AddToTranslation(Deltas[I].GetLocation()*Weight);
        }
        if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
    }
    Mesh.MarkRenderDynamicDataDirty();
}
}

void USpellbookComponent::CreateFocusMeshes()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn||!Camera.IsValid())return;
    FocusBook=NewObject<USkeletalMeshComponent>(Pawn,TEXT("SpellbookFloatingPages"));
    Pawn->AddInstanceComponent(FocusBook);FocusBook->SetupAttachment(Camera.Get());
    FocusBook->SetOnlyOwnerSee(true);FocusBook->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FocusBook->SetCanEverAffectNavigation(false);FocusBook->SetCastShadow(false);
    FocusBook->bReceivesDecals=false;FocusBook->SetVisibility(false);FocusBook->RegisterComponent();
    FocusBook->SetComponentTickEnabled(false);FocusBook->SetBoundsScale(2.f);
    FocusBook->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    // The owner/world views share one evaluated bone buffer, without a second graph.
    FocusWorldBook=NewObject<USkeletalMeshComponent>(Pawn,TEXT("SpellbookFloatingWorldPages"));
    Pawn->AddInstanceComponent(FocusWorldBook);FocusWorldBook->SetupAttachment(Pawn->GetRootComponent());
    FocusWorldBook->SetOwnerNoSee(true);FocusWorldBook->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FocusWorldBook->SetCanEverAffectNavigation(false);FocusWorldBook->SetCastShadow(false);
    FocusWorldBook->bReceivesDecals=false;FocusWorldBook->SetVisibility(false);FocusWorldBook->RegisterComponent();
    FocusWorldBook->SetComponentTickEnabled(false);FocusWorldBook->SetBoundsScale(2.f);
}

bool USpellbookComponent::IsFocusEmpowered() const
{
    if(UsesNetFocusAuthority())return IsConcentrating()&&
        GetWorld()->GetTimeSeconds()-NetFocusStartedAt>=SpellbookFocusMotion::OpenLength;
    // Opening/closing still own the animation, but only the fully open hold grants stats.
    return bFocusPair&&bFocusDesired&&IsConcentrating()&&FocusAge>=SpellbookFocusMotion::OpenLength&&OwnsLeftHand();
}

bool USpellbookComponent::ToggleFocus()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Staff=Pawn?Pawn->FindComponentByClass<UStaffWeaponComponent>():nullptr;
    if(!bFocusPair||!Staff||!Staff->IsEquipped())return false;
    if(bFocusInterrupted)return false;
    if(IsFocusActive())
    {
        bFocusDesired=!bFocusDesired;
        if(!bFocusDesired&&!bFocusClosing)BeginCloseFocus();
        return true;
    }
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();
    const auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
    if(!OwnsLeftHand()||Staff->IsBusy()||Pawn->IsDoorPushActive()||Pawn->IsResolvingActionInterrupt()
        ||(Potion&&Potion->IsActive())||(Magic&&Magic->IsGestureActive())||(Quick&&Quick->IsOccupyingLeftHand())
        ||!FocusBook||!FocusBook->GetSkeletalMeshAsset()||!OpenClip||!FlipClip)return false;
    Pawn->ExitSprintForWeapon();Arms->CaptureFocusEntry();
    UCombatStatusFormula::GetOrAdd(Pawn);
    FocusAge=PagePhase=PageAlpha=OpenAlpha=0.f;
    bFocusDesired=true;bFocusClosing=bFocusDetached=bFocusInterrupted=false;
    Arms->SetFocusPose(0.f,1.f,false);
    SendFocusRequest(1);
    return true;
}

void USpellbookComponent::BeginCloseFocus()
{
    SendFocusRequest(2);
    bFocusClosing=true;CloseAge=0.f;ClosePageAlpha=PageAlpha;
    ReturnStartTime=FMath::Clamp(FocusAge,0.f,SpellbookFocusMotion::OpenLength);
    CloseBookSeconds=FMath::Max(0.f,ReturnStartTime-SpellbookFocusMotion::OpeningAt);
    FocusReturnCamera=bFocusDetached?FocusBook->GetRelativeTransform()
        :Book->GetComponentTransform().GetRelativeTransform(Camera->GetComponentTransform());
    ClosePageDeltas.Reset();
    if(bFocusDetached)
    {
        const auto Current=FocusBook->GetBoneSpaceTransformsView();
        const TArray<FTransform> Snapshot(Current.GetData(),Current.Num());
        FocusBook->SetAnimation(OpenClip);FocusBook->SetPlayRate(0.f);
        FocusBook->SetComponentSpaceTransformsDoubleBuffering(false);
        FocusBook->SetPosition(SpellbookFocusMotion::SourceTime(ReturnStartTime),false);
        FocusBook->TickAnimation(0.f,false);FocusBook->RefreshBoneTransforms();
        const auto Base=FocusBook->GetBoneSpaceTransformsView();
        ClosePageDeltas.Init(FTransform::Identity,Base.Num());
        for(const int32 I:PageBones)if(Snapshot.IsValidIndex(I)&&I<Base.Num())
        {
            ClosePageDeltas[I].SetRotation((Snapshot[I].GetRotation()*Base[I].GetRotation().Inverse()).GetNormalized());
            ClosePageDeltas[I].SetLocation(Snapshot[I].GetLocation()-Base[I].GetLocation());
        }
    }
}

float USpellbookComponent::FocusRecoveryBlend() const
{
    if(bFocusInterrupted&&InterruptAge>=SpellbookFocusInterruptMotion::Catch)return 1.f;
    // Start at the actually displayed opening pose when cancelled mid-action.
    return bFocusClosing?SpellbookFocusMotion::Ease(0.f,
        FMath::Min(SpellbookFocusPolish::RecoveryBlendSeconds,ReturnStartTime),CloseAge):0.f;
}

FTransform USpellbookComponent::FocusHandSway(float PoseTime) const
{
    namespace Motion=SpellbookFocusMotion;
    if(bFocusInterrupted)return FTransform::Identity;
    if(!IsFocusActive()||!Arms||PoseTime<Motion::Gather)return FTransform::Identity;
    float Weight=Motion::Ease(Motion::OpenLength,Motion::OpenLength+.4f,FocusAge);
    if(bFocusClosing)Weight*=1.f-Motion::Ease(0.f,.35f,CloseAge*Motion::PlaybackRate);
    if(Weight<=0.f)return FTransform::Identity;
    const float Time=Arms->MotionTime,Phase=Arms->StridePhase,Move=Arms->MoveWeight;
    const FVector Breath(.12f*FMath::Sin(Time*1.3f),.22f*FMath::Sin(Time*1.7f),.42f*FMath::Sin(Time*1.9f));
    const FVector Step(.24f*FMath::Sin(2.f*Phase-.4f),.34f*FMath::Sin(Phase-.25f),-.40f*FMath::Cos(2.f*Phase-.45f));
    const FVector Tremor(.025f*FMath::Sin(Time*8.1f),.04f*FMath::Sin(Time*7.3f),.055f*FMath::Sin(Time*9.7f));
    // Reading retains one palm/elbow shape across walking, stopping and crouch.
    // Transport the entire arm gently; movement never adds another palm roll.
    return FTransform(FQuat::Identity,(Breath+Step*Move+Tremor)*Weight);
}

void USpellbookComponent::CancelFocus()
{
    if(UsesNetFocusAuthority())StopNetFocus(false);
    if(FocusAge>=0.f)SendFocusRequest(0);
    FocusAge=-1.f;bFocusDesired=bFocusClosing=bFocusDetached=bFocusInterrupted=false;
    InterruptAge=0.f;InterruptBookEntry.Reset();InterruptBookClosed.Reset();
    PageAlpha=OpenAlpha=PagePhase=0.f;
    ClosePageDeltas.Reset();
    if(Arms)Arms->SetFocusPose(-1.f,0.f,false);
    if(FocusBook)FocusBook->SetVisibility(false);
    if(FocusWorldBook)FocusWorldBook->SetVisibility(false);
    GoldFade=0.f;ShowFocusGold(false);
}

void USpellbookComponent::AdvanceFocus(float Delta)
{
    if(!IsFocusActive())return;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    if(!bFocusPair||!OwnsLeftHand()||Pawn->IsDoorPushActive()||(Potion&&Potion->IsActive()))
    {CancelFocus();return;}
    namespace Motion=SpellbookFocusMotion;
    if(bFocusInterrupted){AdvanceFocusInterrupt(Delta);return;}
    if(!bFocusClosing)
    {
        const float PreviousAge=FocusAge;FocusAge+=Delta;
        const float SourceTime=Motion::SourceTime(FocusAge);
        OpenAlpha=Motion::OpeningAlpha(SourceTime);
        if(FocusAge>=Motion::OpenLength)
        {
            const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();
            const float PageRate=Magic&&Magic->IsStaffCasting()?2.f:1.f;
            // Integrate speed into the existing phase so entering/leaving a cast never jumps pages.
            const float ReadingDelta=FMath::Max(0.f,FocusAge-FMath::Max(PreviousAge,Motion::OpenLength));
            PagePhase=FMath::Fmod(PagePhase+ReadingDelta*PageRate,Motion::PageCycle);
            PageAlpha=.5f-.5f*FMath::Cos(2.f*PI*PagePhase/Motion::PageCycle);
        }
        Arms->SetFocusPose(FMath::Min(SourceTime,Motion::Gather),1.f,false);
    }
    else
    {
        CloseAge+=Delta;
        PageAlpha=ClosePageAlpha;
        const float SourceTime=Motion::SourceTime(ReturnStartTime-CloseAge);
        OpenAlpha=Motion::OpeningAlpha(SourceTime);
        Arms->SetFocusReturn(SourceTime);
        if(CloseAge>=ReturnStartTime)
        {
            const bool Reopen=bFocusDesired;
            CancelFocus();UpdateVisibility();
            if(Reopen){Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();ToggleFocus();}
        }
    }
}

void USpellbookComponent::PresentFocusBook()
{
    if(!IsFocusActive()||!FocusBook||!Camera.IsValid())return;
    if(bFocusInterrupted){PresentFocusInterruptBook();return;}
    namespace Motion=SpellbookFocusMotion;
    const float SourceTime=Motion::SourceTime(bFocusClosing?ReturnStartTime-CloseAge:FocusAge);
    if(bFocusClosing&&SourceTime<Motion::Detach)
    {
        // All fingers are closed before the accepted rigid return begins.
        // Reuse normal carry attachment, with no second book interpolation.
        bFocusDetached=false;GoldFade=0.f;return;
    }
    if(!bFocusDetached)
    {
        if(bFocusClosing||SourceTime<Motion::Detach)return;
        // Resolve the exact contact time when a frame crosses release.
        Arms->SetFocusPose(Motion::Detach,1.f,false);
        Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
        FTransform Hand=Arms->GetSocketTransform(TEXT("hand_l"),RTS_World);
        Hand.SetScale3D(FVector::OneVector);
        FocusDepartCamera=(SpellbookBookOrientation::InHand()*Hand).GetRelativeTransform(Camera->GetComponentTransform());
        bFocusDetached=true;DetachAge=Motion::Detach;
        Arms->SetFocusPose(FMath::Min(SourceTime,Motion::Gather),1.f,false);
        Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    }
    const FTransform Frame=bFocusClosing?Motion::ReturnBook(FocusReturnCamera,FocusDepartCamera,SourceTime)
        :Motion::OpenBook(FocusDepartCamera,FocusAge);
    FocusBook->SetRelativeTransform(Frame);
    // V27 changes only the book's coordinate direction. Accepted cover/page
    // articulation follows the same staged clock forward and backward.
    const bool Pages=!bFocusClosing&&FocusAge>=Motion::OpenLength;
    auto* Clip=Pages?FlipClip.Get():OpenClip.Get();
    if(!FocusBook->GetSingleNodeInstance()||FocusBook->GetSingleNodeInstance()->GetCurrentAsset()!=Clip)
    {FocusBook->SetAnimation(Clip);FocusBook->SetPlayRate(0.f);}
    FocusBook->SetComponentSpaceTransformsDoubleBuffering(false);
    FocusBook->SetPosition(Pages?PageAlpha*Clip->GetPlayLength():FMath::Min(SourceTime,Clip->GetPlayLength()),false);
    FocusBook->TickAnimation(0.f,false);FocusBook->RefreshBoneTransforms();
    if(bFocusClosing)ApplyClosingPages(*FocusBook,ClosePageDeltas,1.f-Motion::Ease(0.f,CloseBookSeconds,CloseAge));
    if(FocusWorldBook)FocusWorldBook->SetWorldTransform(FocusBook->GetComponentTransform());
    PresentFocusGold();
}
