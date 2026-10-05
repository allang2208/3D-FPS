#include "LurkerM08Monster.h"
#include "LurkerM08AnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "ZombieDogAppearanceComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#if WITH_EDITOR
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#endif

ALurkerM08Monster::ALurkerM08Monster(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
    MonsterDisplayName = FText::FromString(TEXT("伏窥者 M-08"));
    Tags.Remove(TEXT("Wolf")); Tags.AddUnique(TEXT("LurkerM08"));
    Level = 8; Rank = EMonsterRank::Normal; ExperienceReward = 300;
    MaxHealth = 340.f; PhysicalDefense = 24.f; MagicDefense = 14.f; CriticalResistance = 12.f;
    WalkSpeed = 150.f; ChaseSpeed = 315.f;
    GetMesh()->SetAnimInstanceClass(ULurkerM08AnimInstance::StaticClass());
    AirChargeRing = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AirChargeRing"));
    AirChargeRing->SetupAttachment(GetRootComponent());
    AirChargeRing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    AirChargeRing->SetCastShadow(false);
    AirChargeRing->SetCanEverAffectNavigation(false);
    AirChargeRing->bReceivesDecals = false;
    AirChargeRing->SetHiddenInGame(true);
    AggroRadius = 1400.f; LeashRadius = 2200.f;
    bHowlOnEncounter = false; bUsePredictiveHunting = true;
    WoundAppearance->bEnabled = false;
    BiteDamage = 32.f; BiteTriggerRange = 165.f; ContactRadius = 38.f;
    BiteWindup = .12f; BiteCooldown = 1.35f; BiteRecovery = .26f;
    PounceDamage = 48.f; PounceMinRange = 145.f; PounceMaxRange = 700.f;
    PounceWindup = .06f; PounceCooldown = 3.8f; PounceRecovery = .16f;
    PounceTravelStart = .24f; PounceTravelEnd = .74f; PounceArcHeight = 18.f;
    PounceLeadStrength = .55f; PounceMaxLeadDistance = 85.f; PounceStandOff = 130.f;
    BiteContactSlack = 18.f; BiteContactAngle = 100.f;
    PounceContactReach = 170.f; PounceContactAngle = 110.f;
    HuntingHeightTolerance = 85.f; AttackTrackingYawRate = 220.f;
    Combat->StaggerDuration = .55f;
    DeathAnimationFraction = .55f;
    GetCapsuleComponent()->InitCapsuleSize(70.f, 70.f);
    BaseEyeHeight = 0.f;
    auto* Movement = GetCharacterMovement();
    Movement->MaxWalkSpeed = ChaseSpeed;
    Movement->RotationRate = FRotator(0, 220, 0);
    // Retain the compatible ground profile for engine metadata; M08 routes by
    // physical surface support and no longer requires a ground NavMesh.
    auto& Agent = Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius = 70.f; Agent.AgentHeight = 140.f; Agent.AgentStepHeight = 40.f;
    Movement->SetUpdateNavAgentWithOwnersCollisions(false);
}

