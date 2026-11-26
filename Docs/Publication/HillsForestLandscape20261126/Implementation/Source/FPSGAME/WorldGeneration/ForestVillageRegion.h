#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TemperateForestWater.h"
#include "ForestVillageRegion.generated.h"

class ALandscapeProxy;
class UInstancedStaticMeshComponent;
class UMaterialFunction;
class UMaterialInterface;
class UMaterial;
class UMaterialExpression;
class AForestGrassCell;
struct FPCGContext;
class UPCGGraph;
class UStaticMesh;

class UDynamicMeshComponent;

USTRUCT()
struct FForestVillagePoolSite
{
    GENERATED_BODY()
    UPROPERTY() FIntPoint OriginM = FIntPoint::ZeroValue;
    UPROPERTY() double WaterZ = 0.;
    UPROPERTY() TArray<FIntPoint> Cells;
};

// Authoring sites in world cm: X, Y, yaw in degrees, scale. Height is fitted at each bake.
USTRUCT()
struct FForestTalusVariant
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UStaticMesh> Mesh;
    UPROPERTY() TArray<FVector4f> Hills;
    UPROPERTY() TArray<FVector4f> Road;
};

// The PCG spawn point is the origin of its hydrology tile, in world centimetres.
UCLASS()
class FPSGAME_API AForestVillagePoolSurface : public AActor
{
    GENERATED_BODY()
public:
    AForestVillagePoolSurface();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    void UseWaterMaterial(UMaterialInterface* Material);
private:
    void BuildSurface();
    UPROPERTY() TObjectPtr<UDynamicMeshComponent> Water;
};

