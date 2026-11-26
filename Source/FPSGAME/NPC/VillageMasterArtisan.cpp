#include "VillageMasterArtisan.h"
#include "../WorldGeneration/VillageMechanicalWorkshop.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "VillageArtisanAppearance.h"
#include "VillageResidentDetail.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StreamableManager.h"
#include "TimerManager.h"

namespace
{
const FVillageArtisanAppearance MasterAppearance{
    FSoftObjectPath(TEXT("/Game/Characters/VillageMasterArtisan/SK_MasterArtisan_Head.SK_MasterArtisan_Head")),
    FSoftObjectPath(TEXT("/Game/Characters/VillageMasterArtisan/SK_MasterArtisan_Workwear.SK_MasterArtisan_Workwear"))
};
}

AVillageMasterArtisan::AVillageMasterArtisan()
{
    bReplicates = true;
    bNetUseOwnerRelevancy = true;
    PrimaryActorTick.bCanEverTick = false;
    auto* Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("StandingCapsule"));
    SetRootComponent(Capsule);
    Capsule->InitCapsuleSize(31.f, 91.f);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));
    Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Capsule->SetCanEverAffectNavigation(false);
    Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("StrongBody"));
    Body->SetupAttachment(Capsule);
    Body->SetRelativeLocationAndRotation(FVector(0,0,-91), FRotator(0,FResidentConversationFacing::RestYaw,0));
    Head = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("ArtisanHead"));
    Workwear = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("ArtisanWorkwear"));
    Head->SetupAttachment(Body);
    Workwear->SetupAttachment(Body);
    for (auto* Part : {Body.Get(), Head.Get(), Workwear.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetVisibility(false);
    }
    Tags.Add(TEXT("NPC"));
    Tags.Add(TEXT("Friendly"));
}

ATemperateHillsWorld* AVillageMasterArtisan::Village() const
{
    const auto* Shop=Cast<AVillageMechanicalWorkshop>(GetParentActor());
    return Shop ? Cast<ATemperateHillsWorld>(Shop->GetOwner()) : nullptr;
}

void AVillageMasterArtisan::BeginPlay()
{
    Super::BeginPlay();
    UVillageResidentDetail::Attach(*this, MasterAppearance.Paths(),
        FStreamableDelegate::CreateUObject(this, &AVillageMasterArtisan::Dress),
        {Body.Get(), Head.Get(), Workwear.Get()},
        FSimpleDelegate::CreateWeakLambda(this, [this] { GetWorldTimerManager().ClearTimer(DressTimer); }));
}

void AVillageMasterArtisan::Dress()
{
    if (MasterAppearance.IsCompiling())
    {
        GetWorldTimerManager().SetTimer(DressTimer, this, &AVillageMasterArtisan::Dress, .05f, false);
        return;
    }
    MasterAppearance.Dress(*Body, *Head, *Workwear, Facing);
}

void AVillageMasterArtisan::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DressTimer);
    Super::EndPlay(Reason);
}
