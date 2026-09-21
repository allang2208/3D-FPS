#include "WitchMotionCandidate.h"
#include "WitchFoundationAnimInstance.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

void AWitchMotionCandidate::AssignFoundationSkeleton(USkeletalMesh* TargetMesh, USkeleton* TargetSkeleton)
{
#if WITH_EDITOR
    if (TargetMesh && TargetSkeleton)
    {
        TargetMesh->SetSkeleton(TargetSkeleton);
        TargetMesh->SetPostProcessAnimBlueprint(nullptr);
        TargetMesh->MarkPackageDirty();
    }
#endif
}

AWitchMotionCandidate::AWitchMotionCandidate()
{
    PrimaryActorTick.bCanEverTick = true;
    Tags.Add(TEXT("WitchMotionCandidate"));
    GetCapsuleComponent()->InitCapsuleSize(34.f, 94.f);
    auto* Move = GetCharacterMovement();
    Move->MaxWalkSpeed = 82.5f;
    Move->MaxAcceleration = 130.f;
    Move->BrakingDecelerationWalking = 190.f;
    Move->GetNavMovementProperties()->bUseAccelerationForPaths = true;
    Move->bOrientRotationToMovement = true;
    Move->RotationRate = FRotator(0, 110.f, 0);
    Move->MaxStepHeight = 40.f;
    Move->SetUpdateNavAgentWithOwnersCollisions(false);
    auto& Agent = Move->GetNavAgentPropertiesRef();
    Agent.AgentRadius = 34.f; Agent.AgentHeight = 192.f; Agent.AgentStepHeight = 40.f;
    bUseControllerRotationYaw = false;
    AIControllerClass = AAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Body(TEXT("/Game/Monsters/WitchFoundation/SK_WitchFoundation.SK_WitchFoundation"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Idle(TEXT("/Game/Monsters/WitchFoundation/Animations/A_WitchFoundation_Idle.A_WitchFoundation_Idle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Walk(TEXT("/Game/Monsters/WitchFoundation/Animations/A_WitchFoundation_Walk.A_WitchFoundation_Walk"));
    GetMesh()->SetSkeletalMeshAsset(Body.Object);
    GetMesh()->SetAnimInstanceClass(UWitchFoundationAnimInstance::StaticClass());
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GetMesh()->SetCanEverAffectNavigation(false);
    IdleClip = Idle.Object; WalkClip = Walk.Object;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> StaffAsset(TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_Staff.SM_Witch_Staff"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> BottleAsset(TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_PoisonBottle.SM_Witch_PoisonBottle"));
    Staff = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Staff"));
    Bottle = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Bottle"));
    Staff->SetupAttachment(GetMesh(), TEXT("hand_l")); Staff->SetStaticMesh(StaffAsset.Object);
    Bottle->SetupAttachment(GetMesh(), TEXT("hand_r")); Bottle->SetStaticMesh(BottleAsset.Object);
    for (auto* Prop : {Staff.Get(), Bottle.Get()})
    {
        Prop->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Prop->SetGenerateOverlapEvents(false); Prop->SetCanEverAffectNavigation(false);
    }
    AlignBodyAndGrips();
}

void AWitchMotionCandidate::AlignBodyAndGrips()
{
    const auto* Model = GetMesh()->GetSkeletalMeshAsset();
    if (!Model) return;
    const auto& Ref = Model->GetRefSkeleton();
    auto Rest = [&Ref](FName Name)
    {
        const int32 I = Ref.FindBoneIndex(Name);
        if (I == INDEX_NONE) return FTransform::Identity;
        FTransform T = Ref.GetRefBonePose()[I];
        for (int32 P = Ref.GetParentIndex(I); P != INDEX_NONE; P = Ref.GetParentIndex(P)) T *= Ref.GetRefBonePose()[P];
        return T;
    };
    const FVector Forward = (Rest(TEXT("ball_l")).GetLocation() - Rest(TEXT("foot_l")).GetLocation()
        + Rest(TEXT("ball_r")).GetLocation() - Rest(TEXT("foot_r")).GetLocation()).GetSafeNormal2D();
    GetMesh()->SetRelativeRotation(FRotator(0, -Forward.Rotation().Yaw, 0));
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()));
    for (const bool bLeft : {true, false})
    {
        const FString S = bLeft ? TEXT("l") : TEXT("r");
        const FTransform Hand = Rest(FName(*(TEXT("hand_") + S)));
        const FVector Along = (Rest(FName(*(TEXT("middle_01_") + S))).GetLocation() - Hand.GetLocation()).GetSafeNormal();
        const FVector Across = (Rest(FName(*(TEXT("index_01_") + S))).GetLocation()
            - Rest(FName(*(TEXT("pinky_01_") + S))).GetLocation()).GetSafeNormal();
        const FVector Palm = FVector::CrossProduct(Along, Across).GetSafeNormal() * (bLeft ? -1.f : 1.f);
        const FVector GripLocal = Hand.InverseTransformPosition(Hand.GetLocation() + Along * 7.1f + Palm * 2.2f);
        const FVector UpLocal = Hand.InverseTransformVectorNoScale(Across);
        const FVector ForwardLocal = Hand.InverseTransformVectorNoScale(Along);
        const FQuat Rotation = FRotationMatrix::MakeFromZX(UpLocal, ForwardLocal).ToQuat();
        auto* Prop = bLeft ? Staff.Get() : Bottle.Get();
        const FVector Location = GripLocal - Rotation.RotateVector(FVector(0, 0, bLeft ? 92.f : 9.f));
        Prop->SetRelativeTransform(FTransform(Rotation, Location));
    }
}

void AWitchMotionCandidate::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform); AlignBodyAndGrips();
}

void AWitchMotionCandidate::BeginPlay()
{
    // Assets can be imported after the new native class is first loaded in the editor.
    if (!GetMesh()->GetSkeletalMeshAsset()) GetMesh()->SetSkeletalMeshAsset(LoadObject<USkeletalMesh>(nullptr,
        TEXT("/Game/Monsters/WitchFoundation/SK_WitchFoundation.SK_WitchFoundation")));
    if (!IdleClip) IdleClip = LoadObject<UAnimSequence>(nullptr,
        TEXT("/Game/Monsters/WitchFoundation/Animations/A_WitchFoundation_Idle.A_WitchFoundation_Idle"));
    if (!WalkClip) WalkClip = LoadObject<UAnimSequence>(nullptr,
        TEXT("/Game/Monsters/WitchFoundation/Animations/A_WitchFoundation_Walk.A_WitchFoundation_Walk"));
    AlignBodyAndGrips();
    GetMesh()->SetAnimInstanceClass(UWitchFoundationAnimInstance::StaticClass());
    Super::BeginPlay();
}

void AWitchMotionCandidate::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority() || GetWorld()->GetTimeSeconds() < NextPathAt) return;
    NextPathAt = GetWorld()->GetTimeSeconds() + .35f;
    auto* AI = Cast<AAIController>(GetController());
    auto* Target = UGameplayStatics::GetPlayerPawn(this, 0);
    if (!AI || !Target) return;
    const float Distance = FVector::Dist2D(GetActorLocation(), Target->GetActorLocation());
    if (Distance <= 205.f || Distance > 3000.f) AI->StopMovement();
    else AI->MoveToActor(Target, 180.f, true, true, true, nullptr, true);
}
