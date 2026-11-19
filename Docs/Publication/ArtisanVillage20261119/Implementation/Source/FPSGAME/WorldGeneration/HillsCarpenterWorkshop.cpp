#include "HillsCarpenterWorkshop.h"
#include "HillsBlacksmith.h"
#include "VillageShopFacing.h"

#include "TemperateHillsWorld.h"
#include "../Building/VoxelBuildWorld.h"
#include "../NPC/VillageCarpenterResident.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"

namespace
{
void UpdateCrystalDrive(UStaticMeshComponent* Body, bool bAvailable)
{
    static const FName CrystalCore(TEXT("CrystalCore"));
    static const FName DriveStrength(TEXT("DriveStrength"));
    const int32 Slot = Body->GetMaterialIndex(CrystalCore);
    if (Slot == INDEX_NONE) return;
    UMaterialInterface* Surface = Body->GetMaterial(Slot);
    float Strength = 0.f;
    if (!Surface || !Surface->GetScalarParameterValue(FMaterialParameterInfo(DriveStrength), Strength)) return;
    // Repeated world/actor notifications must preserve the working saw's brighter drive.
    if (bAvailable == (Strength > 0.f)) return;
    UMaterialInstanceDynamic* Crystal = Cast<UMaterialInstanceDynamic>(Surface);
    if (!Crystal) Crystal = Body->CreateDynamicMaterialInstance(Slot);
    if (Crystal) Crystal->SetScalarParameterValue(DriveStrength, bAvailable ? 1.f : 0.f);
}
}

AHillsCarpenterWorkshop::AHillsCarpenterWorkshop()
{
    bAlwaysRelevant = true;
    const FVector OriginalFeet(45., 205., 1.47);
    ResidentPose = FTransform(FVector(-OriginalFeet.X, -OriginalFeet.Y, 0.).Rotation(), OriginalFeet);
}

void AHillsCarpenterWorkshop::BeginPlay()
{
    Super::BeginPlay();
    // The level mesh can be visible before the world and its replicated station bind.
    if (GetNetMode() != NM_DedicatedServer) UpdateCrystalDrive(Body(), IsSceneStationAvailable());
    BindVillage();
}

void AHillsCarpenterWorkshop::BindVillage()
{
    if (!Hills.IsValid())
        for (TActorIterator<ATemperateHillsWorld> It(GetWorld()); It; ++It)
        {
            Hills = *It;
            break;
        }
    if (HasAuthority() && !GetOwner())
        for (TActorIterator<AVoxelBuildWorld> It(GetWorld()); It; ++It)
            if (It->IsReady())
            {
                SetOwner(*It);
                break;
            }
    if (Hills.IsValid() && GetOwner())
    {
        GetWorldTimerManager().ClearTimer(BindTimer);
        ApplyVillageState();
        return;
    }
    GetWorldTimerManager().SetTimer(BindTimer, this, &AHillsCarpenterWorkshop::BindVillage, 1.f, false);
}

bool AHillsCarpenterWorkshop::IsSceneStationAvailable() const
{
    return Hills.IsValid() && Hills->IsVillageCarpenterRepaired() && PrefabId() == VoxelWoodworkingBenchId && !IsFalling();
}

void AHillsCarpenterWorkshop::RefreshRegistration()
{
    const bool bAvailable = IsSceneStationAvailable();
    if (GetNetMode() != NM_DedicatedServer) UpdateCrystalDrive(Body(), bAvailable);
    if (auto* Building = Cast<AVoxelBuildWorld>(GetOwner()))
    {
        if (bAvailable) Building->RegisterSceneStation(this);
        else Building->UnregisterSceneStation(this);
    }
}

