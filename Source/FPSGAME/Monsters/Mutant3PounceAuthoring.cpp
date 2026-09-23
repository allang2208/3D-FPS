#include "Mutant3.h"
#include "Animation/AnimSequence.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#endif

bool AMutant3::ApplyPounceHandTracks(UAnimSequence* Target, UAnimSequence* Authored)
{
#if WITH_EDITOR
    // Copy only hand rotations into the accepted clips: no FBX roundtrip of
    // shoulders, elbows, body, root, foot grounding, timing or animation curves.
    if (!Target || !Authored || Target == Authored || Target->GetSkeleton() != Authored->GetSkeleton()) return false;
    const FString Path = Target->GetPathName();
    const FString Folder = TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/");
    if (Path != Folder+TEXT("A_Mutant3_PounceFlight.A_Mutant3_PounceFlight") &&
        Path != Folder+TEXT("A_Mutant3_PounceLand.A_Mutant3_PounceLand")) return false;
    const auto* Existing = Target->GetDataModel();
    const auto* Source = Authored->GetDataModel();
    if (!Existing || !Source || Existing->GetFrameRate() != Source->GetFrameRate() ||
        Existing->GetNumberOfKeys() != Source->GetNumberOfKeys()) return false;
    TArray<FName> Names;
    for (const TCHAR* Side : {TEXT("Left"), TEXT("Right")})
    {
        Names.Add(FName(*(FString(Side)+TEXT("Hand"))));
        for (const TCHAR* Digit : {TEXT("Index"), TEXT("Middle"), TEXT("Ring"), TEXT("Pinky"), TEXT("Thumb")})
            for (int32 Joint=1; Joint<=3; ++Joint)
                Names.Add(FName(*FString::Printf(TEXT("%s%s%d_Claw"), Side, Digit, Joint)));
    }
    TMap<FName, TArray<FTransform>> OldTracks, NewTracks;
    for (const FName Name : Names)
    {
        if (!Existing->IsValidBoneTrackName(Name) || !Source->IsValidBoneTrackName(Name)) return false;
        Existing->GetBoneTrackTransforms(Name, OldTracks.Add(Name));
        Source->GetBoneTrackTransforms(Name, NewTracks.Add(Name));
        if (OldTracks[Name].Num() != NewTracks[Name].Num() || OldTracks[Name].IsEmpty()) return false;
    }
    auto& Controller = Target->GetController();
    Controller.OpenBracket(FText::FromString(TEXT("Mutant3 pounce downward wrists and claws")), false);
    bool Applied = true;
    for (const FName Name : Names)
    {
        TArray<FVector> Positions, Scales;
        TArray<FQuat> Rotations;
        const auto& Old = OldTracks[Name];
        const auto& New = NewTracks[Name];
        for (int32 Frame=0; Frame<Old.Num(); ++Frame)
        {
            Positions.Add(Old[Frame].GetTranslation());
            Scales.Add(Old[Frame].GetScale3D());
            Rotations.Add(New[Frame].GetRotation().GetNormalized());
        }
        Applied &= Controller.SetBoneTrackKeys(Name, Positions, Rotations, Scales, false);
    }
    Controller.CloseBracket(false);
    if (Applied) Target->MarkPackageDirty();
    return Applied;
#else
    return false;
#endif
}
