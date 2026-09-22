#include "WitchRebuiltMonster.h"
#include "WitchRebuiltAnimInstance.h"
#include "MonsterCombatComponent.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"

AWitchRebuiltMonster::AWitchRebuiltMonster(const FObjectInitializer& Initializer) : Super(Initializer)
{
    Tags.Add(TEXT("WitchRebuilt"));
    WalkSpeed = 82.5f;
    auto* Move = GetCharacterMovement();
    Move->MaxWalkSpeed = WalkSpeed; Move->MaxAcceleration = 130.f;
    Move->BrakingDecelerationWalking = 190.f;
    Move->GetNavMovementProperties()->bUseAccelerationForPaths = true;
    ResolveAssets();
    GetMesh()->SetAnimInstanceClass(UWitchRebuiltAnimInstance::StaticClass());
    AlignVisual();
}

void AWitchRebuiltMonster::ResolveAssets()
{
    // Never fall back to an incompatible historical Witch skeleton for this class.
    VisualMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Monsters/WitchRebuilt/SK_WitchRebuilt.SK_WitchRebuilt"));
    auto Clip = [](const TCHAR* ClipRole)
    {
        const FString Name = FString(TEXT("A_WitchRebuilt_")) + ClipRole;
        return LoadObject<UAnimSequence>(nullptr, *(TEXT("/Game/Monsters/WitchRebuilt/Animations/") + Name + TEXT(".") + Name));
    };
    IdleClip = Clip(TEXT("Idle")); WalkClip = Clip(TEXT("Walk"));
    CastClip = Clip(TEXT("CastPoison")); ThrowClip = Clip(TEXT("ThrowPoisonBottle"));
    DeathClip = Clip(TEXT("DeathBackward")); Combat->HitClip = Clip(TEXT("Hit"));
    TurnLeftClip = Clip(TEXT("TurnLeft")); TurnRightClip = Clip(TEXT("TurnRight"));
    AttackClip = CastClip;
    Bottle->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,
        TEXT("/Game/Monsters/WitchRebuilt/Props/SM_WitchRebuilt_Bottle.SM_WitchRebuilt_Bottle")));
}

void AWitchRebuiltMonster::AlignVisual()
{
    Super::AlignVisual();
    if (!VisualMesh) return;
    const auto& Ref = VisualMesh->GetRefSkeleton();
    auto Position = [&Ref](FName Name)
    {
        const int32 I = Ref.FindBoneIndex(Name);
        if (I == INDEX_NONE) return FVector::ZeroVector;
        FTransform T = Ref.GetRefBonePose()[I];
        for (int32 P = Ref.GetParentIndex(I); P != INDEX_NONE; P = Ref.GetParentIndex(P)) T *= Ref.GetRefBonePose()[P];
        return T.GetLocation();
    };
    const FVector Forward = (Position(TEXT("ball_l")) - Position(TEXT("foot_l"))
        + Position(TEXT("ball_r")) - Position(TEXT("foot_r"))).GetSafeNormal2D();
    GetMesh()->SetRelativeRotation(FRotator(0, -Forward.Rotation().Yaw, 0));
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()));
}

void AWitchRebuiltMonster::AttachProps()
{
    if (!VisualMesh) return;
    const auto& Ref = VisualMesh->GetRefSkeleton();
    auto Rest = [&Ref](FName Name)
    {
        const int32 I = Ref.FindBoneIndex(Name);
        if (I == INDEX_NONE) return FTransform::Identity;
        FTransform T = Ref.GetRefBonePose()[I];
        for (int32 P = Ref.GetParentIndex(I); P != INDEX_NONE; P = Ref.GetParentIndex(P)) T *= Ref.GetRefBonePose()[P];
        return T;
    };
    for (const bool Left : {true, false})
    {
        const FString S = Left ? TEXT("l") : TEXT("r");
        const FName Bone(*(TEXT("hand_") + S)); const FTransform Hand = Rest(Bone);
        const FVector Along = (Rest(FName(*(TEXT("middle_01_") + S))).GetLocation() - Hand.GetLocation()).GetSafeNormal();
        const FVector Across = (Rest(FName(*(TEXT("index_01_") + S))).GetLocation()
            - Rest(FName(*(TEXT("pinky_01_") + S))).GetLocation()).GetSafeNormal();
        // Anatomy is mirrored: reference finger flexion is +cross on Blender's
        // left hand and -cross on its right. FBX's Y reflection reverses both.
        // A common sign placed the bottle on the dorsal side of the right hand.
        const FVector Palm = (Left ? -1.f : 1.f) * FVector::CrossProduct(Along, Across).GetSafeNormal();
        const FVector Grip = Hand.InverseTransformPosition(Hand.GetLocation() + Along * 8.5f + Palm * (Left ? 5.0f : 6.7f));
        const FQuat Rotation = FRotationMatrix::MakeFromZX(Hand.InverseTransformVectorNoScale(Across),
            Hand.InverseTransformVectorNoScale(Along)).ToQuat();
        auto* Prop = Left ? Staff.Get() : Bottle.Get();
        Prop->AttachToComponent(GetMesh(), FAttachmentTransformRules::KeepRelativeTransform, Bone);
        Prop->SetRelativeTransform(FTransform(Rotation, Grip - Rotation.RotateVector(FVector(0,0,Left ? 92.f : 11.8f))));
    }
}