void AHillsCarpenterWorkshop::ApplyVillageState()
{
    if (!Hills.IsValid()) return;
    const bool Repaired = Hills->IsVillageCarpenterRepaired();
    for (const auto& Assembly : ShopAssemblies)
    {
        if (!IsValid(Assembly.Get())) continue;
        TInlineComponentArray<UPointLightComponent*> Lamps(Assembly.Get());
        for (UPointLightComponent* Lamp : Lamps)
            if (Lamp->ComponentHasTag(TEXT("VillageCarpenter.Repaired")))
                Lamp->SetVisibility(Repaired);
        TInlineComponentArray<UPrimitiveComponent*> Parts(Assembly.Get());
        for (UPrimitiveComponent* Part : Parts)
        {
            const bool Ruin = Part->ComponentHasTag(TEXT("VillageCarpenter.Ruined"));
            if (!Ruin && !Part->ComponentHasTag(TEXT("VillageCarpenter.Repaired"))) continue;
            const bool Visible = Ruin != Repaired;
            Part->SetVisibility(Visible);
            Part->SetHiddenInGame(!Visible);
            Part->SetCollisionEnabled(Visible && !Part->ComponentHasTag(TEXT("VillageCarpenter.NoCollision"))
                ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
        }
    }
    if (HasAuthority() && GetOwner())
    {
        const FVector P = GetActorLocation() / 20.;
        const FIntVector StationCell(FMath::FloorToInt(P.X), FMath::FloorToInt(P.Y), FMath::FloorToInt(P.Z));
        const FName DesiredId = Repaired ? VoxelWoodworkingBenchId : NAME_None;
        // Reapplying scenery after replication must not restart an active table saw.
        if (PrefabId() != DesiredId || NetMesh != StationMesh || AnchorCell() != StationCell)
        {
            Configure(DesiredId, StationCell, 0, StationMesh, nullptr, nullptr);
            ForceNetUpdate();
        }
        UpdateResident(Repaired);
    }
    Body()->SetReceivesDecals(false);
    RefreshRegistration();
}

void AHillsCarpenterWorkshop::UpdateResident(bool bRepaired)
{
    if (!bRepaired)
    {
        if (Resident.IsValid()) Resident->Destroy();
        Resident.Reset();
        return;
    }
    if (Resident.IsValid()) return;

    FActorSpawnParameters Spawn;
    Spawn.Owner = this;
    Spawn.OverrideLevel = GetLevel();
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    FTransform StandingPose = ResidentPose * GetActorTransform();
    StandingPose.AddToTranslation(FVector::UpVector * AVillageCarpenterResident::CapsuleHalfHeight * StandingPose.GetScale3D().Z);
    // The carpenter's bench is rotated -90 degrees in the house frame; its +X points out of the shop.
    VillageShop::FaceAcrossStreet<AHillsBlacksmith>(*this, GetActorForwardVector(), StandingPose);
    Resident = GetWorld()->SpawnActor<AVillageCarpenterResident>(
        AVillageCarpenterResident::StaticClass(), StandingPose, Spawn);
}

bool AHillsCarpenterWorkshop::RepairAreaOccupied() const
{
    return GetWorld()->OverlapAnyTestByObjectType(GetActorTransform().TransformPosition(RepairAreaCenter),
        GetActorQuat(), FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeBox(RepairAreaHalfExtent),
        FCollisionQueryParams(SCENE_QUERY_STAT(VillageCarpenterRepair), false, this));
}

void AHillsCarpenterWorkshop::OnRep_Configuration()
{
    Super::OnRep_Configuration();
    RefreshRegistration();
}

void AHillsCarpenterWorkshop::OnRep_Owner()
{
    Super::OnRep_Owner();
    if (HasActorBegunPlay()) BindVillage();
}

void AHillsCarpenterWorkshop::EndPlay(const EEndPlayReason::Type Reason)
{
    if (HasAuthority()) UpdateResident(false);
    GetWorldTimerManager().ClearTimer(BindTimer);
    if (auto* Building = Cast<AVoxelBuildWorld>(GetOwner())) Building->UnregisterSceneStation(this);
    Super::EndPlay(Reason);
}

bool ATemperateHillsWorld::CompleteVillageCarpenterRepair(FText& FailureReason)
{
    FailureReason = FText::GetEmpty();
    if (!HasAuthority() || Slot.IsEmpty() || !WorldId.IsValid() || !VillageSite.bPlaced)
    {
        FailureReason = FText::FromString(TEXT("村庄尚未准备好修复木工工坊。"));
        return false;
    }
    if (IsVillageCarpenterRepaired()) return true;
    TActorIterator<AHillsCarpenterWorkshop> Shop(GetWorld());
    const auto* Building = Shop ? Cast<AVoxelBuildWorld>(Shop->GetOwner()) : nullptr;
    if (!Building || !Shop->StationMesh)
    {
        FailureReason = FText::FromString(TEXT("木工工坊还未准备好，请稍后重试。"));
        return false;
    }
    if (Shop->RepairAreaOccupied())
    {
        FailureReason = FText::FromString(TEXT("请让人员和动物离开木工工坊和作业院，再完成修复。"));
        return false;
    }
    if (Building->HasPrefabAt(Shop->AnchorCell()))
    {
        FailureReason = FText::FromString(TEXT("木工工作台的位置被建造构件占用，请移开后再修复。"));
        return false;
    }
    return CommitVillagePlanRepair(UTemperateHillsSave::CarpenterPlan, 3, TEXT("木工工坊修复未能保存，请重试。"), FailureReason);
}
