#include "SpellbookComponent.h"
#include "SpellbookAuthoredFocus.h"
#include "SpellbookAuthoredReturn.h"
#include "SpellbookFocusMotion.h"
#include "Engine/SkeletalMesh.h"

void USpellbookArmsMeshComponent::CacheFocusPose()
{
    CachePose();auto* Mesh=GetSkeletalMeshAsset();
    if(!Mesh||(!FocusKeys.IsEmpty()&&ReturnKeys.Num()==SpellbookAuthoredSpineDownReturn::KeyCount))return;
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
            FocusKeys[K][I].SetRotation(Key.Rotation.GetNormalized());
        }
    }
    ReturnKeys.SetNum(SpellbookAuthoredSpineDownReturn::KeyCount);
    for(int32 K=0;K<ReturnKeys.Num();++K)
    {
        ReturnKeys[K]=Ref.GetRefBonePose();
        for(int32 B=0;B<Grip::BoneCount;++B)if(const int32 I=LeftBones[B];I>=0)
        {
            const int32 Parent=Ref.GetParentIndex(I);
            const FVector Scale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
            const auto& Key=SpellbookAuthoredSpineDownReturn::Poses[K][B];
            ReturnKeys[K][I].SetLocation(FVector(Key.Position[0],Key.Position[1],Key.Position[2])/Scale);
            ReturnKeys[K][I].SetRotation(FQuat(Key.Rotation[0],Key.Rotation[1],Key.Rotation[2],Key.Rotation[3]).GetNormalized());
        }
    }
}

void USpellbookArmsMeshComponent::CaptureFocusEntry()
{
    CacheFocusPose();CaptureQuickCombatEntry(0);FocusEntry=StrikeEntry;
}

void USpellbookArmsMeshComponent::CaptureFocusReturn(bool Detached)
{
    CacheFocusPose();CaptureQuickCombatEntry(0);ReturnEntry=StrikeEntry;
    bReturnDetached=Detached;ReturnProgress=0.f;
}

void USpellbookArmsMeshComponent::ApplyFocusPose(TArray<FTransform>& LocalPose)
{
    if(FocusPoseTime<0.f||FocusPoseWeight<=0.f)return;
    CacheFocusPose();if(FocusKeys.IsEmpty())return;
    namespace Motion=SpellbookFocusMotion;
    if(bFocusReturning)
    {
        if(ReturnEntry.Num()!=LocalPose.Num())ReturnEntry=LocalPose;
        const float Sample=FMath::Clamp(ReturnProgress,0.f,1.f)*(ReturnKeys.Num()-1);
        const int32 A=FMath::Min(FMath::FloorToInt(Sample),ReturnKeys.Num()-2);
        const float Entry=1.f-Motion::Ease(0.f,Motion::DropStart/Motion::ReturnLength,ReturnProgress);
        const float Settle=Motion::IdleHandoff(ReturnProgress*Motion::ReturnLength);
        for(const int32 I:LeftBones)if(I>=0)
        {
            FTransform Target,Mixed;
            if(!bReturnDetached)
            {
                // An early toggle with the book still in hand only lowers the arm.
                Mixed.Blend(ReturnEntry[I],LocalPose[I],Motion::Ease(0.f,1.f,ReturnProgress));
                LocalPose[I]=Mixed;continue;
            }
            Target.Blend(ReturnKeys[A][I],ReturnKeys[A+1][I],Sample-A);
            const FQuat Delta=ReturnEntry[I].GetRotation()*ReturnKeys[0][I].GetRotation().Inverse();
            Target.SetRotation((FQuat::Slerp(FQuat::Identity,Delta,Entry)*Target.GetRotation()).GetNormalized());
            Target.AddToTranslation((ReturnEntry[I].GetLocation()-ReturnKeys[0][I].GetLocation())*Entry);
            Mixed.Blend(Target,LocalPose[I],Settle);LocalPose[I]=Mixed;
        }
        return;
    }
    namespace Focus=SpellbookAuthoredFocus;
    if(FocusEntry.Num()!=LocalPose.Num())FocusEntry=LocalPose;
    int32 A=0;while(A<Focus::KeyCount-2&&FocusPoseTime>=Focus::Times[A+1])++A;
    const float T=FMath::Clamp((FocusPoseTime-Focus::Times[A])/(Focus::Times[A+1]-Focus::Times[A]),0.f,1.f);
    const float Entry=1.f-FMath::SmoothStep(0.f,Motion::Detach,FocusPoseTime);
    for(const int32 I:LeftBones)if(I>=0)
    {
        FTransform Target,Mixed;Target.Blend(FocusKeys[A][I],FocusKeys[A+1][I],T);
        const FQuat Delta=FocusEntry[I].GetRotation()*FocusKeys[0][I].GetRotation().Inverse();
        Target.SetRotation((FQuat::Slerp(FQuat::Identity,Delta,Entry)*Target.GetRotation()).GetNormalized());
        Target.AddToTranslation((FocusEntry[I].GetLocation()-FocusKeys[0][I].GetLocation())*Entry);
        Mixed.Blend(LocalPose[I],Target,FocusPoseWeight);LocalPose[I]=Mixed;
    }
}
