#include "FatZombie.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#endif

bool AFatZombie::AuthorStaggerAnimation(UAnimSequence* Clip)
{
#if WITH_EDITOR
    if (!Clip || Clip->GetPathName() != TEXT("/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_Stagger.A_FatZombie_Stagger") || !Clip->GetSkeleton()) return false;
    const auto* Model = Clip->GetDataModel();
    TArray<FName> Names;
    Model->GetBoneTrackNames(Names);
    TMap<FName, FTransform> Rest;
    for (FName Name : Names)
    {
        TArray<FTransform> Keys;
        Model->GetBoneTrackTransforms(Name, Keys);
        if (!Keys.IsEmpty()) Rest.Add(Name, Keys[0]);
    }
    const auto& Skeleton = Clip->GetSkeleton()->GetReferenceSkeleton();
    TArray<FTransform> ComponentPose;
    for (int32 Index = 0; Index < Skeleton.GetNum(); ++Index)
    {
        const FTransform* Key = Rest.Find(Skeleton.GetBoneName(Index));
        const FTransform Local = Key ? *Key : Skeleton.GetRefBonePose()[Index];
        const int32 Parent = Skeleton.GetParentIndex(Index);
        ComponentPose.Add(Parent >= 0 ? Local * ComponentPose[Parent] : Local);
    }
    const int32 Head = Skeleton.FindBoneIndex(TEXT("Head"));
    const int32 Front = Skeleton.FindBoneIndex(TEXT("headfront"));
    if (Head == INDEX_NONE || Front == INDEX_NONE || Rest.IsEmpty()) return false;
    const FVector Forward = (ComponentPose[Front].GetLocation() - ComponentPose[Head].GetLocation()).GetSafeNormal2D();
    const FVector RecoilAxis = FVector::CrossProduct(FVector::UpVector, -Forward).GetSafeNormal();
    // Preserve the accepted idle's legs, feet and root. The torso recoils and
    // both elbows fold visibly into a braced stagger, independent of the scratch.
    const TMap<FName, float> Angles = {
        {TEXT("Spine02"), 10.f}, {TEXT("Spine01"), 8.f}, {TEXT("Spine"), 6.f},
        {TEXT("neck"), -4.f}, {TEXT("LeftArm"), 16.f}, {TEXT("RightArm"), 16.f},
        {TEXT("LeftForeArm"), 28.f}, {TEXT("RightForeArm"), 28.f}
    };
    auto& Controller = Clip->GetController();
    Controller.OpenBracket(FText::FromString(TEXT("Author fat zombie stagger from accepted idle")), false);
    Controller.SetFrameRate(FFrameRate(120, 1), false);
    Controller.SetNumberOfFrames(FFrameNumber(108), false);
    for (const auto& Pair : Rest)
    {
        const int32 Index = Skeleton.FindBoneIndex(Pair.Key);
        const FVector LocalAxis = ComponentPose[Index].GetRotation().Inverse().RotateVector(RecoilAxis);
        TArray<FVector> Positions, Scales;
        TArray<FQuat> Rotations;
        for (int32 Frame = 0; Frame <= 108; ++Frame)
        {
            const float Time = Frame / 120.f;
            const float Strength = Time < .1f ? FMath::SmoothStep(0.f, .1f, Time) : 1.f - FMath::SmoothStep(.6f, .9f, Time);
            FTransform Key = Pair.Value;
            Key.SetRotation((Key.GetRotation() * FQuat(LocalAxis, FMath::DegreesToRadians(Angles.FindRef(Pair.Key) * Strength))).GetNormalized());
            Positions.Add(Key.GetTranslation()); Scales.Add(Key.GetScale3D()); Rotations.Add(Key.GetRotation());
        }
        Controller.SetBoneTrackKeys(Pair.Key, Positions, Rotations, Scales, false);
    }
    Controller.CloseBracket(false);
    Clip->bEnableRootMotion = false;
    Clip->RateScale = 1.f;
    Clip->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
