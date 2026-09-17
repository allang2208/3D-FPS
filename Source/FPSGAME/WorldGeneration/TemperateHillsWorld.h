#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "../FPSGAMEGameMode.h"
#include "TemperateHillsSurface.h"
#include "TemperateHillsRiver.h"
#include "TemperateHillsWorld.generated.h"

class UPCGComponent;
class UPCGGraph;
class UBoxComponent;
class UDynamicMeshComponent;
class UStaticMesh;
class USkeletalMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UInstancedStaticMeshComponent;
class ACameraActor;
class UPrimitiveComponent;
class UTexture2D;
class UVolumetricCloudComponent;
struct FTemperateHillsStreamingState;
struct FTemperateBackdropState;
struct FProductionResource;

/** Curated environment references. No level/assembly imports from the source packs. */
UCLASS(BlueprintType)
class FPSGAME_API UTemperateHillsAssets : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UMaterialInterface> GroundMaterial;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UMaterialInterface> ValleyFogMaterial;
    UPROPERTY(EditAnywhere) TSoftClassPtr<AActor> ValleyFogClass;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UStaticMesh> TrunkCollisionMesh;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<USkeletalMesh>> Trees;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UStaticMesh>> Rocks;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UStaticMesh>> Shrubs;
    UPROPERTY(EditAnywhere, Category="Grass") TArray<TSoftObjectPtr<UStaticMesh>> Grass;
    UPROPERTY(EditAnywhere, Category="Grass") TArray<TSoftObjectPtr<UStaticMesh>> GrassAccents;
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="45",ClampMax="200",Units="cm")) float GrassSpacingCm = 55.f;
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="0",ClampMax="1")) float GrassCoverage = .94f;
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="120",ClampMax="500",Units="cm")) float GrassAccentSpacingCm = 180.f;
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="0",ClampMax="1")) float GrassAccentCoverage = .5f;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UPCGGraph>> Graphs;
    UPROPERTY(EditAnywhere, Category="River") TSoftObjectPtr<UMaterialInterface> RiverMaterial;
    UPROPERTY(EditAnywhere, Category="River") TArray<TSoftObjectPtr<UStaticMesh>> RiverRocks;
    UPROPERTY(EditAnywhere, Category="Backdrop") TSoftObjectPtr<UMaterialInterface> BackdropMaterial;
    // Native default also upgrades existing biome assets that predate this field.
    UPROPERTY(EditAnywhere, Category="Sky") TSoftObjectPtr<UMaterialInterface> SkyCloudMaterial =
        TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/Sky/MI_HillsClouds.MI_HillsClouds")));
    UPROPERTY(EditAnywhere, Category="Fog", meta=(ClampMin="0",ClampMax="1")) float ValleyFogDensity = .32f;
};

USTRUCT(BlueprintType)
struct FHillsCraterRecord
{
    GENERATED_BODY()
    UPROPERTY() double X=0;
    UPROPERTY() double Y=0;
    UPROPERTY() double Radius=0;
    UPROPERTY() double Depth=0;
    UPROPERTY() double Rim=0;
};

USTRUCT(BlueprintType)
struct FHillsTerrainEditRecord
{
    GENERATED_BODY()
    UPROPERTY() int32 Type=0;
    UPROPERTY() double X=0;
    UPROPERTY() double Y=0;
    UPROPERTY() double Radius=0;
    UPROPERTY() double HalfX=0;
    UPROPERTY() double HalfY=0;
    UPROPERTY() double Amplitude=0;
    UPROPERTY() double Lip=0;
    UPROPERTY() int32 Seed=0;
};

/** V1 stores the world identity/seed; V2 craters; V3 general terrain edits. */
UCLASS()
class FPSGAME_API UTemperateHillsSave : public USaveGame
{
    GENERATED_BODY()
public:
    // Exposed for maintenance tooling (Tools/WorldGeneration/clean_hills_edits.py).
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Version = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Seed = 122;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FGuid WorldId;
    // Kept so V2 saves still load; new saves write Edits only.
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FHillsCraterRecord> Craters;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FHillsTerrainEditRecord> Edits;
};

struct FTemperatePlacement
{
    FTransform Transform;
    FSoftObjectPath Mesh;
    uint32 Key = 0;
    uint64 CandidateId = 0;
};

