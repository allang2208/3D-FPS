#include "VillageGunshopServices.h"
#include "../NPC/VillageResidentDetail.h"
#include "../Building/VoxelBuildWorld.h"
#include "../NPC/VillageArtisanAppearance.h"
#include "../UI/ResidentHighlightSubsystem.h"
#include "TemperateHillsWorld.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"
#include "TimerManager.h"

AVillageGunshopWorkbench::AVillageGunshopWorkbench()
{
    bAlwaysRelevant = true;
    Body()->SetReceivesDecals(false);
}

void AVillageGunshopWorkbench::BeginPlay()
{
    Super::BeginPlay();
    BindBuildingWorld();
}

void AVillageGunshopWorkbench::BindBuildingWorld()
{
    if (!HasAuthority()) { RefreshRegistration(); return; }
    for (TActorIterator<AVoxelBuildWorld> It(GetWorld()); It; ++It)
    {
        if (!It->IsReady()) continue;
        SetOwner(*It);
        RefreshRegistration();
        return;
    }
    GetWorldTimerManager().SetTimer(BindTimer, this, &ThisClass::BindBuildingWorld, 1.f, false);
}

bool AVillageGunshopWorkbench::IsSceneStationAvailable() const
{
    return !IsHidden() && !IsFalling() && PrefabId() == VoxelGunWorkbenchId;
}

void AVillageGunshopWorkbench::RefreshRegistration()
{
    auto* Building = Cast<AVoxelBuildWorld>(GetOwner());
    if (!Building) return;
    if (HasAuthority())
    {
        const FName Desired = IsHidden() ? NAME_None : VoxelGunWorkbenchId;
        const FVector P = GetActorLocation() / 20.;
        const FIntVector StationCell(FMath::FloorToInt(P.X), FMath::FloorToInt(P.Y), FMath::FloorToInt(P.Z));
        if (PrefabId() != Desired || AnchorCell() != StationCell || NetMesh != StationMesh)
        {
            Configure(Desired, StationCell, 0, StationMesh, nullptr, nullptr);
            ForceNetUpdate();
        }
    }
    if (IsSceneStationAvailable()) Building->RegisterSceneStation(this);
    else Building->UnregisterSceneStation(this);
}

void AVillageGunshopWorkbench::SetActorHiddenInGame(bool bNewHidden)
{
    Super::SetActorHiddenInGame(bNewHidden);
    if (HasActorBegunPlay()) RefreshRegistration();
}

void AVillageGunshopWorkbench::OnRep_Owner()
{
    Super::OnRep_Owner();
    RefreshRegistration();
}

void AVillageGunshopWorkbench::OnRep_Configuration()
{
    Super::OnRep_Configuration();
    RefreshRegistration();
}

void AVillageGunshopWorkbench::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(BindTimer);
    if (auto* Building = Cast<AVoxelBuildWorld>(GetOwner())) Building->UnregisterSceneStation(this);
    Super::EndPlay(Reason);
}

AVillageGunshopCounter::AVillageGunshopCounter()
{
    bReplicates = true;
    auto* Touch = CreateDefaultSubobject<UBoxComponent>(TEXT("OrderBookAndCounterEdge"));
    SetRootComponent(Touch);
    Touch->InitBoxExtent(FVector(65., 35., 9.5));
    Touch->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Touch->SetCollisionResponseToAllChannels(ECR_Ignore);
    Touch->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Touch->SetGenerateOverlapEvents(false);
    Touch->SetCanEverAffectNavigation(false);

    // Relative to the existing order-book anchor. Keep the stool to his left
    // and leave a clear aisle behind him to the workbench.
    const FVector Feet(-100., 97., -103.);
    auto* ResidentTarget = CreateDefaultSubobject<UBoxComponent>(TEXT("GunsmithTalkTarget"));
    ResidentTarget->SetupAttachment(Touch);
    ResidentTarget->SetRelativeLocation(Feet + FVector(0., 0., 91.));
    ResidentTarget->InitBoxExtent(FVector(25., 21., 90.));
    ResidentTarget->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ResidentTarget->SetCollisionResponseToAllChannels(ECR_Ignore);
    ResidentTarget->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    ResidentTarget->SetGenerateOverlapEvents(false);
    ResidentTarget->SetCanEverAffectNavigation(false);

    ResidentBody = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("GunsmithBody"));
    ResidentHead = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("GunsmithHead"));
    Workwear = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("GunsmithWorkwear"));
    ResidentBody->SetupAttachment(Touch);
    ResidentBody->SetRelativeLocationAndRotation(Feet, FRotator(0., 180., 0.));
    ResidentHead->SetupAttachment(ResidentBody);
    Workwear->SetupAttachment(ResidentBody);
    for (auto* Part : {ResidentBody.Get(), ResidentHead.Get(), Workwear.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);
    }
}

namespace
{
    const FVillageArtisanAppearance GunsmithAppearance{
        FSoftObjectPath(TEXT("/Game/Characters/VillageGunsmith/SK_Gunsmith_Head.SK_Gunsmith_Head")),
        FSoftObjectPath(TEXT("/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Outfit.SK_Smith_Outfit"))};
}

void AVillageGunshopCounter::BeginPlay()
{
    Super::BeginPlay();
    LoadGunsmith();
}

void AVillageGunshopCounter::SetActorHiddenInGame(bool bNewHidden)
{
    Super::SetActorHiddenInGame(bNewHidden);
    if (!bNewHidden && HasActorBegunPlay()) LoadGunsmith();
}

void AVillageGunshopCounter::LoadGunsmith()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    UVillageResidentDetail::Attach(*this,  GunsmithAppearance.Paths(),
        FStreamableDelegate::CreateUObject(this, &ThisClass::DressGunsmith), {ResidentBody.Get(), ResidentHead.Get(), Workwear.Get()});
}

void AVillageGunshopCounter::DressGunsmith()
{
    GunsmithAppearance.Dress(*ResidentBody, *ResidentHead, *Workwear, Facing);
    UResidentHighlightSubsystem::RegisterShopkeeper(*this);
}
