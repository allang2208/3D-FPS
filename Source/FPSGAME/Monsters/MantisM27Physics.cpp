#include "MantisM27Monster.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"

bool AMantisM27Monster::PreparePhysics(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
    if (!InMesh || !InMesh->GetPhysicsAsset() || !InMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/MantisM27/"))) return false;
    UPhysicsAsset* Asset=InMesh->GetPhysicsAsset(); const auto& Ref=InMesh->GetRefSkeleton();
    TArray<FTransform> Frames=Ref.GetRefBonePose();
    for (int32 I=0;I<Frames.Num();++I) if (Ref.GetParentIndex(I)>=0) Frames[I]*=Frames[Ref.GetParentIndex(I)];
    struct FBodySpec { FName Bone, End; float Radius, Mass; };
    const TArray<FBodySpec> Specs={
        {TEXT("root"),TEXT("root"),1,1},{TEXT("pelvis"),TEXT("spine_01"),12,9},
        {TEXT("spine_01"),TEXT("spine_02"),14,8},{TEXT("spine_02"),TEXT("neck_01"),16,10},
        {TEXT("head"),TEXT("head_tip"),8,4},
        {TEXT("upperarm_l"),TEXT("lowerarm_l"),5,3},{TEXT("upperarm_r"),TEXT("lowerarm_r"),5,3},
        {TEXT("lowerarm_l"),TEXT("blade_mid_l"),5,4},{TEXT("lowerarm_r"),TEXT("blade_mid_r"),5,4},
        {TEXT("thigh_l"),TEXT("calf_l"),7,6},{TEXT("thigh_r"),TEXT("calf_r"),7,6},
        {TEXT("calf_l"),TEXT("foot_l"),5,3},{TEXT("calf_r"),TEXT("foot_r"),5,3},
        {TEXT("foot_l"),TEXT("ball_l"),6,1.5f},{TEXT("foot_r"),TEXT("ball_r"),6,1.5f}};
    for (const auto& Spec:Specs) if (Ref.FindBoneIndex(Spec.Bone)==INDEX_NONE || Ref.FindBoneIndex(Spec.End)==INDEX_NONE) return false;
    // Blade markers carry no skin weights. Keep their chains evaluating at every
    // LOD so GetSocketLocation follows the attack instead of a culled bone pose.
    InMesh->Modify();
    auto& Sockets=InMesh->GetMeshOnlySocketList();
    for (const TCHAR* Side:{TEXT("l"),TEXT("r")}) for (const TCHAR* Part:{TEXT("root"),TEXT("mid"),TEXT("tip")})
    {
        const FName Name(*FString::Printf(TEXT("blade_%s_%s"),Part,Side));
        if (Ref.FindBoneIndex(Name)==INDEX_NONE) return false;
        USkeletalMeshSocket* Socket=nullptr;
        for (USkeletalMeshSocket* Existing:Sockets) if (Existing && Existing->SocketName==Name) { Socket=Existing; break; }
        if (!Socket) { Socket=NewObject<USkeletalMeshSocket>(InMesh,NAME_None,RF_Transactional); Sockets.Add(Socket); }
        Socket->SocketName=Name; Socket->BoneName=Name; Socket->bForceAlwaysAnimated=true;
    }
    Asset->Modify(); Asset->SkeletalBodySetups.Reset(); Asset->ConstraintSetup.Reset(); Asset->CollisionDisableTable.Reset();
    for (const auto& Spec:Specs)
    {
        auto* Body=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional); Body->BoneName=Spec.Bone;
        const FTransform& Frame=Frames[Ref.FindBoneIndex(Spec.Bone)];
        auto Capsule=[&](FName A,FName B,float Radius)
        {
            const FVector From=Frame.InverseTransformPosition(Frames[Ref.FindBoneIndex(A)].GetLocation());
            const FVector To=Frame.InverseTransformPosition(Frames[Ref.FindBoneIndex(B)].GetLocation());
            FKSphylElem Shape; Shape.Center=(From+To)*.5f; Shape.Radius=Radius;
            Shape.Length=FMath::Max(.1f,(To-From).Size()-Radius);
            Shape.Rotation=FQuat::FindBetweenNormals(FVector::UpVector,(To-From).GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector)).Rotator();
            Body->AggGeom.SphylElems.Add(Shape);
        };
        if (Spec.Bone==TEXT("root")) { FKSphereElem Sphere; Sphere.Radius=1.f; Body->AggGeom.SphereElems.Add(Sphere); }
        else Capsule(Spec.Bone,Spec.End,Spec.Radius);
        if (Spec.Bone==TEXT("lowerarm_l")) Capsule(TEXT("blade_mid_l"),TEXT("blade_tip_l"),4);
        if (Spec.Bone==TEXT("lowerarm_r")) Capsule(TEXT("blade_mid_r"),TEXT("blade_tip_r"),4);
        Body->CollisionTraceFlag=CTF_UseSimpleAsComplex; Body->PhysicsType=PhysType_Default;
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->DefaultInstance.SetMassOverride(Spec.Mass);
        Body->DefaultInstance.LinearDamping=.8f; Body->DefaultInstance.AngularDamping=2.5f;
        Body->DefaultInstance.bUseCCD=true;
        Body->CreatePhysicsMeshes(); Asset->SkeletalBodySetups.Add(Body);
    }
    Asset->UpdateBodySetupIndexMap();
    for (int32 I=1;I<Asset->SkeletalBodySetups.Num();++I)
    {
        const FName Bone=Asset->SkeletalBodySetups[I]->BoneName; const int32 Index=Ref.FindBoneIndex(Bone);
        int32 Parent=Ref.GetParentIndex(Index);
        while (Parent!=INDEX_NONE && Asset->FindBodyIndex(Ref.GetBoneName(Parent))==INDEX_NONE) Parent=Ref.GetParentIndex(Parent);
        if (Parent==INDEX_NONE) continue;
        auto* Joint=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);
        auto& C=Joint->DefaultInstance; C.ConstraintBone1=Bone; C.ConstraintBone2=Ref.GetBoneName(Parent); C.JointName=Bone;
        const FTransform Anchor(Frames[Index].GetRotation(),Frames[Index].GetLocation());
        C.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(Frames[Index]));
        C.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(Frames[Parent]));
        C.SetLinearXLimit(LCM_Locked,0); C.SetLinearYLimit(LCM_Locked,0); C.SetLinearZLimit(LCM_Locked,0);
        const FString Name=Bone.ToString(); const bool RootJoint=C.ConstraintBone2==TEXT("root");
        const bool Hinge=Name.StartsWith(TEXT("calf")) || Name.StartsWith(TEXT("lowerarm"));
        C.SetAngularSwing1Limit(RootJoint?ACM_Locked:ACM_Limited,Hinge?60.f:35.f);
        C.SetAngularSwing2Limit(RootJoint?ACM_Locked:ACM_Limited,Hinge?8.f:30.f);
        C.SetAngularTwistLimit(RootJoint?ACM_Locked:ACM_Limited,Hinge?8.f:25.f);
        C.SetDisableCollision(true); Asset->ConstraintSetup.Add(Joint);
        Asset->DisableCollision(I,Asset->FindBodyIndex(C.ConstraintBone2));
    }
    for (int32 I=0;I<Asset->SkeletalBodySetups.Num();++I)
        for (int32 J=I+1;J<Asset->SkeletalBodySetups.Num();++J)
        {
            const USkeletalBodySetup* A=Asset->SkeletalBodySetups[I]; const USkeletalBodySetup* B=Asset->SkeletalBodySetups[J];
            bool Overlap=I==0 || J==0;
            const auto& TA=Frames[Ref.FindBoneIndex(A->BoneName)]; const auto& TB=Frames[Ref.FindBoneIndex(B->BoneName)];
            for (const auto& CA:A->AggGeom.SphylElems) for (const auto& CB:B->AggGeom.SphylElems)
            {
                const FVector PA=TA.TransformPosition(CA.Center),PB=TB.TransformPosition(CB.Center);
                const FVector DA=TA.TransformVectorNoScale(CA.Rotation.Quaternion().GetAxisZ())*CA.Length*.5f;
                const FVector DB=TB.TransformVectorNoScale(CB.Rotation.Quaternion().GetAxisZ())*CB.Length*.5f;
                FVector NA,NB; FMath::SegmentDistToSegmentSafe(PA-DA,PA+DA,PB-DB,PB+DB,NA,NB);
                Overlap|=FVector::DistSquared(NA,NB)<FMath::Square(CA.Radius+CB.Radius+1.f);
            }
            if (Overlap) Asset->DisableCollision(I,J);
        }
    Asset->UpdateBoundsBodiesArray(); Asset->MarkPackageDirty(); InMesh->MarkPackageDirty(); return true;
#else
    return false;
#endif
}
