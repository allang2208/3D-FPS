#include "SpellbookComponent.h"
#include "SpellbookAuthoredFocus.h"
#include "SpellbookBookOrientation.h"
#include "SpellbookFocusInterruptMotion.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void USpellbookArmsMeshComponent::CaptureFocusInterrupt()
{
    CacheFocusPose();CaptureQuickCombatEntry(0);InterruptEntry=StrikeEntry;
}

void USpellbookArmsMeshComponent::ApplyFocusInterruptPose(TArray<FTransform>& LocalPose,const USpellbookComponent& BookState)
{
    CacheFocusPose();if(FocusKeys.IsEmpty()||InterruptEntry.Num()!=LocalPose.Num())return;
    namespace Hit=SpellbookFocusInterruptMotion;
    namespace Focus=SpellbookAuthoredFocus;
    using SpellbookFocusMotion::Ease;
    const float Age=BookState.FocusInterruptAge();
    const float Source=BookState.FocusInterruptContactSource();
    const int32 ThumbRoot=GetBoneIndex(TEXT("thumb_01_l"));
    int32 A=0;while(A<Focus::KeyCount-2&&Source>=Focus::Times[A+1])++A;
    const float Sample=FMath::Clamp((Source-Focus::Times[A])/(Focus::Times[A+1]-Focus::Times[A]),0.f,1.f);
    for(int32 B=0;B<LeftBones.Num();++B)if(const int32 I=LeftBones[B];I>=0)
    {
        FTransform CatchPose,Reaction;
        CatchPose.Blend(FocusKeys[A][I],FocusKeys[A+1][I],Sample);
        if(Focus::FingerBone[B])
        {
            const auto& First=Focus::ReturnRotations[A][B];const auto& Second=Focus::ReturnRotations[A+1][B];
            CatchPose.SetRotation(FQuat::Slerp(FQuat(First[0],First[1],First[2],First[3]),
                FQuat(Second[0],Second[1],Second[2],Second[3]),Sample).GetNormalized());
        }
        if(I==ThumbRoot)CatchPose.SetRotation(Hit::ClearThumb(CatchPose.GetRotation(),1.f));
        // Clear the thumb first while the arm stays below the reading pages.
        // The book moves away before the hand rises to the receiving pose.
        const float CatchWeight=Focus::FingerBone[B]?(I==ThumbRoot?Ease(0.f,.12f,Age):Ease(.02f,.16f,Age))
            :Ease(Hit::HandApproachStart,Hit::DropStart,Age);
        Reaction.Blend(InterruptEntry[I],CatchPose,CatchWeight);
        LocalPose[I]=Reaction;
    }
}

void USpellbookComponent::BeginFocusInterruptPresentation()
{
    if(FocusAge<0.f||bFocusInterrupted)return;
    // A server hit may arrive after the owner has started closing this same book.
    const float EntryTime=bFocusClosing?FMath::Max(0.f,ReturnStartTime-CloseAge):
        FMath::Min(FocusAge,SpellbookFocusMotion::OpenLength);
    // Change the state before publishing the resource loss: another accepted
    // hit or an equipment callback cannot charge this focus session twice.
    bFocusInterrupted=true;bFocusDesired=false;bFocusClosing=false;InterruptAge=0.f;
    InterruptOpenAlpha=OpenAlpha;InterruptGoldFade=GoldFade;
    namespace Hit=SpellbookFocusInterruptMotion;
    InterruptContactSource=bFocusDetached?Hit::CatchSource:SpellbookFocusMotion::SourceTime(EntryTime);
    ReturnStartTime=bFocusDetached?Hit::NormalReturnStart(Hit::CatchSource):EntryTime;
    ClosePageAlpha=PageAlpha;
    if(Arms)Arms->CaptureFocusInterrupt();
    InterruptBookEntry.Reset();InterruptBookClosed.Reset();
    if(bFocusDetached&&FocusBook&&OpenClip&&FlipClip)
    {
        InterruptBookFrame=FocusBook->GetRelativeTransform();
        const auto Current=FocusBook->GetBoneSpaceTransformsView();
        InterruptBookEntry=TArray<FTransform>(Current.GetData(),Current.Num());
        FocusBook->SetAnimation(OpenClip);FocusBook->SetPlayRate(0.f);
        FocusBook->SetComponentSpaceTransformsDoubleBuffering(false);
        FocusBook->SetPosition(SpellbookFocusMotion::Detach,false);
        FocusBook->TickAnimation(0.f,false);FocusBook->RefreshBoneTransforms();
        const auto Closed=FocusBook->GetBoneSpaceTransformsView();
        InterruptBookClosed=TArray<FTransform>(Closed.GetData(),Closed.Num());
        // Restore the captured pose immediately after sampling the catch pose.
        PresentFocusInterruptBook();
    }
    else
    {
        // A book that has not left the hand cannot fall; resume its normal
        // return from the current source time without inventing a release.
        InterruptAge=Hit::Catch;
        if(Arms)Arms->SetFocusReturn(InterruptContactSource);
    }
}

