#include "SpellbookComponent.h"
#include "SpellbookAuthoredFocus.h"
#include "SpellbookFocusMotion.h"
#include "SpellbookFocusInterruptMotion.h"
#include "Engine/SkeletalMesh.h"

void USpellbookArmsMeshComponent::CacheFocusPose()
{
    CachePose();auto* Mesh=GetSkeletalMeshAsset();
    if(!Mesh||FocusKeys.Num()==SpellbookAuthoredFocus::KeyCount)return;
    const auto& Ref=Mesh->GetRefSkeleton();namespace Grip=SpellbookAuthoredGrip;
    FocusKeys.SetNum(SpellbookAuthoredFocus::KeyCount);
    for(int32 K=0;K<FocusKeys.Num();++K)
    {
        FocusKeys[K]=Ref.GetRefBonePose();
        for(int32 B=0;B<Grip::BoneCount;++B)if(const int32 I=LeftBones[B];I>=0)
        {
            const int32 Parent=Ref.GetParentIndex(I);
            const FVector Scale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
            const auto& Key=SpellbookAuthoredFocus::Poses[K][B];
            FocusKeys[K][I].SetLocation(FVector(Key.Position[0],Key.Position[1],Key.Position[2])/Scale);
            FocusKeys[K][I].SetRotation(FQuat(Key.Rotation[0],Key.Rotation[1],Key.Rotation[2],Key.Rotation[3]).GetNormalized());
        }
    }
}

void USpellbookArmsMeshComponent::CaptureFocusEntry()
{
    CacheFocusPose();CaptureQuickCombatEntry(0);FocusEntry=StrikeEntry;
}

void USpellbookArmsMeshComponent::ApplyFocusPose(TArray<FTransform>& LocalPose)
{
    if(const auto* Book=GetOwner()?GetOwner()->FindComponentByClass<USpellbookComponent>():nullptr;
        Book&&Book->IsFocusInterrupted()&&Book->FocusInterruptAge()<SpellbookFocusInterruptMotion::Catch)
    {ApplyFocusInterruptPose(LocalPose,*Book);return;}
    if(FocusPoseTime<0.f||FocusPoseWeight<=0.f)return;
    CacheFocusPose();if(FocusKeys.IsEmpty())return;
    namespace Motion=SpellbookFocusMotion;
    namespace Focus=SpellbookAuthoredFocus;
    if(FocusEntry.Num()!=LocalPose.Num())FocusEntry=LocalPose;
    int32 A=0;while(A<Focus::KeyCount-2&&FocusPoseTime>=Focus::Times[A+1])++A;
    const float T=FMath::Clamp((FocusPoseTime-Focus::Times[A])/(Focus::Times[A+1]-Focus::Times[A]),0.f,1.f);
    const float Entry=1.f-FMath::SmoothStep(0.f,Motion::Detach,FocusPoseTime);
    const auto* Spellbook=bFocusReturning&&GetOwner()?GetOwner()->FindComponentByClass<USpellbookComponent>():nullptr;
    const float Recovery=Spellbook?Spellbook->FocusRecoveryBlend():0.f;
    const int32 InterruptThumb=Spellbook&&Spellbook->IsFocusInterrupted()?GetBoneIndex(TEXT("thumb_01_l")):INDEX_NONE;
    for(int32 B=0;B<LeftBones.Num();++B)if(const int32 I=LeftBones[B];I>=0)
    {
        FTransform Target,Mixed;Target.Blend(FocusKeys[A][I],FocusKeys[A+1][I],T);
        if(Recovery>0.f&&Focus::FingerBone[B])
        {
            const auto& First=Focus::ReturnRotations[A][B];
            const auto& Second=Focus::ReturnRotations[A+1][B];
            const FQuat Return=FQuat::Slerp(FQuat(First[0],First[1],First[2],First[3]),
                FQuat(Second[0],Second[1],Second[2],Second[3]),T).GetNormalized();
            Target.SetRotation(FQuat::Slerp(Target.GetRotation(),Return,Recovery).GetNormalized());
        }
        if(I==InterruptThumb)
        {
            // Match the cleared thumb exactly at catch, then ease back onto
            // the accepted closed grip; no thumb snap at the recovery handoff.
            namespace Hit=SpellbookFocusInterruptMotion;
            Target.SetRotation(Hit::ClearThumb(Target.GetRotation(),Motion::Ease(Hit::ThumbClearanceEndSource,Hit::CatchSource,FocusPoseTime)));
        }
        const FQuat Delta=FocusEntry[I].GetRotation()*FocusKeys[0][I].GetRotation().Inverse();
        Target.SetRotation((FQuat::Slerp(FQuat::Identity,Delta,Entry)*Target.GetRotation()).GetNormalized());
        Target.AddToTranslation((FocusEntry[I].GetLocation()-FocusKeys[0][I].GetLocation())*Entry);
        if(bFocusReturning)
        {
            FTransform Settled;Settled.Blend(Target,LocalPose[I],1.f-Motion::Ease(0.f,.12f,FocusPoseTime));
            Target=Settled;
        }
        Mixed.Blend(LocalPose[I],Target,FocusPoseWeight);LocalPose[I]=Mixed;
    }
}
