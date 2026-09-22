#include "WitchRebuiltMonster.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

bool AWitchRebuiltMonster::PrepareRebuiltPhysics(USkeletalMesh* SourceMesh, bool bApply)
{
#if WITH_EDITOR
    if (!SourceMesh || !SourceMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/WitchRebuilt/"))) return false;
    auto* Asset = SourceMesh->GetPhysicsAsset();
    if (!Asset || !Asset->GetPathName().StartsWith(TEXT("/Game/Monsters/WitchRebuilt/"))) return false;
    const auto& Ref = SourceMesh->GetRefSkeleton();
    TArray<FTransform> Frames = Ref.GetRefBonePose();
    for (int32 I = 0; I < Frames.Num(); ++I)
        if (Ref.GetParentIndex(I) >= 0) Frames[I] *= Frames[Ref.GetParentIndex(I)];
    FString Report = FString::Printf(TEXT("Before apply=%d bodies=%d constraints=%d\n"),
        bApply, Asset->SkeletalBodySetups.Num(), Asset->ConstraintSetup.Num());
    for (const UPhysicsConstraintTemplate* Joint : Asset->ConstraintSetup)
    {
        if (!Joint) continue;
        const auto& C = Joint->DefaultInstance;
        const int32 A = Ref.FindBoneIndex(C.ConstraintBone1), B = Ref.FindBoneIndex(C.ConstraintBone2);
        const double Error = A >= 0 && B >= 0 ? FVector::Distance(
            Frames[A].TransformPosition(C.GetRefFrame(EConstraintFrame::Frame1).GetLocation()),
            Frames[B].TransformPosition(C.GetRefFrame(EConstraintFrame::Frame2).GetLocation())) : -1.;
        Report += FString::Printf(TEXT("joint=%s child=%s parent=%s reference_gap_cm=%.6f\n"),
            *C.JointName.ToString(), *C.ConstraintBone1.ToString(), *C.ConstraintBone2.ToString(), Error);
    }
    FFileHelper::SaveStringToFile(Report, *(FPaths::ProjectSavedDir()/TEXT("WitchRebuilt-physics-refinement.txt")),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    if (!bApply) return true;

    struct FBodySpec { const TCHAR* Bone; const TCHAR* End; float Radius; float Mass; };
    const FBodySpec Specs[] = {
        {TEXT("pelvis"),TEXT("spine_02"),10.f,11.f},
        {TEXT("spine_02"),TEXT("spine_05"),10.f,10.f},
        {TEXT("spine_05"),TEXT("neck_01"),11.f,9.f},
        {TEXT("head"),TEXT("head"),8.f,5.f},
        {TEXT("upperarm_l"),TEXT("lowerarm_l"),4.6f,2.5f}, {TEXT("upperarm_r"),TEXT("lowerarm_r"),4.6f,2.5f},
        {TEXT("lowerarm_l"),TEXT("hand_l"),3.8f,1.4f}, {TEXT("lowerarm_r"),TEXT("hand_r"),3.8f,1.4f},
        {TEXT("hand_l"),TEXT("middle_01_l"),2.8f,.6f}, {TEXT("hand_r"),TEXT("middle_01_r"),2.8f,.6f},
        {TEXT("thigh_l"),TEXT("calf_l"),8.5f,6.f}, {TEXT("thigh_r"),TEXT("calf_r"),8.5f,6.f},
        {TEXT("calf_l"),TEXT("foot_l"),5.5f,3.f}, {TEXT("calf_r"),TEXT("foot_r"),5.5f,3.f},
        {TEXT("foot_l"),TEXT("ball_l"),4.f,1.f}, {TEXT("foot_r"),TEXT("ball_r"),4.f,1.f}
    };
    for (const auto& S : Specs)
        if (Ref.FindBoneIndex(S.Bone) < 0 || Ref.FindBoneIndex(S.End) < 0) return false;
    Asset->Modify(); Asset->SkeletalBodySetups.Reset(); Asset->ConstraintSetup.Reset(); Asset->CollisionDisableTable.Reset();
    for (const auto& S : Specs)
    {
        const auto& Frame = Frames[Ref.FindBoneIndex(S.Bone)];
        FVector Start = Frame.GetLocation(), End = Frames[Ref.FindBoneIndex(S.End)].GetLocation();
        if (Start.Equals(End)) End += FVector(0,0,12.f);
        const float Scale = Frame.GetScale3D().GetAbsMax();
        auto* Body = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
        Body->BoneName = S.Bone; Body->PhysicsType = PhysType_Default;
        FKSphylElem Shape;
        Shape.Center = Frame.InverseTransformPosition((Start+End)*.5);
        Shape.Rotation = FRotationMatrix::MakeFromZ(Frame.InverseTransformVectorNoScale(End-Start)).Rotator();
        Shape.Radius = S.Radius/Scale;
        Shape.Length = FMath::Max(0., FVector::Distance(Start,End)-S.Radius*1.2)/Scale;
        Body->AggGeom.SphylElems.Add(Shape); Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        auto& Instance = Body->DefaultInstance;
        Instance.SetCollisionProfileName(TEXT("Ragdoll")); Instance.SetMassOverride(S.Mass);
        Instance.LinearDamping = .8f; Instance.AngularDamping = 2.5f;
        Instance.bUseCCD = true; Instance.PositionSolverIterationCount = 16; Instance.VelocitySolverIterationCount = 8;
        Body->InvalidatePhysicsData(); Body->CreatePhysicsMeshes(); Asset->SkeletalBodySetups.Add(Body);
    }
    Asset->UpdateBodySetupIndexMap();
    double MaxAnchorError = 0.;
    for (int32 I = 0; I < Asset->SkeletalBodySetups.Num(); ++I)
    {
        const FName Name = Asset->SkeletalBodySetups[I]->BoneName;
        const int32 Bone = Ref.FindBoneIndex(Name); int32 Parent = Ref.GetParentIndex(Bone);
        while (Parent >= 0 && Asset->FindBodyIndex(Ref.GetBoneName(Parent)) == INDEX_NONE) Parent = Ref.GetParentIndex(Parent);
        if (Parent < 0) continue;
        auto* Joint = NewObject<UPhysicsConstraintTemplate>(Asset, NAME_None, RF_Transactional);
        auto& C = Joint->DefaultInstance;
        C.JointName = Name; C.ConstraintBone1 = Name; C.ConstraintBone2 = Ref.GetBoneName(Parent);
        const FTransform Anchor(Frames[Bone].GetRotation(), Frames[Bone].GetLocation());
        C.SetRefFrame(EConstraintFrame::Frame1, Anchor.GetRelativeTransform(Frames[Bone]));
        C.SetRefFrame(EConstraintFrame::Frame2, Anchor.GetRelativeTransform(Frames[Parent]));
        C.SetLinearXLimit(LCM_Locked,0); C.SetLinearYLimit(LCM_Locked,0); C.SetLinearZLimit(LCM_Locked,0);
        FVector Limits(20,20,15); const FString N = Name.ToString();
        if (N.StartsWith(TEXT("thigh"))) Limits = FVector(45,35,25);
        else if (N.StartsWith(TEXT("calf"))) Limits = FVector(65,8,8);
        else if (N.StartsWith(TEXT("upperarm"))) Limits = FVector(65,55,40);
        else if (N.StartsWith(TEXT("lowerarm"))) Limits = FVector(65,12,15);
        else if (N.StartsWith(TEXT("hand")) || N.StartsWith(TEXT("foot"))) Limits = FVector(25,20,15);
        C.SetAngularSwing1Limit(ACM_Limited,Limits.X); C.SetAngularSwing2Limit(ACM_Limited,Limits.Y); C.SetAngularTwistLimit(ACM_Limited,Limits.Z);
        C.SetLinearBreakable(false,0); C.SetAngularBreakable(false,0); C.SetDisableCollision(true);
        C.ProfileInstance.bEnableProjection = true;
        C.ProfileInstance.ProjectionLinearTolerance = 2.f; C.ProfileInstance.ProjectionAngularTolerance = 10.f;
        Asset->ConstraintSetup.Add(Joint); Asset->DisableCollision(I,Asset->FindBodyIndex(C.ConstraintBone2));
        const FVector A = Frames[Bone].TransformPosition(C.GetRefFrame(EConstraintFrame::Frame1).GetLocation());
        const FVector B = Frames[Parent].TransformPosition(C.GetRefFrame(EConstraintFrame::Frame2).GetLocation());
        MaxAnchorError = FMath::Max(MaxAnchorError,FVector::Distance(A,B));
    }
    // Neighbouring torso/hip volumes overlap by design. Suppress only those
    // pairs already overlapping at rest; keep separated limb contacts enabled.
    for (int32 I=0; I<Asset->SkeletalBodySetups.Num(); ++I) for (int32 J=I+1; J<Asset->SkeletalBodySetups.Num(); ++J)
    {
        const USkeletalBodySetup* A=Asset->SkeletalBodySetups[I]; const USkeletalBodySetup* B=Asset->SkeletalBodySetups[J];
        const auto& TA=Frames[Ref.FindBoneIndex(A->BoneName)]; const auto& TB=Frames[Ref.FindBoneIndex(B->BoneName)];
        const auto& CA=A->AggGeom.SphylElems[0]; const auto& CB=B->AggGeom.SphylElems[0];
        const double SA=TA.GetScale3D().GetAbsMax(), SB=TB.GetScale3D().GetAbsMax();
        const FVector PA=TA.TransformPosition(CA.Center), PB=TB.TransformPosition(CB.Center);
        const FVector DA=TA.TransformVectorNoScale(CA.Rotation.Quaternion().GetAxisZ())*CA.Length*SA*.5;
        const FVector DB=TB.TransformVectorNoScale(CB.Rotation.Quaternion().GetAxisZ())*CB.Length*SB*.5;
        FVector NA,NB; FMath::SegmentDistToSegmentSafe(PA-DA,PA+DA,PB-DB,PB+DB,NA,NB);
        if (FVector::DistSquared(NA,NB)<FMath::Square(CA.Radius*SA+CB.Radius*SB)) Asset->DisableCollision(I,J);
    }
    Asset->UpdateBoundsBodiesArray(); Asset->SetPreviewMesh(SourceMesh,false); Asset->MarkPackageDirty();
    const FString Result=FString::Printf(TEXT("After bodies=%d constraints=%d max_reference_gap_cm=%.9f\n"),
        Asset->SkeletalBodySetups.Num(),Asset->ConstraintSetup.Num(),MaxAnchorError);
    FFileHelper::SaveStringToFile(Result,*(FPaths::ProjectSavedDir()/TEXT("WitchRebuilt-physics-refinement.txt")),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append);
    UE_LOG(LogTemp,Display,TEXT("WITCH_REBUILT_PHYSICS %s"),*Result);
    return Asset->ConstraintSetup.Num()==Asset->SkeletalBodySetups.Num()-1;
#else
    return false;
#endif
}