void AWitchRebuiltMonster::BeginPlay()
{
    ResolveAssets();
    GetMesh()->SetAnimInstanceClass(UWitchRebuiltAnimInstance::StaticClass());
    PreviousYaw = GetActorRotation().Yaw;
    Super::BeginPlay();
}

void AWitchRebuiltMonster::StartStateAnimation(UAnimSequence* Clip, bool bLoop)
{
    if (!Cast<UWitchRebuiltAnimInstance>(GetMesh()->GetAnimInstance()))
        GetMesh()->SetAnimInstanceClass(UWitchRebuiltAnimInstance::StaticClass());
    Super::StartStateAnimation(Clip, bLoop);
}

bool AWitchRebuiltMonster::CanCast(APawn* Candidate) const
{
    // Settling happens before the shared attack clock starts; release times stay exact.
    return SettledSeconds >= .22f && Super::CanCast(Candidate);
}

void AWitchRebuiltMonster::StartDeathPresentation()
{
    // The skirt is waist-supported, not trouser-skinned. Keep its continuous
    // physical sheet through the fall; disabling it would expose the legs again.
    GetMesh()->ForceClothNextUpdateTeleportAndReset();
    Super::StartDeathPresentation();
}

void AWitchRebuiltMonster::Tick(float Dt)
{
    Super::Tick(Dt);
    const float Yaw = GetActorRotation().Yaw;
    const float TurnRate = FMath::Abs(FMath::FindDeltaAngleDegrees(PreviousYaw, Yaw)) / FMath::Max(.001f, Dt);
    PreviousYaw = Yaw;
    SettledSeconds = GetVelocity().Size2D() < 3.f && TurnRate < 12.f ? SettledSeconds + Dt : 0.f;
    // Hysteresis avoids resetting the solver repeatedly at a single distance.
    const APlayerController* ViewerController = GetWorld()->GetFirstPlayerController();
    const APawn* Viewer = ViewerController ? ViewerController->GetPawn() : nullptr;
    const double DistanceSquared = Viewer ? FVector::DistSquared(Viewer->GetActorLocation(),
        GetMesh()->GetComponentLocation()) : 0.;
    if (DistanceSquared <= FMath::Square(2000.f)) bWantsClothSimulation = true;
    else if (DistanceSquared >= FMath::Square(2400.f)) bWantsClothSimulation = false;
    if (bWantsClothSimulation && GetMesh()->IsClothingSimulationSuspended())
    {
        GetMesh()->ResumeClothingSimulation();
        GetMesh()->ForceClothNextUpdateTeleportAndReset();
    }
    GetMesh()->ClothBlendWeight = FMath::FInterpConstantTo(GetMesh()->ClothBlendWeight,
        bWantsClothSimulation ? 1.f : 0.f, Dt, 1.f / .35f);
    if (!bWantsClothSimulation && GetMesh()->ClothBlendWeight <= 0.f && !GetMesh()->IsClothingSimulationSuspended())
        GetMesh()->SuspendClothingSimulation();
    // Simulated clothing uses the accepted LOD0 binding. Reduced LODs are only
    // eligible after the far-distance transition has reached its skinned pose.
    const int32 ForcedLOD = bWantsClothSimulation || GetMesh()->ClothBlendWeight > 0.f ? 1 : 0;
    if (GetMesh()->GetForcedLOD() != ForcedLOD) GetMesh()->SetForcedLOD(ForcedLOD);
}
