#include "VillageResidentDetail.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ArtisanDefenseComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillagePresentationView.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"

namespace
{
static float GResidentRTDistCm = 1800.f;
static FAutoConsoleVariableRef CVarResidentRTDistCm(
    TEXT("fps.Hills.ResidentRayTracingDistCm"),
    GResidentRTDistCm,
    TEXT("Max camera distance (cm, +300 cm hysteresis) for village residents to stay visible in Ray Tracing. <= 0 keeps RT always on."),
    ECVF_Default);

// Only a solid stationary surface counts as shelter. Transparent shopfronts,
// an open door or a gap between modules must let the appearance request through.
bool SolidCover(UWorld& World, const FVector& Eye, const FVector& End, const FCollisionQueryParams& Query)
{
    FHitResult Hit;
    if (!World.LineTraceSingleByChannel(Hit, Eye, End, ECC_Visibility, Query)) return false;
    auto* Wall = Cast<UStaticMeshComponent>(Hit.GetComponent());
    if (!Wall || Wall->Mobility == EComponentMobility::Movable || Wall->GetNumMaterials() == 0) return false;
    for (int32 I = 0; I < Wall->GetNumMaterials(); ++I)
        if (auto* Mat = Wall->GetMaterial(I); !Mat || Mat->GetBlendMode() != BLEND_Opaque) return false;
    return true;
}

bool CanSeeShop(UWorld& World, const AActor& Owner, const FVector& Feet)
{
    for (auto It = World.GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = It->Get();
        if (!PC || !PC->IsLocalController() || !PC->PlayerCameraManager) continue;
        auto* View = PC->PlayerCameraManager.Get();
        const FVector Eye = View->GetCameraLocation();
        const FVector ToShop = Feet - Eye;
        if (FVector::DotProduct(View->GetCameraRotation().Vector(), ToShop.GetSafeNormal()) < .10) continue;
        const FVector Side = FVector::CrossProduct(ToShop.GetSafeNormal2D(), FVector::UpVector) * 95.;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageShopSight), true, &Owner);
        Query.AddIgnoredActor(PC->GetPawn());
        if (!SolidCover(World, Eye, Feet + FVector(0,0,180), Query) ||
            !SolidCover(World, Eye, Feet + FVector(0,0,70) + Side, Query) ||
            !SolidCover(World, Eye, Feet + FVector(0,0,70) - Side, Query)) return true;
    }
    return false;
}
}

UVillageResidentDetail::UVillageResidentDetail()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickInterval = .25f;
}

void UVillageResidentDetail::Attach(AActor& Owner, TArray<FSoftObjectPath> Assets, FSimpleDelegate Dress,
    std::initializer_list<USkeletalMeshComponent*> Parts, FSimpleDelegate Release)
{
    if (Owner.GetNetMode() == NM_DedicatedServer) return;
    if (auto* Existing = Owner.FindComponentByClass<UVillageResidentDetail>())
    {
        Existing->Refresh();
        return;
    }
    auto* Detail = NewObject<UVillageResidentDetail>(&Owner, NAME_None, RF_Transient);
    Detail->Paths = MoveTemp(Assets);
    Detail->ApplyAppearance = MoveTemp(Dress);
    Detail->ReleaseAppearance = MoveTemp(Release);
    for (auto* Part : Parts)
    {
        Detail->Meshes.Add(Part);
        Detail->OriginalTickOptions.Add(uint8(Part->VisibilityBasedAnimTickOption));
    }
    Owner.AddInstanceComponent(Detail);
    Detail->RegisterComponent();
    Detail->Refresh();
}

void UVillageResidentDetail::UpdateRayTracingVisibility(bool bVisible)
{
    if (bRTVisible == bVisible) return;
    bRTVisible = bVisible;
    for (int32 I = 0; I < Meshes.Num(); ++I)
        if (auto* Mesh = Meshes[I].Get())
            Mesh->SetVisibleInRayTracing(bVisible);
}

