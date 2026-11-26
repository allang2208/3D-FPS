#include "VillageTavernKeeper.h"
#include "../NPC/VillageResidentDetail.h"
#include "../UI/ResidentHighlightSubsystem.h"

#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Pawn.h"

namespace
{
const FSoftObjectPath KeeperMesh(TEXT("/Game/Characters/VillageTavernKeeper/SK_TavernKeeper.SK_TavernKeeper"));
const FSoftObjectPath KeeperIdle(TEXT("/Game/Characters/VillageTavernKeeper/A_TavernKeeper_Idle.A_TavernKeeper_Idle"));
// In the keeper's frame the 260 x 72 cm counter is centred 85 cm in front of her.
constexpr double GuestEdge = 85. + 36.;
constexpr double CounterHalfLength = 130.;
}

AVillageTavernKeeper::AVillageTavernKeeper()
{
    bReplicates = true;
    SetCanBeDamaged(false);
    Tags.Append({TEXT("NPC"), TEXT("Friendly"), TEXT("VillageTavernKeeper")});
    auto* Feet = CreateDefaultSubobject<USceneComponent>(TEXT("StandingPoint"));
    SetRootComponent(Feet);

    auto* Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("StandingCapsule"));
    Capsule->SetupAttachment(Feet);
    Capsule->InitCapsuleSize(28.f, 84.f);
    Capsule->SetRelativeLocation(FVector(0., 0., 84.));
    Capsule->SetCollisionObjectType(ECC_WorldDynamic);
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Capsule->SetCollisionResponseToAllChannels(ECR_Ignore);
    Capsule->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
    Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Capsule->SetGenerateOverlapEvents(false);
    Capsule->SetCanEverAffectNavigation(false);

    auto* ServiceTarget = CreateDefaultSubobject<UBoxComponent>(TEXT("CounterTalkTarget"));
    ServiceTarget->SetupAttachment(Feet);
    ServiceTarget->SetRelativeLocation(FVector(GuestEdge + 2., 0., 119.));
    ServiceTarget->InitBoxExtent(FVector(3., CounterHalfLength - 4., 47.));
    ServiceTarget->SetCollisionObjectType(ECC_WorldDynamic);
    ServiceTarget->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ServiceTarget->SetCollisionResponseToAllChannels(ECR_Ignore);
    ServiceTarget->SetCollisionResponseToChannel(ECC_Visibility, ECR_Overlap);
    ServiceTarget->SetGenerateOverlapEvents(false);
    ServiceTarget->SetCanEverAffectNavigation(false);

    Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("TavernKeeperBody"));
    Body->SetupAttachment(Feet);
    // The imported body is grounded at the soles and faces mesh +Y. The counter marker faces actor +X.
    Body->SetRelativeRotation(FRotator(0., FResidentConversationFacing::RestYaw, 0.));
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetGenerateOverlapEvents(false);
    Body->SetCanEverAffectNavigation(false);
}

void AVillageTavernKeeper::BeginPlay()
{
    Super::BeginPlay();
    UResidentHighlightSubsystem::RegisterShopkeeper(*this);
    if (GetNetMode() != NM_DedicatedServer)
        UVillageResidentDetail::Attach(*this, 
            TArray<FSoftObjectPath>{KeeperMesh, KeeperIdle},
            FStreamableDelegate::CreateUObject(this, &AVillageTavernKeeper::ApplyAppearance), {Body.Get()});
}

void AVillageTavernKeeper::ApplyAppearance()
{
    auto* Mesh = Cast<USkeletalMesh>(KeeperMesh.ResolveObject());
    auto* Idle = Cast<UAnimSequence>(KeeperIdle.ResolveObject());
    if (!Mesh || !Idle)
    {
        UE_LOG(LogTemp, Error, TEXT("Tavern keeper could not load mesh %s or idle %s (mesh=%d idle=%d)"),
            *KeeperMesh.ToString(), *KeeperIdle.ToString(), Mesh != nullptr, Idle != nullptr);
        return;
    }

    Body->SetSkeletalMeshAsset(Mesh);
    float IdleTime = 0.f;
    if (const AGameStateBase* State = GetWorld()->GetGameState(); State && Idle->GetPlayLength() > 0.f)
        IdleTime = FMath::Fmod(State->GetServerWorldTimeSeconds(), double(Idle->GetPlayLength()));
    ConversationFacing.StartIdle(*Body, *Idle, IdleTime);
}

bool AVillageTavernKeeper::GetCounterTalkPoint(const APawn& Guest, FVector& Point) const
{
    FVector Feet = Guest.GetActorLocation();
    if (const auto* Capsule = Guest.FindComponentByClass<UCapsuleComponent>())
        Feet = Capsule->GetComponentLocation() - FVector::UpVector * Capsule->GetScaledCapsuleHalfHeight();
    const FTransform& Frame = GetActorTransform();
    const FVector Local = Frame.InverseTransformPosition(Feet);
    if (Local.X < GuestEdge || Local.X > GuestEdge + 140. || FMath::Abs(Local.Y) > CounterHalfLength
        || Local.Z < -45. || Local.Z > 55.)
        return false;

    Point = Frame.TransformPosition(FVector(0., 0., 153.));
    return true;
}

bool AVillageTavernKeeper::CanServe(const APawn* Pawn) const
{
    return ResidentConversation::CanReach(Pawn, this);
}

void AVillageTavernKeeper::SetLocalConversation(APlayerController* Player)
{
    ConversationFacing.SetLocalPlayer(Player);
}
