#pragma once
#include "TemperateHillsWorld.h"
#include "TemperateHillsFixedLayout.h"
#include "TemperateQuarryFixedDressing.h"
#include "Async/Future.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "RenderCommandFence.h"
class UDynamicMeshComponent;
class UInstancedStaticMeshComponent;
class ULevelStreamingDynamic;
class UTemperateHillsGuestSource;
class UTexture2D;
struct FStreamableHandle;
class UTransitLoadingSubsystem;
namespace HillsStreaming
{
void AcquireStreamingBudget();
void FinishEntryBudgetIfReady(bool& Preparing,bool Ready,bool Failed,const UTransitLoadingSubsystem* Loading);
constexpr double CellSize=6400.0;
constexpr int32 SurfaceDetailQuads=64;
// Entry only waits for this playable neighborhood. The normal view ring starts
// streaming after release, with the existing two terrain jobs / one mesh per frame.
constexpr double EntryRadius=3200.0;
constexpr double EntryVegetationRadius=1600.0;
enum EAssetBatch { Solids, Understory, GroundCover, Atmosphere, BatchCount };

struct FMeshResult
{
    FIntPoint Key;
    bool Detailed=false;
    UE::Geometry::FDynamicMesh3 Mesh;
    UE::Geometry::FDynamicMesh3 Water;
    UE::Geometry::FDynamicMesh3 Ponds;
};
struct FJob
{
    FIntPoint Key;
    uint32 EditRevision=0;
    TFuture<TSharedPtr<FMeshResult,ESPMode::ThreadSafe>> Future;
};
struct FCell
{
    TWeakObjectPtr<UDynamicMeshComponent> Mesh;
    TWeakObjectPtr<UDynamicMeshComponent> Pending;
    TWeakObjectPtr<UInstancedStaticMeshComponent> Trunks;
    TWeakObjectPtr<UDynamicMeshComponent> Water;
    TWeakObjectPtr<UDynamicMeshComponent> Ponds;
    bool Detailed=false;
    bool PendingDetailed=false;
    // Set when a runtime crater landed in this cell: the live mesh stays until a
    // replacement is cooked, then the cell is rebuilt from the new crater list.
    bool Dirty=false;
};

void SetCellMesh(UDynamicMeshComponent* Component,UE::Geometry::FDynamicMesh3&& Mesh,TConstArrayView<TObjectPtr<UPCGComponent>> VegetationLayers);
double CellDistanceSquared(const FVector& Point,const FVector& Origin);
void CountVegetationCells(UPCGComponent* Component,FVector Center,double Radius,double Half,int32& Required,int32& Complete);
TSharedPtr<FMeshResult,ESPMode::ThreadSafe> MakeMesh(FIntPoint Key,bool Detailed,double Half,int32 Seed,TemperateRiver::FPlanPtr River,const TArray<TemperateHillsSurface::FTerrainEdit>& Edits,int32 Version,TemperateForestWater::FPlanPtr ForestWater,FTemperateChapelSite Chapel,FTemperateVillageSite Village);
}
struct FTemperateHillsStreamingState
{
    TWeakObjectPtr<ULevelStreamingDynamic> VillageLevel;
    TMap<FIntPoint,HillsStreaming::FCell> Cells;
    TArray<HillsStreaming::FJob> Jobs;
    TFuture<TemperateHillsFixedLayout::FLayout> RiverJob;
    uint32 FixedLayoutChecksum=0;
    bool RiverPending=false;
    enum class EQuarryStage : uint8 { Idle, Loading, RockLayout, Collision, Dressing, Details, Complete, Failed };
    struct FQuarryAssembly
    {
        EQuarryStage Stage=EQuarryStage::Idle;
        bool Requested=false;
        bool UsingFixedDressing=false;
        TFuture<TemperateQuarryFixedDressing::FLayoutPtr> FixedDressingJob;
        int32 NextSection=0;
        TSharedPtr<FStreamableHandle> Handle;
        TArray<FSoftObjectPath> Paths;
        TMap<FSoftObjectPath,TArray<FTransform>> Groups;
        TMap<FIntPoint,double> GroundVertices;
        FSoftObjectPath ActiveMesh;
        TWeakObjectPtr<UInstancedStaticMeshComponent> ActiveComponent;
        int32 NextInstance=0;
        int32 InstanceCount=0;
        bool HasBlockers() const {return Stage>=EQuarryStage::Collision&&Stage!=EQuarryStage::Failed;}
        bool HasCollision() const {return Stage>=EQuarryStage::Dressing&&Stage!=EQuarryStage::Failed;}
    } Quarry;
    TFuture<TemperateRiver::FPlanPtr> VillageBiomeJob;
    bool VillageBiomePending=false;
    using FWaterPlans=TTuple<TemperateForestWater::FPlanPtr,TemperateForestWater::FPlanPtr>;
    TFuture<FWaterPlans> ForestWaterJob;
    bool ForestWaterPending=false;
    uint32 ForestWaterRevision=0;
    TArray<TSharedPtr<FStreamableHandle>> Handles;
    TSharedPtr<FStreamableHandle> SmithAppearance;
    TSharedPtr<FStreamableHandle> CarpenterAppearance;
    TArray<TWeakObjectPtr<UTexture2D>> GroundTextures;
    TMap<int32,TWeakObjectPtr<AActor>> Fog;
    // River mist keyed by centreline point index; separate lifecycle/density.
    TMap<int32,TWeakObjectPtr<AActor>> RiverFog;
    struct FSurfaceHold
    {
        EMovementMode ResumeMode=MOVE_Falling;
        FIntPoint WaitCell;
        FIntPoint PawnCell;
    };
    TMap<TWeakObjectPtr<ACharacter>,FSurfaceHold> HeldPawns;
    TMap<TWeakObjectPtr<APlayerController>,TWeakObjectPtr<UTemperateHillsGuestSource>> GuestSources;
#if !UE_BUILD_SHIPPING
    TWeakObjectPtr<ACharacter> Visitor;
    FIntPoint VisitCell=FIntPoint::ZeroValue;
    FVector2D VisitTarget=FVector2D::ZeroVector;
    FVector2D VisitFocus=FVector2D::ZeroVector;
    bool bVillageVisit=false;
    bool bWhiteCliffsVisit=false;
    void StageVisit(ACharacter* Player,FVector2D Target,FVector2D Focus,double Half)
    {
        VisitTarget={FMath::Clamp(Target.X,-Half+150.,Half-150.),FMath::Clamp(Target.Y,-Half+150.,Half-150.)};
        VisitFocus=Focus;
        VisitCell={FMath::FloorToInt32((VisitTarget.X+Half)/HillsStreaming::CellSize),
                   FMath::FloorToInt32((VisitTarget.Y+Half)/HillsStreaming::CellSize)};
        Visitor=Player;
    }
#endif
    bool StaggerVillageEntry=false;
    TWeakObjectPtr<class ALandscapeProxy> ForestLandscape;
    TWeakObjectPtr<class AForestVillageRegion> ForestRegion;
    int32 ForestPSOActorIndex=0;
    TArray<TWeakObjectPtr<UPrimitiveComponent>> ForestPendingPSOs;
    TArray<double> ForestBorderHeights;
    TArray<float> ForestVillageGroundCm;
    bool GroundReady=false;
    bool LoadingAssets=false;
    bool TreesActive=false;
    bool FogReady=false;
    bool Stopping=false;
    bool Failed=false;
    bool PreparingBudget=true;
    bool EntryCleanupRequested=false;
    double EntryCleanupGCTime=0;
    double NextSurfaceWaitLog=0;
    struct FAssetBatch
    {
        bool Requested=false,Loaded=false,Ready=false;
        int32 Submitted=0, Finished=0;
        TArray<FSoftObjectPath> Paths;
        TSharedPtr<FStreamableHandle> Handle;
#if WITH_EDITOR
        int32 NextCompilationPath=0;
#endif
        double NextWaitLog=0;
    };
    FAssetBatch Batches[HillsStreaming::BatchCount];
    int32 CompletedStages=0;
    bool LayerActive[4]={};
    int32 WarmupAsset=0;
    int32 SettledFrames=0;
    int32 InitialPCGTotal=0;
    int32 InitialPCGReady=0;
    int32 RetainedHandleCount=0;
    TArray<TWeakObjectPtr<UObject>> WarmupMeshes;
    bool WarmupRemoved=false;
    FRenderCommandFence RenderFence;
    double TextureWaitStart=0;
    double NextGroundResidencyRefresh=0;
    double GroundMaterialIdleWaitStart=0;
    bool GroundTexturesCollected=false;
    bool GroundMaterialReadinessLogged=false;
    bool GroundTextureReadinessLogged=false;
    double NextFogTime=0;
    double NextVegetationFrontierTime=0;
    double NextEntryProgressLog=0;
    TArray<FIntPoint,TInlineAllocator<9>> SpawnCells;
    TSet<TWeakObjectPtr<AController>> WaitingToSpawn;
    // Neighbouring PCG jobs query overlapping, already-fitted rock fields.
    // These windows belong to this streamed world and contain no live instances.
    struct FRockWindow
    {
        FBox Area=FBox(ForceInit);
        TArray<FTemperatePlacement> Rocks;
        uint64 LastUse=0;
    };
    struct FRockFit
    {
        uint64 Id=0;
        int32 Seed=0;
        uint32 Revision=0;
        TWeakObjectPtr<const UStaticMesh> Mesh;
        FTransform Input,Output;
        bool Supported=false;
    };
    TArray<FRockFit> RockFits;
    TArray<FRockWindow> VegetationRockWindows;
    // The quarry is assembled once; adjacent vegetation windows can reuse its
    // exact solid placements until a terrain edit changes their support.
    TArray<TemperateQuarryFixedDressing::FBlocker> QuarryBlockers;
    uint32 QuarryBlockerRevision=0;
    uint32 RockWindowRevision=0;
    int32 ReadySpawnCellCount() const
    {
        int32 Ready=0;
        for(const FIntPoint& Key:SpawnCells)
            if(const auto* Cell=Cells.Find(Key);Cell&&Cell->Mesh.IsValid()&&Cell->Detailed&&!Cell->Dirty&&!Cell->Pending.IsValid())++Ready;
        return Ready;
    }
};

#if !UE_BUILD_SHIPPING
bool LandAtVisitTarget(ATemperateHillsWorld& Hills,FTemperateHillsStreamingState& S,UDynamicMeshComponent* Ground,ACharacter& Player);
#endif