void USpellbookComponent::AdvanceFocusInterrupt(float Delta)
{
    namespace Hit=SpellbookFocusInterruptMotion;
    InterruptAge+=Delta;
    OpenAlpha=FMath::Lerp(InterruptOpenAlpha,1.f,SpellbookFocusMotion::Ease(0.f,.08f,InterruptAge))
        *(1.f-SpellbookFocusMotion::Ease(Hit::CollapseStart,Hit::CollapseEnd,InterruptAge));
    if(InterruptAge>=Hit::Catch)
    {
        bFocusDetached=false;
        const float Remaining=ReturnStartTime-(InterruptAge-Hit::Catch);
        Arms->SetFocusReturn(SpellbookFocusMotion::SourceTime(Remaining));
        if(Remaining<=0.f){CancelFocus();UpdateVisibility();}
    }
}

void USpellbookComponent::PresentFocusInterruptBook()
{
    if(!bFocusDetached||!Arms||!FocusBook||!Camera.IsValid())return;
    namespace Hit=SpellbookFocusInterruptMotion;
    using SpellbookFocusMotion::Ease;
    const float Age=InterruptAge;
    FTransform Hand=Arms->GetSocketTransform(TEXT("hand_l"),RTS_World);Hand.SetScale3D(FVector::OneVector);
    const FTransform CatchFrame=(SpellbookBookOrientation::InHand()*Hand).GetRelativeTransform(Camera->GetComponentTransform());
    FTransform AbovePalm=CatchFrame;AbovePalm.AddToTranslation(FVector(0,0,Hit::DropHeight));
    FTransform Frame;
    if(Age<Hit::DropStart)Frame.Blend(InterruptBookFrame,AbovePalm,Ease(Hit::BookClearanceStart,Hit::DropStart,Age));
    else
    {
        // Fully closed and aligned before falling. Only vertical translation
        // remains; it reaches the exact rigid hand attachment at contact.
        const float Fall=FMath::Clamp((Age-Hit::DropStart)/(Hit::Catch-Hit::DropStart),0.f,1.f);
        Frame=CatchFrame;Frame.AddToTranslation(FVector(0,0,Hit::DropHeight*(1.f-Fall*Fall)));
    }
    FocusBook->SetRelativeTransform(Frame);

    // Traverse real authored leaf turns, not a noisy interpolation toward closed.
    // Pick the farther end so even a hit near a cycle endpoint turns several pages.
    const float End=ClosePageAlpha<.5f?1.f:0.f;
    const float Page=FMath::Lerp(ClosePageAlpha,End,Ease(0.f,Hit::RapidEnd,Age));
    if(!FocusBook->GetSingleNodeInstance()||FocusBook->GetSingleNodeInstance()->GetCurrentAsset()!=FlipClip)
    {FocusBook->SetAnimation(FlipClip);FocusBook->SetPlayRate(0.f);}
    FocusBook->SetPosition(Page*FlipClip->GetPlayLength(),false);
    FocusBook->TickAnimation(0.f,false);FocusBook->RefreshBoneTransforms();
    const auto* Mesh=FocusBook->GetSkeletalMeshAsset();if(!Mesh)return;
    const auto Flipping=FocusBook->GetBoneSpaceTransformsView();
    const auto& Ref=Mesh->GetRefSkeleton();auto& Pose=FocusBook->GetEditableComponentSpaceTransforms();
    if(Pose.Num()!=InterruptBookEntry.Num()||Pose.Num()!=InterruptBookClosed.Num())return;
    for(int32 I=0;I<Pose.Num();++I)
    {
        FTransform Reading;Reading.Blend(InterruptBookEntry[I],Flipping[I],Ease(0.f,.08f,Age));
        Pose[I].Blend(Reading,InterruptBookClosed[I],Ease(Hit::CollapseStart,Hit::CollapseEnd,Age));
        if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
    }
    FocusBook->MarkRenderDynamicDataDirty();
    if(FocusWorldBook)FocusWorldBook->SetWorldTransform(FocusBook->GetComponentTransform());
    PresentFocusGold();
}
