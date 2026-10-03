#include "FleshHandMonster.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"

bool AFleshHandMonster::BuildCorpsePhysics(USkeletalMesh* Mesh,UPhysicsAsset* Asset)
{
#if WITH_EDITOR
    if(!Mesh||!Asset||Asset->SkeletalBodySetups.IsEmpty())return false;
    const auto& Ref=Mesh->GetRefSkeleton();
    TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)
        if(Ref.GetParentIndex(I)!=INDEX_NONE)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    Asset->Modify();Asset->ConstraintSetup.Reset();Asset->CollisionDisableTable.Reset();Asset->UpdateBodySetupIndexMap();
    TArray<FBox> Bounds;
    for(const auto& Pointer:Asset->SkeletalBodySetups)
    {
        auto* Body=Pointer.Get();if(!Body)continue;
        Body->Modify();Body->PhysicsType=PhysType_Default;
        const FString Name=Body->BoneName.ToString().ToLower();
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->DefaultInstance.LinearDamping=.25f;Body->DefaultInstance.AngularDamping=.9f;
        Body->DefaultInstance.SetMassOverride(Name.Contains(TEXT("palm"))?12.f:
            Name.Contains(TEXT("arm"))||Name.Contains(TEXT("wrist"))?6.f:.7f);
        Body->DefaultInstance.bUseCCD=true;
        Body->DefaultInstance.PositionSolverIterationCount=12;
        Body->DefaultInstance.VelocitySolverIterationCount=4;
        const int32 Bone=Ref.FindBoneIndex(Body->BoneName);
        if(Bone==INDEX_NONE)return false;
        Bounds.Add(Body->AggGeom.CalcAABB(Frames[Bone]));
        int32 Parent=Ref.GetParentIndex(Bone);
        while(Parent!=INDEX_NONE&&Asset->FindBodyIndex(Ref.GetBoneName(Parent))==INDEX_NONE)Parent=Ref.GetParentIndex(Parent);
        if(Parent==INDEX_NONE)continue;
        auto* Joint=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);
        auto& C=Joint->DefaultInstance;
        C.JointName=Body->BoneName;C.ConstraintBone1=Body->BoneName;C.ConstraintBone2=Ref.GetBoneName(Parent);
        const FTransform Anchor(Frames[Bone].GetRotation(),Frames[Bone].GetLocation());
        C.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(Frames[Bone]));
        C.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(Frames[Parent]));
        C.SetLinearXLimit(LCM_Locked,0);C.SetLinearYLimit(LCM_Locked,0);C.SetLinearZLimit(LCM_Locked,0);
        const bool Wrist=Name.Contains(TEXT("palm"))||Name.Contains(TEXT("wrist"));
        C.SetAngularSwing1Limit(ACM_Limited,Wrist?55.f:45.f);
        C.SetAngularSwing2Limit(ACM_Limited,Wrist?35.f:25.f);
        C.SetAngularTwistLimit(ACM_Limited,Wrist?30.f:15.f);
        C.SetDisableCollision(true);C.DisableProjection();C.SetShockPropagationParams(false,0.f);
        C.SetOrientationDriveTwistAndSwing(false,false);C.SetAngularVelocityDriveTwistAndSwing(false,false);
        Joint->SetDefaultProfile(C);Asset->ConstraintSetup.Add(Joint);
        Asset->DisableCollision(Asset->FindBodyIndex(Body->BoneName),Asset->FindBodyIndex(C.ConstraintBone2));
    }
    // Query-only authoring disables every pair. In the dedicated corpse,
    // suppress adjacent/reference-overlapping volumes while allowing the
    // remaining palm/finger bodies to contact one another naturally.
    for(int32 I=0;I<Bounds.Num();++I)for(int32 J=I+1;J<Bounds.Num();++J)
        if(Bounds[I].Intersect(Bounds[J]))Asset->DisableCollision(I,J);
    Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();
    // The caller saves this separate asset; the live query asset and mesh stay intact.
    return !Asset->ConstraintSetup.IsEmpty();
#else
    return false;
#endif
}