void UVillageResidentDetail::ReducePoseWork(bool bReduce)
{
    if (bReduced == bReduce) return;
    bReduced = bReduce;
    for (int32 I = 0; I < Meshes.Num(); ++I)
        if (auto* Mesh = Meshes[I].Get())
        {
            Mesh->bEnableUpdateRateOptimizations = bReduce;
            Mesh->VisibilityBasedAnimTickOption = bReduce ? EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered :
                EVisibilityBasedAnimTickOption(OriginalTickOptions[I]);
        }
}

void UVillageResidentDetail::Refresh()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(VillageResident_RefreshAppearance);
    auto* Owner = GetOwner();
    auto* World = GetWorld();
    if (!Owner || !World || Meshes.IsEmpty() || !Meshes[0].IsValid()) return;
    const auto* Body = Meshes[0].Get();
    const double Now = World->GetTimeSeconds();
    bool bHasCamera = false;
    const double Distance = VillagePresentationView::Distance(*World, Body->GetComponentLocation(), 0., &bHasCamera);
    const auto* Defense = Owner->FindComponentByClass<UArtisanDefenseComponent>();
    // Active guard actions need authoritative sockets even for offscreen raids.
    // Prewarm idle guards for approaching remote players independently of the host camera.
    bool bGameplayPose = Defense && !Defense->IsAtWork();
    if (Defense && !bGameplayPose && Owner->GetNetMode() == NM_ListenServer)
        for (auto It = World->GetPlayerControllerIterator(); It; ++It)
        {
            const auto* PC = It->Get();
            const auto* Pawn = PC && !PC->IsLocalController() ? PC->GetPawn().Get() : nullptr;
            if (Pawn && FVector::DistSquared(Pawn->GetActorLocation(), Owner->GetActorLocation()) <= FMath::Square(3600.))
            {
                bGameplayPose = true;
                break;
            }
        }
    // Distance includes active optical magnification. A shadow or an unobstructed
    // view from across the hills must not pin a full-size shopkeeper indefinitely.
    const bool bBeyondDetail = bHasCamera && Distance > 12500.;
    const bool bInView = !bBeyondDetail && Body->GetSkeletalMeshAsset() && Body->WasRecentlyRendered(1.25f);
    if (!bHasCamera && !bGameplayPose && !Load) return;
    const bool bSheltered = !bHasCamera || bBeyondDetail || (Distance > 3600. && !bGameplayPose && !bInView &&
        !CanSeeShop(*World, *Owner, Body->GetComponentLocation()));
    const bool bNear = !Owner->IsHidden() && !bSheltered;
    if (bNear || bGameplayPose || bInView) LastNeeded = Now;
    ReducePoseWork(!bGameplayPose && (Owner->IsHidden() || !bHasCamera || Distance > 1400.));
    const bool bWantRT = GResidentRTDistCm <= 0.f
        || (!Owner->IsHidden() && bHasCamera && Distance <= (bRTVisible ? (double(GResidentRTDistCm) + 300.) : double(GResidentRTDistCm)));
    UpdateRayTracingVisibility(bWantRT);
    if ((bNear || bGameplayPose) && !Load)
        Load = ATemperateHillsWorld::RequestResidentAppearance(World, Paths, ApplyAppearance);
    if (Load && !bGameplayPose && !bInView && (Owner->IsHidden() || bSheltered) && Now - LastNeeded > 12.)
    {
        Load->CancelHandle();
        Load.Reset();
        ReleaseAppearance.ExecuteIfBound();
        for (auto& Weak : Meshes)
            if (auto* Mesh = Weak.Get())
            {
                Mesh->SetLeaderPoseComponent(nullptr);
                Mesh->SetSkeletalMeshAsset(nullptr);
            }
    }
}

void UVillageResidentDetail::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime, TickType, TickFunction);
    Refresh();
}

void UVillageResidentDetail::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Load) Load->CancelHandle();
    Load.Reset();
    Super::EndPlay(Reason);
}