int32 ALurkerM08Monster::AuthorLurkerPhysics(USkeletalMesh* AuthoredMesh)
{
#if WITH_EDITOR
    if (!AuthoredMesh || !AuthoredMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/LurkerM08/"))) return 0;
    UPhysicsAsset* Physics = AuthoredMesh->GetPhysicsAsset();
    if (!Physics || !Physics->GetPathName().StartsWith(TEXT("/Game/Monsters/LurkerM08/"))) return 0;
    const FReferenceSkeleton& Ref = AuthoredMesh->GetRefSkeleton();
    struct FSegment { const TCHAR* Bone; const TCHAR* End; float Radius; };
    const FSegment Segments[] = {
        {TEXT("pelvis"),TEXT("spine_01"),17}, {TEXT("chest"),TEXT("neck"),18},
        {TEXT("neck"),TEXT("head"),15}, {TEXT("head"),TEXT("Wolf_-Head"),19},
        {TEXT("upperarm_L"),TEXT("forearm_L"),10}, {TEXT("forearm_L"),TEXT("hand_L"),8},
        {TEXT("hand_L"),TEXT("finger3_01_L"),9},
        {TEXT("upperarm_R"),TEXT("forearm_R"),10}, {TEXT("forearm_R"),TEXT("hand_R"),8},
        {TEXT("hand_R"),TEXT("finger3_01_R"),9},
        {TEXT("thigh_L"),TEXT("calf_L"),12}, {TEXT("calf_L"),TEXT("ankle_L"),7},
        {TEXT("ankle_L"),TEXT("hindfoot_L"),5}, {TEXT("hindfoot_L"),TEXT("toe2_L"),7},
        {TEXT("thigh_R"),TEXT("calf_R"),12}, {TEXT("calf_R"),TEXT("ankle_R"),7},
        {TEXT("ankle_R"),TEXT("hindfoot_R"),5}, {TEXT("hindfoot_R"),TEXT("toe2_R"),7},
        {TEXT("arch_front_L"),TEXT("arch_crown"),5}, {TEXT("arch_front_R"),TEXT("arch_crown"),5},
        {TEXT("arch_rear_L"),TEXT("arch_crown"),5}, {TEXT("arch_rear_R"),TEXT("arch_crown"),5},
        {TEXT("arch_crown"),nullptr,8}
    };
    for (const auto& Segment : Segments)
        if (Ref.FindBoneIndex(Segment.Bone) == INDEX_NONE ||
            (Segment.End && Ref.FindBoneIndex(Segment.End) == INDEX_NONE)) return 0;
    TArray<FTransform> ComponentPose;
    ComponentPose.SetNum(Ref.GetNum());
    for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
    {
        const int32 Parent = Ref.GetParentIndex(Index);
        ComponentPose[Index] = Parent == INDEX_NONE ? Ref.GetRefBonePose()[Index]
            : Ref.GetRefBonePose()[Index] * ComponentPose[Parent];
    }
    Physics->Modify(); AuthoredMesh->Modify();
    Physics->SkeletalBodySetups.Reset(); Physics->ConstraintSetup.Reset();
    Physics->CollisionDisableTable.Reset();
    Physics->SetPreviewMesh(AuthoredMesh);
    for (const auto& Segment : Segments)
    {
        const int32 Index = Ref.FindBoneIndex(Segment.Bone);
        const FTransform& Transform = ComponentPose[Index];
        const float UnitScale = FMath::Max(.0001f, Transform.GetScale3D().GetAbsMax());
        const FVector End = Segment.End ? Transform.InverseTransformPosition(
            ComponentPose[Ref.FindBoneIndex(Segment.End)].GetLocation()) : FVector(0, 12.f / UnitScale, 0);
        auto* Body = NewObject<USkeletalBodySetup>(Physics, NAME_None, RF_Transactional);
        Body->BoneName = Segment.Bone;
        Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        Body->PhysicsType = PhysType_Default;
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->DefaultInstance.LinearDamping = 1.5f;
        Body->DefaultInstance.AngularDamping = 4.f;
        Body->DefaultInstance.bUseCCD = true;
        FKSphylElem Shape;
        Shape.Center = End * .5f;
        Shape.Radius = Segment.Radius / UnitScale;
        Shape.Length = FMath::Max(0.f, End.Size() - Shape.Radius * 1.5f);
        Shape.Rotation = FQuat::FindBetweenNormals(FVector::UpVector, End.GetSafeNormal(SMALL_NUMBER, FVector::UpVector)).Rotator();
        Body->AggGeom.SphylElems.Add(Shape);
        Body->InvalidatePhysicsData(); Body->CreatePhysicsMeshes();
        Physics->SkeletalBodySetups.Add(Body);
    }
    Physics->UpdateBodySetupIndexMap();
    for (const auto& Body : Physics->SkeletalBodySetups)
    {
        int32 Parent = Ref.GetParentIndex(Ref.FindBoneIndex(Body->BoneName));
        while (Parent != INDEX_NONE && Physics->FindBodyIndex(Ref.GetBoneName(Parent)) == INDEX_NONE)
            Parent = Ref.GetParentIndex(Parent);
        if (Parent == INDEX_NONE) continue;
        auto* Joint = NewObject<UPhysicsConstraintTemplate>(Physics, NAME_None, RF_Transactional);
        auto& Instance = Joint->DefaultInstance;
        Instance.JointName = Body->BoneName;
        Instance.ConstraintBone1 = Body->BoneName;
        Instance.ConstraintBone2 = Ref.GetBoneName(Parent);
        const bool bArch = Body->BoneName.ToString().StartsWith(TEXT("arch_"));
        Instance.SetLinearXLimit(LCM_Locked, 0); Instance.SetLinearYLimit(LCM_Locked, 0); Instance.SetLinearZLimit(LCM_Locked, 0);
        Instance.SetAngularSwing1Limit(ACM_Limited, bArch ? 6.f : 35.f);
        Instance.SetAngularSwing2Limit(ACM_Limited, bArch ? 6.f : 30.f);
        Instance.SetAngularTwistLimit(ACM_Limited, bArch ? 4.f : 22.f);
        Instance.SnapTransformsToDefault(EConstraintTransformComponentFlags::All, Physics);
        Joint->SetDefaultProfile(Instance);
        Physics->ConstraintSetup.Add(Joint);
    }
    // The folded forearms and dorsal supports overlap anatomically. Keep their
    // internal contacts disabled; world contacts still support the corpse.
    for (int32 A = 0; A < Physics->SkeletalBodySetups.Num(); ++A)
        for (int32 B = A + 1; B < Physics->SkeletalBodySetups.Num(); ++B) Physics->DisableCollision(A, B);
    Physics->UpdateBoundsBodiesArray(); Physics->RefreshPhysicsAssetChange();
    AuthoredMesh->SetEnablePerPolyCollision(false);
    Physics->MarkPackageDirty(); AuthoredMesh->MarkPackageDirty();
    return Physics->SkeletalBodySetups.Num();
#else
    return 0;
#endif
}
