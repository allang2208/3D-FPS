#include "SpitterZombie.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"

bool ASpitterZombie::PreparePhysics(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
    if(!InMesh || !InMesh->GetPhysicsAsset() || !InMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/SpitterZombie/")))return false;
    auto* Asset=InMesh->GetPhysicsAsset(); const auto& Ref=InMesh->GetRefSkeleton();
    TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 RootIndex=Ref.FindBoneIndex(TEXT("SpitterRoot"));
    if(RootIndex==INDEX_NONE || Ref.FindBoneIndex(TEXT("Hips"))==INDEX_NONE)return false;
    const TMap<FName,float> Masses={
        {TEXT("SpitterRoot"),1.f},{TEXT("Hips"),9.f},{TEXT("Spine02"),8.f},{TEXT("Spine01"),7.f},{TEXT("Spine"),7.f},
        {TEXT("neck"),1.f},{TEXT("Head"),4.f},{TEXT("LeftArm"),2.f},{TEXT("RightArm"),2.f},
        {TEXT("LeftForeArm"),1.5f},{TEXT("RightForeArm"),1.5f},{TEXT("LeftHand"),.5f},{TEXT("RightHand"),.5f},
        {TEXT("LeftUpLeg"),5.f},{TEXT("RightUpLeg"),5.f},{TEXT("LeftLeg"),3.f},{TEXT("RightLeg"),3.f},
        {TEXT("LeftFoot"),1.f},{TEXT("RightFoot"),1.f}};
    Asset->Modify(); Asset->ConstraintSetup.Reset(); Asset->CollisionDisableTable.Reset();
    Asset->SkeletalBodySetups.RemoveAll([&](const auto& Body){return !Body || !Masses.Contains(Body->BoneName);});
    Asset->UpdateBodySetupIndexMap();
    if(Asset->FindBodyIndex(TEXT("SpitterRoot"))==INDEX_NONE)
    {
        auto* Root=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);
        Root->BoneName=TEXT("SpitterRoot"); FKSphereElem Sphere;
        Sphere.Radius=1.f/Frames[RootIndex].GetScale3D().GetAbsMax(); Root->AggGeom.SphereElems.Add(Sphere);
        Asset->SkeletalBodySetups.Insert(Root,0);
    }
    for(USkeletalBodySetup* Body:Asset->SkeletalBodySetups)
    {
        Body->Modify(); Body->CollisionTraceFlag=CTF_UseSimpleAsComplex; Body->PhysicsType=PhysType_Default;
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->DefaultInstance.LinearDamping=.8f; Body->DefaultInstance.AngularDamping=2.5f;
        Body->DefaultInstance.SetMassOverride(Masses.FindRef(Body->BoneName));
        Body->DefaultInstance.bUseCCD=true;
        Body->DefaultInstance.PositionSolverIterationCount=12; Body->DefaultInstance.VelocitySolverIterationCount=6;
        if(Body->BoneName==TEXT("SpitterRoot"))
        {Body->bConsiderForBounds=false;Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision);}
        Body->InvalidatePhysicsData(); Body->CreatePhysicsMeshes();
    }
    Asset->UpdateBodySetupIndexMap();
    for(int32 I=0;I<Asset->SkeletalBodySetups.Num();++I)
    {
        const FName Name=Asset->SkeletalBodySetups[I]->BoneName;
        const int32 Bone=Ref.FindBoneIndex(Name); int32 Parent=Ref.GetParentIndex(Bone);
        while(Parent>=0 && Asset->FindBodyIndex(Ref.GetBoneName(Parent))==INDEX_NONE)Parent=Ref.GetParentIndex(Parent);
        if(Parent<0)continue;
        auto* Joint=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);
        auto& C=Joint->DefaultInstance;
        C.JointName=Name;C.ConstraintBone1=Name;C.ConstraintBone2=Ref.GetBoneName(Parent);
        const FTransform Anchor(Frames[Bone].GetRotation(),Frames[Bone].GetLocation());
        C.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(Frames[Bone]));
        C.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(Frames[Parent]));
        C.SetLinearXLimit(LCM_Locked,0);C.SetLinearYLimit(LCM_Locked,0);C.SetLinearZLimit(LCM_Locked,0);
        const bool bRoot=C.ConstraintBone2==TEXT("SpitterRoot");
        C.SetAngularSwing1Limit(bRoot?ACM_Locked:ACM_Limited,35.f);
        C.SetAngularSwing2Limit(bRoot?ACM_Locked:ACM_Limited,30.f);
        C.SetAngularTwistLimit(bRoot?ACM_Locked:ACM_Limited,25.f);
        C.SetDisableCollision(true);
        Asset->ConstraintSetup.Add(Joint);
        Asset->DisableCollision(I,Asset->FindBodyIndex(C.ConstraintBone2));
    }
    Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();InMesh->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
