#include "SpellbookComponent.h"
#include "SpellbookFocusMotion.h"
#include "SpellbookAuthoredGrip.h"
#include "SpellbookReturnContact.h"
#include "../Staff/StaffWeaponComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Skills/FPSFireballComponent.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "SpellbookReturnDebug.inl"

namespace
{
void CloseCurrentPages(USkeletalMeshComponent& Mesh,float Alpha)
{
    // The manually sampled book uses one writable pose buffer. Fold directly
    // from the frozen current page pose; do not rewind the page-turn animation.
    const auto& Ref=Mesh.GetSkeletalMeshAsset()->GetRefSkeleton();
    const auto Local=Mesh.GetBoneSpaceTransformsView();
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    for(int32 I=0;I<Pose.Num();++I)
    {
        Pose[I].Blend(Local[I],Ref.GetRefBonePose()[I],Alpha);
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

bool USpellbookComponent::ToggleFocus()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Staff=Pawn?Pawn->FindComponentByClass<UStaffWeaponComponent>():nullptr;
    if(!bFocusPair||!Staff||!Staff->IsEquipped())return false;
    if(IsFocusActive())
    {
        bFocusDesired=!bFocusDesired;bQueuedBookStrike=false;
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
    FocusAge=PagePhase=PageAlpha=OpenAlpha=0.f;
    bFocusDesired=true;bFocusClosing=bFocusDetached=bQueuedBookStrike=false;
    Arms->SetFocusPose(0.f,1.f,false);
    return true;
}

void USpellbookComponent::BeginCloseFocus()
{
    bFocusClosing=true;CloseAge=0.f;ClosePageAlpha=PageAlpha;CloseOpenAlpha=OpenAlpha;
    Arms->CaptureFocusReturn(bFocusDetached);
    CloseResetSeconds=0.f;
    CloseBookSeconds=bFocusDetached?SpellbookFocusMotion::Close:0.f;
    FocusReturnCamera=bFocusDetached?FocusBook->GetRelativeTransform()
        :Book->GetComponentTransform().GetRelativeTransform(Camera->GetComponentTransform());
}

FVector USpellbookComponent::FocusCatchOffset() const
{
    // Receiving is authored at the existing focus wrist. Do not reach toward
    // the floating book or chase its bob when closing.
    return FVector::ZeroVector;
}

void USpellbookComponent::CancelFocus()
{
    FocusAge=-1.f;bFocusDesired=bFocusClosing=bFocusDetached=bQueuedBookStrike=false;
    PageAlpha=OpenAlpha=PagePhase=0.f;
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
    if(!bFocusClosing)
    {
        const float PreviousAge=FocusAge;FocusAge+=Delta;
        OpenAlpha=FMath::Clamp((FocusAge-Motion::OpenStart)/Motion::OpenDuration,0.f,1.f);
        if(FocusAge>=Motion::Ready)
        {
            PagePhase=FMath::Fmod(PagePhase+FMath::Max(0.f,FocusAge-FMath::Max(PreviousAge,Motion::Ready)),Motion::PageCycle);
            PageAlpha=.5f-.5f*FMath::Cos(2.f*PI*PagePhase/Motion::PageCycle);
        }
        Arms->SetFocusPose(FMath::Min(FocusAge,Motion::Gather),1.f,false);
    }
    else
    {
        CloseAge+=Delta;
        PageAlpha=ClosePageAlpha;
        OpenAlpha=CloseOpenAlpha*(1.f-Motion::Ease(0.f,CloseBookSeconds,CloseAge));
        const float Duration=bFocusDetached?Motion::ReturnLength:Motion::HeldReturn;
        const float Return=FMath::Clamp(CloseAge/Duration,0.f,1.f);
        Arms->SetFocusReturn(Return);
        if(CloseAge>=Duration)
        {
            const bool Strike=bQueuedBookStrike,Reopen=bFocusDesired;
            CancelFocus();UpdateVisibility();
            if(Strike||Reopen){Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();}
            if(Strike)BeginQuickCombat();else if(Reopen)ToggleFocus();
        }
    }
}

void USpellbookComponent::PresentFocusBook()
{
    if(!IsFocusActive()||!FocusBook||!Camera.IsValid())return;
    namespace Motion=SpellbookFocusMotion;
    const FTransform Held=Book->GetComponentTransform().GetRelativeTransform(Camera->GetComponentTransform());
    if(!bFocusDetached)
    {
        if(bFocusClosing||FocusAge<Motion::Detach)return;
        bFocusDetached=true;DetachAge=FocusAge;FocusDepartCamera=Held;
    }
    FTransform Frame;
    if(bFocusClosing)
    {
        // Keep the palm at the focus wrist. Both halves close above the spine,
        // then the spine lands in the palm before the fingers and carry handoff.
        const FTransform Mount=SpellbookReturnContact::Mount(CloseAge);
        FTransform Hand=Arms->GetSocketTransform(TEXT("hand_l"),RTS_World);
        // The V7 bone carries the rig's scale-100 import. The mount is authored
        // in centimetres: strip scale before composing either
        // the contact offset or the book frame, matching the normal carry path.
        Hand.SetScale3D(FVector::OneVector);
        Hand=Hand.GetRelativeTransform(Camera->GetComponentTransform());
        Frame=Motion::ReturnBook(FocusReturnCamera,Mount*Hand,CloseAge);
    }
    else Frame=Motion::OpenBook(FocusDepartCamera,FocusAge,DetachAge);
    FocusBook->SetRelativeTransform(Frame);
    // During closure, freeze the page input. The root's hinge lift and local
    // front/page closure bring both halves together above the unchanged spine.
    // Normal reading keeps the original authored forward/back page track.
    const float SampleOpen=bFocusClosing?CloseOpenAlpha:OpenAlpha;
    const float SamplePage=bFocusClosing?ClosePageAlpha:PageAlpha;
    const bool Pages=SampleOpen>=1.f-UE_SMALL_NUMBER;
    auto* Clip=Pages?FlipClip.Get():OpenClip.Get();
    if(!FocusBook->GetSingleNodeInstance()||FocusBook->GetSingleNodeInstance()->GetCurrentAsset()!=Clip)
    {FocusBook->SetAnimation(Clip);FocusBook->SetPlayRate(0.f);}
    FocusBook->SetComponentSpaceTransformsDoubleBuffering(false);
    FocusBook->SetPosition((Pages?SamplePage:SampleOpen)*Clip->GetPlayLength(),false);
    FocusBook->TickAnimation(0.f,false);FocusBook->RefreshBoneTransforms();
    if(bFocusClosing)CloseCurrentPages(*FocusBook,Motion::Ease(0.f,CloseBookSeconds,CloseAge));
    if(FocusWorldBook)FocusWorldBook->SetWorldTransform(FocusBook->GetComponentTransform());
    PresentFocusGold();
}