UCLASS()
class FPSGAME_API ATemperateHillsWorld : public AActor
{
    GENERATED_BODY()
public:
    ATemperateHillsWorld();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, Category="Hills") TObjectPtr<UTemperateHillsAssets> Assets;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Hills") int32 Seed = 122;
    UPROPERTY(EditAnywhere, Category="Hills", meta=(ClampMin="256",ClampMax="1024")) float SizeMeters = 1024.f;
    UPROPERTY(EditAnywhere, Category="Hills|Streaming", meta=(ClampMin="96",ClampMax="256")) float DetailRadiusMeters = 160.f;
    UPROPERTY(EditAnywhere, Category="Hills|Streaming", meta=(ClampMin="256",ClampMax="512")) float ViewRadiusMeters = 384.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hills") bool bReady = false;
    // Allows the loading camera/pawn and PCG to prepare before gameplay is released.
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hills") bool bSurfaceReady = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hills") FGuid WorldId;
    UFUNCTION(BlueprintPure, Category="Hills") FVector GetStartLocation() const;
    FRotator GetStartRotation() const;
    double Height(double X, double Y) const;
    TemperateRiver::FSample SampleRiver(double X, double Y) const
    { return RiverPlan ? RiverPlan->Sample(X, Y) : TemperateRiver::FSample(); }
    FVector SurfaceNormal(double X, double Y) const;
    /** Generated height before any runtime crater is applied. */
    double BaseHeight(double X, double Y) const;
    /** Signed height delta from all runtime terrain edits (+raised, -dug). */
    double TerrainOffsetAt(double X, double Y) const;
    /** True when any edit still influences this point (bucketed lookup). */
    bool TerrainEditTouchesPoint(double X, double Y) const;
    /** Fireball/dig crater: world-space centre, radius and depth in centimetres. */
    bool ApplyCrater(const FVector& Location, double RadiusCm, double DepthCm, double RimCm);
    /**
     * Grid-aligned shovel edit. Half extents and amplitude are centimetres; a
     * negative amplitude digs down, so every call moves the ground by whole
     * 20 cm layers. Callers snap the centre to the 20 cm world grid.
     */
    bool ApplyTerrainStep(const FVector& Location, double HalfXCm, double HalfYCm, double AmplitudeCm, uint32 Seed);
    /** Right-click refill: raises one 20 cm layer and consumes the shovel's soil. */
    bool ApplySoilRefill(const FVector& Location, FString& OutMessage);
    /** Removes PCG ground cover (grass only, never trees/rocks) inside a radius. */
    int32 DestroyGroundCover(const FVector& Center, double RadiusCm);
    int32 GetTerrainEditCount() const { return TerrainEdits.Num(); }
    void GetPlacements(int32 Layer, const FBox& Bounds, TArray<FTemperatePlacement>& Out, bool IncludeRegrowth=false) const;
    uint32 LayoutHash(int32 Layer) const;
    FString ProductionResourceId(int32 Layer,uint64 Candidate) const;
    bool IsProductionDepleted(int32 Layer,uint64 Candidate) const;
    void GetHarvestedStumps(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const;
    bool ResolveProductionResource(const FHitResult& Hit,FProductionResource& Resource,FString& Reason) const;
    void CompleteProductionHarvest(const FProductionResource& Resource,const FHitResult& Hit,const FVector& Direction);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<UBoxComponent> GenerationBounds;
    UPROPERTY() TArray<TObjectPtr<UPCGComponent>> PCGLayers;
    UPROPERTY() TArray<TObjectPtr<UDynamicMeshComponent>> Terrain;
    UPROPERTY() TArray<TObjectPtr<AActor>> ValleyFog;
    UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> FogMaterials;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> GroundMID;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BackdropMID;
    UPROPERTY() TObjectPtr<UTexture2D> BackdropColor;
    UPROPERTY() TObjectPtr<UTexture2D> BackdropCoverage;
    UPROPERTY() TArray<TObjectPtr<UDynamicMeshComponent>> BackdropMeshes;
    UPROPERTY() TObjectPtr<UVolumetricCloudComponent> HillsClouds;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Trunks;
    UPROPERTY() TObjectPtr<ACameraActor> AuditCamera;
    UPROPERTY() TArray<TObjectPtr<UPrimitiveComponent>> WarmupComponents;
    FString Slot;
    FString AuditDir;
    bool bAudit = false;
    bool bNullAudit = false;
    bool bAuditPassed = true;
    int32 AuditStage = 0;
    double AuditNext = 0;
    double StartSeconds = 0;
    TSharedPtr<FTemperateHillsStreamingState> Streaming;
    TSharedPtr<FTemperateBackdropState> Backdrop;
    TemperateRiver::FPlanPtr RiverPlan;
    TArray<double> FrameSamples;
    double Noise(double X, double Y, uint32 Salt) const;
    double PathDistance(double X, double Y) const;
    double ForestWeight(double X, double Y) const;
    bool TreeCandidate(int32 GX, int32 GY, FTemperatePlacement& Out) const;
    void GetGrassPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    void BeginStreaming();
    void TickStreaming();
    void EndStreaming();
    void LoadNextEnvironmentStage();
    void TickPreparation();
    void ActivateVegetationLayer(int32 Layer);
    void BuildValleyFog();
    void TickBackdrop();
    void BeginSkyClouds();
    void ActivateSkyClouds();
    bool IsBackdropReady() const;
    void SetBackdropCellVisible(FIntPoint Cell, bool Visible);
    void EndBackdrop();
    void ResolveSession();
    void RunAudit();
    void InvalidateTerrainCells(const FVector2D& Center, double Radius);
    void PersistTerrainEdits();
    void AddTerrainEdit(const TemperateHillsSurface::FTerrainEdit& Edit);
    /** Coarse spatial index (bucket -> indices into TerrainEdits), rebuilt on every change. */
    void RebuildEditBuckets();
    /** Clears PCG ground cover inside one edit's footprint. */
    int32 ClearCoverForEdit(const TemperateHillsSurface::FTerrainEdit& Edit);
    bool IsGroundCoverMesh(const class UStaticMesh* Mesh) const;
    TArray<TemperateHillsSurface::FTerrainEdit> TerrainEdits;
    TMap<int64, TArray<int32>> EditBuckets;
    double NextCoverSweep = 0;
    void AuditCheck(bool Pass, const TCHAR* Message);
};

UCLASS()
class FPSGAME_API ATemperateHillsGameMode : public AFPSGAMEGameMode
{
    GENERATED_BODY()
public:
    virtual void RestartPlayer(AController* NewPlayer) override;
};
