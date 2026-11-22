#include "HillsHerbalistWorkshop.h"

#include "TemperateHillsWorld.h"
#include "VillageShopTorches.h"
#include "VillageInteriorLighting.h"
#include "../Building/VoxelBuildWorld.h"
#include "../NPC/VillageHerbalist.h"
#include "Components/PrimitiveComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"

namespace
{
const FName PotionWorkbenchId(TEXT("potion_workbench"));
const FName RuinedTag(TEXT("VillageHerbalist.Ruined"));
const FName RepairedTag(TEXT("VillageHerbalist.Repaired"));
const FName NoCollisionTag(TEXT("VillageHerbalist.NoCollision"));
}

AHillsHerbalistWorkshop::AHillsHerbalistWorkshop()
{
    bAlwaysRelevant = true;
}

FIntVector AHillsHerbalistWorkshop::StationCell() const
{
    const FVector Grid = GetActorLocation() / 20.;
    return FIntVector(FMath::FloorToInt(Grid.X), FMath::FloorToInt(Grid.Y), FMath::FloorToInt(Grid.Z));
}

void AHillsHerbalistWorkshop::BeginPlay()
{
    Super::BeginPlay();
    BindVillage();
}

void AHillsHerbalistWorkshop::BindVillage()
{
    if (!Hills.IsValid())
    {
        TActorIterator<ATemperateHillsWorld> It(GetWorld());
        if (It) Hills = *It;
    }
    if (HasAuthority() && !GetOwner())
    {
        for (TActorIterator<AVoxelBuildWorld> It(GetWorld()); It; ++It)
            if (It->IsReady())
            {
                SetOwner(*It);
                break;
            }
    }
    ApplyVillageState();
    if (Hills.IsValid() && GetOwner())
        GetWorldTimerManager().ClearTimer(BindTimer);
    else
        GetWorldTimerManager().SetTimer(BindTimer, this, &AHillsHerbalistWorkshop::BindVillage, 1.f, false);
}

bool AHillsHerbalistWorkshop::IsSceneStationAvailable() const
{
    return Hills.IsValid() && Hills->IsHerbalistRepaired() && PrefabId() == PotionWorkbenchId && !IsFalling();
}

void AHillsHerbalistWorkshop::RefreshStation()
{
    const bool bAvailable = IsSceneStationAvailable();
    SetActorHiddenInGame(!bAvailable);
    SetActorEnableCollision(bAvailable);
    if (auto* Building = Cast<AVoxelBuildWorld>(GetOwner()))
    {
        if (bAvailable) Building->RegisterSceneStation(this);
        else Building->UnregisterSceneStation(this);
    }
}

void AHillsHerbalistWorkshop::ApplyVillageState()
{
    const bool bRepaired = Hills.IsValid() && Hills->IsHerbalistRepaired();
    for (const auto& Assembly : ShopAssemblies)
    {
        if (!IsValid(Assembly.Get())) continue;
        TInlineComponentArray<USceneComponent*> Parts(Assembly.Get());
        for (USceneComponent* Part : Parts)
        {
            const bool bRuinedPart = Part->ComponentHasTag(RuinedTag);
            if (!bRuinedPart && !Part->ComponentHasTag(RepairedTag)) continue;
            const bool bVisible = bRuinedPart != bRepaired;
            if (bRepaired && bVisible)
                UVillageInteriorLighting::ApplyAppearance(Cast<UPointLightComponent>(Part));
            Part->SetVisibility(bVisible);
            Part->SetHiddenInGame(!bVisible);
            if (UPrimitiveComponent* Primitive = Cast<UPrimitiveComponent>(Part))
            {
                Primitive->SetCollisionEnabled(bVisible && !Part->ComponentHasTag(NoCollisionTag)
                    ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
            }
        }
    }
    if (HasAuthority() && Hills.IsValid() && GetOwner())
    {
        const FName DesiredId = bRepaired ? PotionWorkbenchId : NAME_None;
        const FIntVector WorkbenchCell = StationCell();
        if (PrefabId() != DesiredId || AnchorCell() != WorkbenchCell || NetMesh != StationMesh)
        {
            Configure(DesiredId, WorkbenchCell, 0, StationMesh, nullptr, nullptr);
            ForceNetUpdate();
        }
        UpdateResident(bRepaired);
    }
    RefreshStation();
    VillageShopTorches::Apply(*this,VillageShopTorches::EShop::Herbalist,bRepaired);
}

void AHillsHerbalistWorkshop::UpdateResident(bool bRepaired)
{
    if (!bRepaired)
    {
        if (Resident.IsValid()) Resident->Destroy();
        Resident.Reset();
        return;
    }
    if (Resident.IsValid()) return;

    // Plot 03 uses the bench pivot at (37,302,-1). Stand at (205,-88,0) on the
    // shop floor, near the open end of the dispensing counter, facing the aisle.
    const FTransform StandingPoint(FRotator(0., 180., 0.), FVector(168., -390., 1.));
    FActorSpawnParameters Spawn;
    Spawn.Owner = this;
    Spawn.OverrideLevel = GetLevel();
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Resident = GetWorld()->SpawnActor<AVillageHerbalist>(
        AVillageHerbalist::StaticClass(), StandingPoint * GetActorTransform(), Spawn);
}

bool AHillsHerbalistWorkshop::CanRepair(FText& FailureReason) const
{
    const auto* Building = Cast<AVoxelBuildWorld>(GetOwner());
    if (!Hills.IsValid() || !StationMesh || !Building || !Building->IsReady())
    {
        FailureReason = FText::FromString(TEXT("草药铺还未准备好，请稍后重试。"));
        return false;
    }
    const FTransform& Pose = GetActorTransform();
    if (GetWorld()->OverlapAnyTestByObjectType(Pose.TransformPosition(RepairAreaCenter), GetActorQuat(),
        FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeBox(RepairAreaHalfExtent * Pose.GetScale3D().GetAbs()),
        FCollisionQueryParams(SCENE_QUERY_STAT(VillageHerbalistRepair), false, this)))
    {
        FailureReason = FText::FromString(TEXT("请让人员和动物离开草药铺，再完成修复。"));
        return false;
    }
    if (Building->HasPrefabAt(StationCell()))
    {
        FailureReason = FText::FromString(TEXT("药水工作台的位置被建造构件占用，请移开后再修复。"));
        return false;
    }
    return true;
}

void AHillsHerbalistWorkshop::OnRep_Configuration()
{
    Super::OnRep_Configuration();
    RefreshStation();
}

void AHillsHerbalistWorkshop::OnRep_Owner()
{
    Super::OnRep_Owner();
    if (HasActorBegunPlay()) BindVillage();
}

void AHillsHerbalistWorkshop::EndPlay(const EEndPlayReason::Type Reason)
{
    if (HasAuthority()) UpdateResident(false);
    GetWorldTimerManager().ClearTimer(BindTimer);
    if (auto* Building = Cast<AVoxelBuildWorld>(GetOwner())) Building->UnregisterSceneStation(this);
    Super::EndPlay(Reason);
}
