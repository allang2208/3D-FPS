#include "VillageBaker.h"
#include "../NPC/VillageResidentDetail.h"
#include "../UI/ResidentHighlightSubsystem.h"
#include "VillageArtisanAppearance.h"

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

namespace BakerCounter
{
    const FSoftObjectPath Mesh(TEXT("/Game/Characters/VillageBaker/SK_VillageBaker_R1.SK_VillageBaker_R1"));

    // Distances from the service counter centre, in its guest-facing frame.
    constexpr double HalfLength = 126.;
    constexpr double HalfDepth = 43.;
    constexpr double StandingOffset = 90.;
    constexpr double GuestEdge = StandingOffset + HalfDepth;
}

FTransform AVillageBaker::GetStandingTransform(const AActor& BakerySite)
{
    const auto* Counter = BakerySite.FindComponentByTag<USceneComponent>(TEXT("VillageBakery.ServiceCounter"));
    // Older village packages placed the counter near the entrance and lack the marker.
    const FTransform CounterFrame = Counter ? Counter->GetComponentTransform() :
        FTransform(FRotator(0., -90., 0.), FVector(-103., 232., 0.)) * BakerySite.GetActorTransform();
    return FTransform(FVector(-BakerCounter::StandingOffset, 0., 0.)) * CounterFrame;
}

AVillageBaker::AVillageBaker()
{
    bReplicates = true;
    SetCanBeDamaged(false);
    Tags.Append({TEXT("NPC"), TEXT("Friendly"), TEXT("VillageBaker")});

    auto* Feet = CreateDefaultSubobject<USceneComponent>(TEXT("StandingPoint"));
    SetRootComponent(Feet);
    auto* Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("StandingCapsule"));
    Capsule->SetupAttachment(Feet);
    Capsule->InitCapsuleSize(32.f, 91.f);
    Capsule->SetRelativeLocation(FVector(0., 0., 91.));
    Capsule->SetCollisionObjectType(ECC_WorldDynamic);
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Capsule->SetCollisionResponseToAllChannels(ECR_Ignore);
    Capsule->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
    Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Capsule->SetGenerateOverlapEvents(false);
    Capsule->SetCanEverAffectNavigation(false);

    auto* ServiceTarget = CreateDefaultSubobject<UBoxComponent>(TEXT("CounterTalkTarget"));
    ServiceTarget->SetupAttachment(Feet);
    ServiceTarget->InitBoxExtent(FVector(3., BakerCounter::HalfLength - 4., 48.));
    ServiceTarget->SetRelativeLocation(FVector(BakerCounter::GuestEdge + 2., 0., 121.));
    ServiceTarget->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ServiceTarget->SetCollisionObjectType(ECC_WorldDynamic);
    ServiceTarget->SetCollisionResponseToAllChannels(ECR_Ignore);
    ServiceTarget->SetCollisionResponseToChannel(ECC_Visibility, ECR_Overlap);
    ServiceTarget->SetGenerateOverlapEvents(false);
    ServiceTarget->SetCanEverAffectNavigation(false);

    Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("BakerBody"));
    Body->SetupAttachment(Feet);
    Body->SetRelativeRotation(FRotator(0., FResidentConversationFacing::RestYaw, 0.));
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetGenerateOverlapEvents(false);
    Body->SetCanEverAffectNavigation(false);
}

void AVillageBaker::BeginPlay()
{
    Super::BeginPlay();
    UResidentHighlightSubsystem::RegisterShopkeeper(*this);
    if (GetNetMode() != NM_DedicatedServer)
        UVillageResidentDetail::Attach(*this, 
            TArray<FSoftObjectPath>{BakerCounter::Mesh, VillageArtisanAssets::StandingBreath},
            FStreamableDelegate::CreateUObject(this, &AVillageBaker::ApplyAppearance), {Body.Get()});
}

void AVillageBaker::ApplyAppearance()
{
    auto* Mesh = Cast<USkeletalMesh>(BakerCounter::Mesh.ResolveObject());
    auto* Idle = Cast<UAnimSequence>(VillageArtisanAssets::StandingBreath.ResolveObject());
    if (!Mesh || !Idle)
    {
        UE_LOG(LogTemp, Error, TEXT("Village baker appearance could not load mesh %s or idle %s (mesh=%d idle=%d)"),
            *BakerCounter::Mesh.ToString(), *VillageArtisanAssets::StandingBreath.ToString(), Mesh != nullptr, Idle != nullptr);
        return;
    }
    Body->SetSkeletalMeshAsset(Mesh);
    float Phase = 0.f;
    if (const auto* State = GetWorld()->GetGameState(); State && Idle->GetPlayLength() > 0.f)
        Phase = FMath::Fmod(State->GetServerWorldTimeSeconds(), double(Idle->GetPlayLength()));
    Facing.StartIdle(*Body, *Idle, Phase);
}

bool AVillageBaker::GetCounterTalkPoint(const APawn& Guest, FVector& Point) const
{
    FVector Feet = Guest.GetActorLocation();
    if (const auto* Capsule = Guest.FindComponentByClass<UCapsuleComponent>())
        Feet = Capsule->GetComponentLocation() - FVector::UpVector * Capsule->GetScaledCapsuleHalfHeight();
    const FTransform& Frame = GetActorTransform();
    const FVector Local = Frame.InverseTransformPosition(Feet);
    if (Local.X < BakerCounter::GuestEdge || Local.X > BakerCounter::GuestEdge + 125.
        || FMath::Abs(Local.Y) > BakerCounter::HalfLength || Local.Z < -45. || Local.Z > 55.)
        return false;
    Point = Frame.TransformPosition(FVector(0., 0., 157.));
    return true;
}

bool AVillageBaker::CanServe(const APawn* Pawn) const
{
    return ResidentConversation::CanReach(Pawn, this);
}

void AVillageBaker::SetLocalConversation(APlayerController* Player)
{
    Facing.SetLocalPlayer(Player);
}