// The sample is indexed in absolute map coordinates. The original Landscape and the
// village platform stay in their own owners; this actor contains the surrounding ground.
UCLASS()
class FPSGAME_API AForestVillageRegion : public AActor
{
    GENERATED_BODY()
public:
    AForestVillageRegion();
    UPROPERTY(EditAnywhere, Category="Forest village|Surface") TObjectPtr<UMaterialInterface> VillageLoessDetail;
    UPROPERTY(EditAnywhere, Category="Forest village|Surface") TObjectPtr<UMaterialInterface> VillageStableEntryWear;
    UPROPERTY(EditAnywhere, Category="Forest village|Quarry") TSoftObjectPtr<UWorld> QuarryLevel;
    UPROPERTY(EditAnywhere, Category="Forest village|Quarry") FVector QuarryOrigin=FVector::ZeroVector;
    double GroundHeight(double X, double Y) const;
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool InstallCliffExposure(const FString& Directory, UStaticMesh* Ledge, UStaticMesh* Shelf);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool InstallCliffTalus(const FString& SitesFile, UStaticMesh* Fine, UStaticMesh* Fragment);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    static bool WriteCliffLandscapeLayer(class ALandscape* Landscape, const FString& DeltaFile);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    static bool BuildSceneryNaniteMesh(UStaticMesh* Mesh, UMaterialInterface* PackedTerrainMaterial);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    static bool BuildReferenceLandscapeNanite(ALandscapeProxy* Landscape);
    UFUNCTION(BlueprintPure, Category="Forest village|Authoring")
    FTransform FitFloorDecal(double X, double Y, double YawDegrees, double Scale) const;
    bool HasGround() const;
    double MapRoadWeight(double X,double Y) const;
    FVector2f ReferencePaintAt(int32 I,int32 J) const;
    UMaterialInterface* GetReferenceSurface() const { return ReferenceSurface; }
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool BakeReferenceSurface(const FString& Directory,UMaterialInterface* Material);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool BakeMapRoads(const FString& Directory);
    bool HasSitedHill() const { return SettlementOffsets.Num()!=0; }
    FIntPoint GetSettlementMinM() const { return SettlementMinM; }
    double GetSettlementDatumCm() const { return SettlementDatumCm; }
    double DressingOffsetCm(double X,double Y) const;
    int32 SettlementOffsetCm(int32 I,int32 J) const;
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool InstallHillSite(const FString& Directory,FIntPoint MinM,double DatumCm);
#if WITH_EDITOR
    static UMaterialInterface* HillsGrassMaterial(UStaticMesh* Mesh);
#endif
    const FVector4f* HarvestTreeSite(FIntPoint Cell) const { return HarvestTreeSites.Find(Cell); }
    bool ReplacesStudyRock(const FVector& Pos) const { return ReplacedStudyRocks.Contains(FIntPoint(FMath::RoundToInt32(Pos.X),FMath::RoundToInt32(Pos.Y))); }
    bool ReplacesStudyTree(const FVector& Pos) const;
    UMaterialInterface* GetGateSurface() const { return GateSurface; }
    FVector2f GetGatePaint(int32 Column, int32 Row) const;
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    static bool BuildSurfaceFunction(UMaterialInterface* Palette, UMaterialFunction* Function);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    static bool CopyGateMaterialInputs(UMaterial* Original, UMaterialExpression* Attributes);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool ApplySurfaceSample(const FString& Directory, UMaterialInterface* Surface,
        UMaterialInterface* Transition, UMaterialInterface* Gate);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    static bool ExportForestSurface(ALandscapeProxy* Landscape, const FString& Filename);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool BakeGround(const FString& Directory);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool BakeVegetation(const FString& PointsFile, const TArray<UInstancedStaticMeshComponent*>& StudyMeshes, FName OnlyTheme=NAME_None);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool InstallGrassCover(const FString& MaskFile, bool bMaskOnly=false);
    UFUNCTION(BlueprintCallable, Category="Forest village|Authoring")
    bool BakeWoodlandPools(const FString& Directory,int32 Seed);
    TemperateForestWater::FPlanPtr GetWoodlandWater() const;
    void BuildNearGrassPoints(FIntPoint Cell,FPCGContext& Context) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
#if WITH_EDITOR
    virtual bool ShouldTickIfViewportsOnly() const override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void Destroyed() override;
#endif
private:
#if WITH_EDITORONLY_DATA
    UPROPERTY() TObjectPtr<UStaticMesh> CliffLedgeMesh;
    UPROPERTY() TArray<FTransform> CliffHillLedges;
    UPROPERTY() TArray<FTransform> CliffRoadLedges;
    UPROPERTY() TObjectPtr<UStaticMesh> CliffShelfMesh;
    UPROPERTY() TArray<FTransform> CliffHillShelves;
    UPROPERTY() TArray<FTransform> CliffRoadShelves;
    UPROPERTY() TArray<uint8> CliffExposureMask;
    UPROPERTY() TArray<FForestTalusVariant> TalusVariants;
    void FitTalusSites(const TArray<FVector4f>& Sites,UStaticMesh* Mesh,TArray<FTransform>& Out) const;
#endif
    void UpdateQuarryStreaming();
    FTimerHandle QuarryTimer;
    UPROPERTY(Transient) TObjectPtr<class ULevelStreamingDynamic> QuarryStreaming;
    void UpdateGrassCells();
    void ReleaseGrassCells();
    FTimerHandle GrassTimer;
    TWeakObjectPtr<class ATemperateHillsWorld> GrassSettlement;
    TArray<FVector2D,TInlineAllocator<2>> SettledGrassViews;
    TMap<FIntPoint,TWeakObjectPtr<AForestGrassCell>> GrassCells;
    UPROPERTY() TObjectPtr<UPCGGraph> NearGrassGraph;
    UPROPERTY() TArray<uint8> NearGrassMask;
    UPROPERTY() TArray<uint8> OccupiedGrassTiles;
    UPROPERTY() TArray<FVector2f> GrassRestZ;
    UPROPERTY() TArray<FForestVillagePoolSite> WoodlandPools;
    mutable TemperateForestWater::FPlanPtr WoodlandWater;
    UPROPERTY() TArray<int16> HeightCm;
    // One authored root per selected 12 m harvest cell: world XY, ground Z, yaw.
    UPROPERTY() TMap<FIntPoint,FVector4f> HarvestTreeSites;
    UPROPERTY() TSet<FIntPoint> ReplacedStudyRocks;
    UPROPERTY() TArray<uint8> MapRoadPaint;
    UPROPERTY() TObjectPtr<UMaterialInterface> ReferenceSurface;
    UPROPERTY() TArray<uint8> SettlementPaint;
    UPROPERTY() FIntPoint SettlementMinM=FIntPoint(-172,252);
    UPROPERTY() double SettlementDatumCm=0.;
    UPROPERTY() TArray<int16> SettlementOffsets;
    UPROPERTY() TArray<uint8> GatePaint;
    UPROPERTY() TObjectPtr<UMaterialInterface> GateSurface;
};
