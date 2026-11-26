#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Engine/NetSerialization.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "../FPSGAMEGameMode.h"
#include "TemperateHillsRiver.h"
#include "TemperateForestWater.h"
#include "TemperateHillsSurface.h"
#include "TemperateChapelSite.h"
#include "TemperateVillageSite.h"
#include "TemperateHillsWorld.generated.h"

class UPCGComponent;
namespace HillsVegetation { struct FNeighborhood; }
namespace TemperateIronOutcrops { struct FSearch; }
namespace HillsPlacement { struct FVegetationRockMask; }
struct FTemperateForestWindState;
class UPCGGraph;
class UBoxComponent;
class UDynamicMeshComponent;
class UStaticMesh;
class USkeletalMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UMaterialParameterCollection;
class UTransformProviderData;
class UInstancedStaticMeshComponent;
class ACameraActor;
class UPrimitiveComponent;
class UTexture2D;
namespace TemperateHillsGround { struct FMapSource; }
class UVolumetricCloudComponent;
class UStaticMeshComponent;
class AFPSWeatherManager;
struct FTemperateHillsStreamingState;
struct FStreamableHandle;
struct FTemperateBackdropState;
struct FProductionResource;
enum class ETemperatePlantKind : uint8;

USTRUCT(BlueprintType)
struct FTemperateFlowerFamily
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, Category="Flowers") TArray<TSoftObjectPtr<UStaticMesh>> Variants;
};

/** Curated environment references. No level/assembly imports from the source packs. */
UCLASS(BlueprintType)
class FPSGAME_API UTemperateHillsAssets : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UMaterialInterface> GroundMaterial;
    UPROPERTY(EditAnywhere, Category="Forest|GroundCache") TSoftObjectPtr<class URuntimeVirtualTexture> VillageColorCache;
    UPROPERTY(EditAnywhere, Category="Forest|GroundCache") TSoftObjectPtr<class URuntimeVirtualTexture> VillageHeightCache;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UMaterialInterface> ValleyFogMaterial;
    UPROPERTY(EditAnywhere) TSoftClassPtr<AActor> ValleyFogClass;
    UPROPERTY(EditAnywhere, Category="Forest|Wind") TObjectPtr<UMaterialParameterCollection> ForestWindParameters;
    UPROPERTY(EditAnywhere, Category="Forest|Wind") TObjectPtr<UTransformProviderData> ForestWindProvider;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UStaticMesh> TrunkCollisionMesh;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<USkeletalMesh>> Trees;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UStaticMesh>> Rocks;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UStaticMesh>> Shrubs;
    UPROPERTY(EditAnywhere, Category="Grass") TArray<TSoftObjectPtr<UStaticMesh>> Grass;
    UPROPERTY(EditAnywhere, Category="Grass") TArray<TSoftObjectPtr<UStaticMesh>> RainforestGrass;
    UPROPERTY(EditAnywhere, Category="Grass") TArray<TSoftObjectPtr<UStaticMesh>> GrassAccents;
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="45",ClampMax="200",Units="cm")) float GrassSpacingCm = 55.f;
    // Legacy serialized coverage fields remain for asset/script compatibility.
    // Runtime density now comes solely from [TemperateHills.Ecology] in Game.ini;
    // asset spacing and mesh references still own the candidate layout/palette.
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="0",ClampMax="1")) float GrassCoverage = .94f;
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="120",ClampMax="500",Units="cm")) float GrassAccentSpacingCm = 180.f;
    UPROPERTY(EditAnywhere, Category="Grass", meta=(ClampMin="0",ClampMax="1")) float GrassAccentCoverage = .5f;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UPCGGraph>> Graphs;
    UPROPERTY(EditAnywhere, Category="River") TSoftObjectPtr<UMaterialInterface> RiverMaterial;
    UPROPERTY(EditAnywhere, Category="River") TArray<TSoftObjectPtr<UStaticMesh>> RiverRocks;
    UPROPERTY(EditAnywhere, Category="River|Pebble Shore") TArray<TSoftObjectPtr<UStaticMesh>> RiverPebbles;
    UPROPERTY(EditAnywhere, Category="Quarry|Lake Slope") TArray<TSoftObjectPtr<UStaticMesh>> QuarryShoreChips;
    UPROPERTY(EditAnywhere, Category="River|Pebble Shore", meta=(ClampMin="0",ClampMax="40",Units="cm")) float RiverBankReliefCm=22.f;
    UPROPERTY(EditAnywhere, Category="River|Pebble Shore", meta=(ClampMin="45",ClampMax="180",Units="cm")) float RiverPebbleSpacingCm=85.f;
    UPROPERTY(EditAnywhere, Category="River|Pebble Shore", meta=(ClampMin="0",ClampMax="1")) float RiverPebbleCoverage=.78f;
    UPROPERTY(EditAnywhere, Category="River|Ecology") TArray<TSoftObjectPtr<UStaticMesh>> RiverGroundCover;
    UPROPERTY(EditAnywhere, Category="River|Ecology") TArray<TSoftObjectPtr<UStaticMesh>> RiverReeds;
    UPROPERTY(EditAnywhere, Category="River|Ecology") TArray<TSoftObjectPtr<UStaticMesh>> RiverBankGrasses;
    UPROPERTY(EditAnywhere, Category="River|Ecology") TArray<TSoftObjectPtr<UStaticMesh>> RiverUnderstory;
    // Legacy values; river plant densities also use TemperateHills.Ecology.
    UPROPERTY(EditAnywhere, Category="River|Ecology", meta=(ClampMin="0",ClampMax="1")) float RiverPlantCoverage=.95f;
    UPROPERTY(EditAnywhere, Category="River|Ecology", meta=(ClampMin="0",ClampMax="1")) float RiverGroundCoverCoverage=.96f;
    UPROPERTY(EditAnywhere, Category="River|Ecology", meta=(ClampMin="40",ClampMax="150",Units="cm")) float RiverGroundCoverSpacingCm=52.f;
    UPROPERTY(EditAnywhere, Category="Trees|Regrowth", meta=(ClampMin="0")) float TreeDormantDays=1.f;
    UPROPERTY(EditAnywhere, Category="Trees|Regrowth", meta=(ClampMin="0.1")) float TreeMatureDays=6.f;
    UPROPERTY(EditAnywhere, Category="Backdrop") TSoftObjectPtr<UMaterialInterface> BackdropMaterial;
    // Native default also upgrades existing biome assets that predate this field.
    UPROPERTY(EditAnywhere, Category="Sky") TSoftObjectPtr<UMaterialInterface> SkyCloudMaterial =
        TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/Sky/MI_HillsClouds.MI_HillsClouds")));
    UPROPERTY(EditAnywhere, Category="Sky|Day Night") TSoftObjectPtr<UMaterialInterface> DayNightSkyMaterial =
        TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/Sky/MI_HillsDayNightSky.MI_HillsDayNightSky")));
    UPROPERTY(EditAnywhere, Category="Sky|Day Night") TSoftObjectPtr<UStaticMesh> DayNightSkyMesh =
        TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Engine/EngineSky/SM_SkySphere.SM_SkySphere")));
    // Source Sunshine was authored at EV100 5.5; hills retain their EV100 1 lighting.
    UPROPERTY(EditAnywhere, Category="Sky|Day Night") float SkyExposureCompensation = -4.5f;
    UPROPERTY(EditAnywhere, Category="Sky|Day Night") float SkyRotationDegrees = 0.f;
    // Source rotation speed .0005 turns/sec at the existing 2160-second game day.
    UPROPERTY(EditAnywhere, Category="Sky|Day Night") float SkyTurnsPerGameDay = 1.08f;
    UPROPERTY(EditAnywhere, Category="Fog", meta=(ClampMin="0",ClampMax="1")) float ValleyFogDensity = .32f;
    // Embedded surface stones. They reuse the loaded rock meshes and ride the grass PCG
    // layer (no collision, 35-60 m cull) so the ground keeps detail where the player
    // looks without a second streaming budget. Appended after every existing field on
    // purpose: adding members in the middle of this class shifts the ones after it, and
    // a translation unit that is not rebuilt then reads them at the wrong offset.
    UPROPERTY(EditAnywhere, Category="Grass|Ground Detail", meta=(ClampMin="90",ClampMax="600",Units="cm")) float GroundDebrisSpacingCm = 240.f;
    UPROPERTY(EditAnywhere, Category="Grass|Ground Detail", meta=(ClampMin="0",ClampMax="1")) float GroundDebrisCoverage = .30f;
    UPROPERTY(EditAnywhere, Category="Grass|Ground Detail", meta=(ClampMin="4",ClampMax="120",Units="cm")) float GroundDebrisSizeCm = 20.f;
    // Meadow wildflowers/ground plants ride the grass PCG layer as a sparse third
    // pass; forest-floor deadwood and slope cliffs ride the rock layer for its
    // 120 m lifetime and collision while staying unmineable through the existing
    // 500 cm instance-radius reject. Backdrop trees are far-field silhouettes
    // only; river mist reuses the valley fog volume class and material.
    UPROPERTY(EditAnywhere, Category="Grass|Flowers") TArray<TSoftObjectPtr<UStaticMesh>> MeadowFlowers;
    UPROPERTY(EditAnywhere, Category="Grass|Flowers", meta=(ClampMin="200",ClampMax="1200",Units="cm")) float MeadowFlowerSpacingCm = 380.f;
    // Legacy serialized value; the active value is MeadowFlowersDensity.
    UPROPERTY(EditAnywhere, Category="Grass|Flowers", meta=(ClampMin="0",ClampMax="1")) float MeadowFlowerCoverage = .40f;
    UPROPERTY(EditAnywhere, Category="Trees|Forest Floor") TArray<TSoftObjectPtr<UStaticMesh>> FallenLogs;
    UPROPERTY(EditAnywhere, Category="Trees|Forest Floor") TArray<TSoftObjectPtr<UStaticMesh>> ForestRoots;
    UPROPERTY(EditAnywhere, Category="Trees|Forest Floor", meta=(ClampMin="0",ClampMax="1")) float ForestFloorCoverage = .50f;
    UPROPERTY(EditAnywhere, Category="Rocks|Cliffs") TArray<TSoftObjectPtr<UStaticMesh>> Cliffs;
    UPROPERTY(EditAnywhere, Category="Rocks|Cliffs", meta=(ClampMin="0",ClampMax="1")) float CliffCoverage = .55f;
    UPROPERTY(EditAnywhere, Category="Backdrop") TArray<TSoftObjectPtr<UStaticMesh>> BackdropTrees;
    UPROPERTY(EditAnywhere, Category="Backdrop", meta=(ClampMin="0",ClampMax="6000")) int32 BackdropTreeBudget = 1400;
    UPROPERTY(EditAnywhere, Category="Fog", meta=(ClampMin="0",ClampMax="1")) float RiverMistDensity = .24f;
    // Decorative PVE plants share the shrub PCG cell lifetime, not tree harvest IDs.
    UPROPERTY(EditAnywhere, Category="Trees|Understory") TArray<TSoftObjectPtr<USkeletalMesh>> ForestSaplings;
    UPROPERTY(EditAnywhere, Category="Trees|Understory") TArray<TSoftObjectPtr<USkeletalMesh>> ForestShrubs;
    UPROPERTY(EditAnywhere, Category="Trees|Understory") TArray<TSoftObjectPtr<USkeletalMesh>> ForestFerns;
    UPROPERTY(EditAnywhere, Category="Forest|Microhabitats") TArray<TSoftObjectPtr<UStaticMesh>> ForestFungi;
    UPROPERTY(EditAnywhere, Category="Forest|Microhabitats") TArray<TSoftObjectPtr<UStaticMesh>> ForestMoss;
    UPROPERTY(EditAnywhere, Category="Rainforest|Floor") TArray<TSoftObjectPtr<UStaticMesh>> RainforestTwigs;
    UPROPERTY(EditAnywhere, Category="Rainforest|Floor") TSoftObjectPtr<UStaticMesh> RainforestBankBoulder;
    UPROPERTY(EditAnywhere, Category="Rainforest|Floor") TArray<TSoftObjectPtr<UStaticMesh>> RainforestHerbs;
    UPROPERTY(EditAnywhere, Category="Rainforest|Floor") TArray<FTemperateFlowerFamily> ClearingFlowers;
    // Dry-ground cover inside the rainforest mask: low, spreading and tall clumps.
    UPROPERTY(EditAnywhere, Category="Rainforest|Floor") TArray<TSoftObjectPtr<UStaticMesh>> RainforestCarpetGrass;
    UPROPERTY(EditAnywhere, Category="WhiteCliffs") TArray<TSoftObjectPtr<UStaticMesh>> WhiteCliffMeshes;
    UPROPERTY(EditAnywhere, Category="WhiteCliffs") TArray<TSoftObjectPtr<UStaticMesh>> QuarryProps;
    UPROPERTY(EditAnywhere, Category="River|Ecology") TArray<TSoftObjectPtr<UStaticMesh>> WetBankSaplings;
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

/** V1 identity/seed; V2 craters; V3 terrain edits; V4 generator V3; V5 wall; V6 blacksmith repair. */
UCLASS()
class FPSGAME_API UTemperateHillsSave : public USaveGame
{
    GENERATED_BODY()
public:
    // Exposed for maintenance tooling (Tools/WorldGeneration/clean_hills_edits.py).
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Version = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Seed = 122;
    /** 1 = original, 2 = ridged, 3 = rolling hills with a reserved hilltop village. Missing -> 1. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 GeneratorVersion = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FGuid WorldId;
    // Absent in older saves, which keep their original weather and raid schedules.
    UPROPERTY() int32 PlaythroughSeed = 0;
    // Kept so V2 saves still load; new saves write Edits only.
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FHillsCraterRecord> Craters;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FHillsTerrainEditRecord> Edits;
    // Older worlds omit this field and keep the ruined perimeter.
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bVillageWallRepaired = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bVillageBlacksmithRepaired = false;
    UPROPERTY() int32 VillagePlanVersion = 1;
    // V1 recorded unlocks only. V2 atomically restored the wall and smithy.
    // From V3 onward each new plan bit records a committed restoration.
    static constexpr int32 CurrentVillagePlanVersion = 11;
    static constexpr uint8 CarpenterPlan = 4;
    static constexpr uint8 TavernPlan = 8;
    static constexpr uint8 HerbalistPlan = 16;
    static constexpr uint8 ConstructionPlan = 32;
    static constexpr uint8 HighWallPlan = 64;
    static constexpr uint8 WindmillPlan = 128;
    // The original serialized byte is full. Keep its reflected type for V1–8 saves.
    static constexpr uint16 BakeryPlan = 256;
    static constexpr uint16 GunshopPlan = 512;
    static constexpr uint16 GarrisonMechanicsPlan = 1024;
    UPROPERTY() bool bGarrisonMechanics = false;
    UPROPERTY() bool bVillageBakeryRepaired = false;
    UPROPERTY() bool bVillageGunshopRepaired = false;
    UPROPERTY() uint8 VillagePlansUnlocked = 0;
    uint8 SavedVillagePlans() const
    {
        uint8 Mask = 3;
        if (VillagePlanVersion >= 3) Mask |= CarpenterPlan;
        if (VillagePlanVersion >= 4) Mask |= TavernPlan;
        if (VillagePlanVersion >= 5) Mask |= HerbalistPlan;
        if (VillagePlanVersion >= 6) Mask |= ConstructionPlan;
        if (VillagePlanVersion >= 7 && bVillageWallRepaired) Mask |= HighWallPlan;
        if (VillagePlanVersion >= 8) Mask |= WindmillPlan;
        return VillagePlansUnlocked & Mask;
    }
    // Matches the wall/gate damage sidecar. Legacy saves share the zero generation.
    UPROPERTY() FGuid VillageDefenseGeneration;
};

struct FTemperatePlacement
{
    FTransform Transform;
    FSoftObjectPath Mesh;
    uint32 Key = 0;
    uint64 CandidateId = 0;
    bool bVillagePlanting = false;
    bool bHasTriangleSupport = false;
};

UCLASS()
class FPSGAME_API ATemperateHillsWorld : public AActor
{
    GENERATED_BODY()
public:
    ATemperateHillsWorld();
    bool IsForestVillage() const { return ActorHasTag(TEXT("ForestPathVillage")); }
    static TSharedPtr<FStreamableHandle> RequestResidentAppearance(UWorld* World, TArray<FSoftObjectPath> Paths, FSimpleDelegate OnLoaded = {});
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(EditAnywhere, Category="Hills") TObjectPtr<UTemperateHillsAssets> Assets;
    UPROPERTY(EditDefaultsOnly, Category="River|Pilot") TSoftObjectPtr<UMaterialInterface> RiverPilotMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Fluids/RiverPilot20260923/M_RiverPilot.M_RiverPilot")));
    UPROPERTY(EditDefaultsOnly, Category="River|Pilot") TSoftObjectPtr<class UNiagaraSystem> RiverPilotSplash = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash.NS_RiverBulletSplash")));
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Hills") int32 Seed = 122;
    /** 0 until the session resolves; replicated so clients rebuild with the server's formula. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Hills") int32 GeneratorVersion = 0;
    UPROPERTY(EditAnywhere, Replicated, Category="Hills", meta=(ClampMin="256",ClampMax="1024")) float SizeMeters = 1024.f;
    UPROPERTY(Replicated) FTemperateEcologySnapshot NetEcology;
    /** Session policy; existing saved edits are retained while new edits are paused. */
    UPROPERTY(BlueprintReadOnly, Replicated, Category="Hills") bool bTerrainDestructionEnabled = false;
    const TemperateEcology::FProfile& EcologyProfile() const { return NetEcology.Profile; }
    UPROPERTY(EditAnywhere, Category="Hills|Streaming", meta=(ClampMin="96",ClampMax="256")) float DetailRadiusMeters = 160.f;
    UPROPERTY(EditAnywhere, Category="Hills|Streaming", meta=(ClampMin="256",ClampMax="512")) float ViewRadiusMeters = 384.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hills") bool bReady = false;
    // Allows the loading camera/pawn and PCG to prepare before gameplay is released.
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hills") bool bSurfaceReady = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="Hills") FGuid WorldId;
    // Zero identifies legacy sessions. A new playthrough varies events while
    // keeping its survey anchor independent of subsequent player earthworks.
    UPROPERTY(Replicated) int32 PlaythroughSeed = 0;
    /** M4 联机：服务端广播的地形编辑（与存档同构的传输形）+ 版本号；客户端转成 TerrainEdits 做确定性重建。 */
    UPROPERTY(ReplicatedUsing=OnRep_NetEdits)
    TArray<FHillsTerrainEditRecord> NetEdits;
    UPROPERTY(Replicated)
    int32 NetEditsVersion = 0;
    UFUNCTION()
    void OnRep_NetEdits();
    UFUNCTION(BlueprintPure, Category="Hills") FVector GetStartLocation() const;
    /** Stable pre-settlement anchor used by river/village planning, never the player entry. */
    FVector GetGenerationAnchor() const;
#if WITH_EDITOR
    bool BakeFixedLayout();
    bool ExportQuarrySurvey(const FString& Directory);
    bool BakeFixedQuarryDressing(uint32 LayoutChecksum);
#endif
    bool PrepareSpawnGround(AController* Controller);
    bool RequestQuarryVisit(class ACharacter* Player,FString& Reason);
    void PrefetchQuarryVisit();
    bool PrepareQuarryForVegetation(const FBox& CellBounds);
    FRotator GetStartRotation() const;
    const FTemperateVillageSite& GetVillageSite() const { return VillageSite; }
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsVillageWallRepaired() const { return bVillageWallRepaired; }
    bool HasVillageHighWall() const { return bVillageWallRepaired && (VillagePlansUnlocked & UTemperateHillsSave::HighWallPlan) != 0; }
    /** Call from the authoritative repair quest after its real objectives succeed.
      * Returns false if saving fails or a pawn occupies the completed wall footprint. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Hills|Village")
    bool CompleteVillageWallRepair(FText& FailureReason);
    bool CompleteVillageHighWallUpgrade(FText& FailureReason);
    uint16 GetSiegeRanks() const { return SiegeRanks; }
    bool PurchaseSiegeUpgrade(APawn* Payer,int32 Index,int32 ExpectedRank,FText& Failure);
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsVillageBlacksmithRepaired() const { return bVillageBlacksmithRepaired; }
    /** Quest completion entry; commits the restored shop before enabling its forge. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Hills|Village")
    bool CompleteVillageBlacksmithRepair(FText& FailureReason);
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsVillageCarpenterRepaired() const { return (VillagePlansUnlocked & UTemperateHillsSave::CarpenterPlan) != 0; }
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Hills|Village")
    bool CompleteVillageCarpenterRepair(FText& FailureReason);
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsTavernRepaired() const { return (VillagePlansUnlocked & UTemperateHillsSave::TavernPlan) != 0; }
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsHerbalistRepaired() const { return (VillagePlansUnlocked & UTemperateHillsSave::HerbalistPlan) != 0; }
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsWindmillRepaired() const { return (VillagePlansUnlocked & UTemperateHillsSave::WindmillPlan) != 0; }
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsBakeryRepaired() const { return bVillageBakeryRepaired; }
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsGunshopRepaired() const { return bVillageGunshopRepaired; }
    // The streamed tavern supplies its construction footprint while present.
    DECLARE_DELEGATE_RetVal(bool, FTavernAreaOccupied);
    FTavernAreaOccupied TavernAreaOccupied;
    FSimpleMulticastDelegate OnTavernRepairChanged;
    bool IsVillagePlanUnlocked(FName Plan) const;
    bool UnlockVillagePlan(FName Plan,FText& FailureReason);
    bool ResetVillageUpgrades(FText& FailureReason);
#if !UE_BUILD_SHIPPING
    void RequestRainforestVisit();
    void RequestVillageVisit();
#endif
    double RainforestWeight(double X,double Y) const {return RiverPlan?RiverPlan->RainforestWeight(X,Y):0.;}
    double Height(double X, double Y) const;
    TemperateRiver::FSample SampleRiver(double X, double Y) const
    { return RiverPlan ? RiverPlan->Sample(X, Y) : TemperateRiver::FSample(); }
    FVector SurfaceNormal(double X, double Y) const;
    TemperateForestWater::FSample SampleForestWater(double X,double Y) const
    {return ForestWaterPlan?ForestWaterPlan->Sample(X,Y):TemperateForestWater::FSample();}
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
    uint32 GetTerrainEditRevision() const { return TerrainEditRevision; }
    uint32 GetMapSurfaceRevision() const;
    // Small shared sample for this level's connected peers; the harvest ledger travels on changes.
    UPROPERTY(ReplicatedUsing=OnRep_ForestGrowthDay) double ForestGrowthDay=-1.;
    UFUNCTION() void OnRep_ForestGrowthDay();
    FColor ForestMapLayers(double X,double Y,double GroundZ) const;
    double SettlementRoadWeight(double X,double Y) const;
    UMaterialInterface* GetMapGroundMaterial() const;
    void CopyMapGround(TemperateHillsGround::FMapSource& Out) const;
    void GetForestStandingTrees(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const;
    void GetPlacements(int32 Layer, const FBox& Bounds, TArray<FTemperatePlacement>& Out, bool IncludeRegrowth=false) const;
    TSharedPtr<HillsVegetation::FNeighborhood> PrepareVegetationCell(const FBox& Bounds,bool bNeedsGround=true) const;
    TSharedPtr<HillsVegetation::FNeighborhood> BeginVegetationCell(const FBox& Bounds) const;
    bool AdvanceVegetationCell(const TSharedPtr<HillsVegetation::FNeighborhood>& Neighbors,bool bNeedsGround) const;
    void GetVegetationStrip(int32 Layer,const FBox& Bounds,HillsVegetation::FNeighborhood& Neighbors,TArray<FTemperatePlacement>& Out) const;
    /** Shared natural/F6 support rules; only changes Z, never a resource's XY. */
    bool FitRockPlacement(const UStaticMesh& Mesh,FTransform& Placement,bool Ore) const;
    uint32 LayoutHash(int32 Layer) const;
    /** 岩块候选的矿种定义（iron_ore/copper_ore/silver_ore/gold_ore，空=纯石）。渲染外观
     *  （矿脉变体网格）与采集掉落必须共用这一份判定，否则看见的矿和挖出的矿会不一致。
     *  2026-09-30 空间加权：矿围绕岩石地貌（地表碎石斑+坡度）与河床带富集，At 为候选格心。 */
    FString RockOreDefinition(uint32 Key, const FVector2D& At) const;
    /** 含矿岩块：每种矿四个稳定随机形态（00A–03A）；纯石返回空路径。 */
    FSoftObjectPath OreRockVariantMesh(uint32 Key, const FVector2D& At) const;
    FString ProductionResourceId(int32 Layer,uint64 Candidate) const;
    bool IsProductionDepleted(int32 Layer,uint64 Candidate) const;
    bool FindNearestIronOutcrop(const FVector2D& From,TemperateIronOutcrops::FSearch& Search,FVector& OutPoint,uint64& OutRock) const;
    void GetHarvestedStumps(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const;
    void GetRegrowingTrees(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const;
    // Fits legacy and new saved offsets against the actual forest-village surface.
    bool ForestSaplingPlacement(uint64 CandidateId,FVector2D& Offset,FVector2D Stump,FTemperatePlacement& Out) const;
    bool ResolveProductionResource(const FHitResult& Hit,FProductionResource& Resource,FString& Reason) const;
    void CompleteProductionHarvest(const FProductionResource& Resource,const FHitResult& Hit,const FVector& Direction);
    UFUNCTION(NetMulticast,Unreliable) void MulticastHarvestImpact(bool Wood,bool Stump,FVector_NetQuantize Point,uint32 ImpactSeed);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class UTemperateVillageCheckCommandlet;
    UPROPERTY(EditDefaultsOnly,Category="Forest|Village") TSoftObjectPtr<UMaterialInterface> ForestVillageRoadMaterial =
        TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestVillageMudRoad.MI_ForestVillageMudRoad")));
    UPROPERTY(EditDefaultsOnly,Category="Forest|Water") TSoftObjectPtr<UMaterialInterface> ForestPondMaterial =
        TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/WetForest/M_ForestPond.M_ForestPond")));
    TemperateForestWater::FPlanPtr ForestWaterPlan;
    UPROPERTY() TObjectPtr<UBoxComponent> GenerationBounds;
    UPROPERTY() TArray<TObjectPtr<UPCGComponent>> PCGLayers;
    UPROPERTY() TArray<TObjectPtr<UDynamicMeshComponent>> Terrain;
    UPROPERTY() TArray<TObjectPtr<AActor>> ValleyFog;
    UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> FogMaterials;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> GroundMID;
    UPROPERTY(Transient) TArray<TObjectPtr<class URuntimeVirtualTextureComponent>> VillageGroundCache;
    void PrepareVillageGroundCache();
    void ApplySmithYardGround();
    void ReleaseVillageGroundCache();
    void BindVillageGroundCache(UDynamicMeshComponent* Mesh);
    void InvalidateVillageGroundCache(const UDynamicMeshComponent* Mesh);
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BackdropMID;
    UPROPERTY() TObjectPtr<UTexture2D> BackdropColor;
    UPROPERTY() TObjectPtr<UTexture2D> BackdropCoverage;
    UPROPERTY() TArray<TObjectPtr<UDynamicMeshComponent>> BackdropMeshes;
    UPROPERTY() TArray<TObjectPtr<class UHierarchicalInstancedStaticMeshComponent>> BackdropCanopy;
    UPROPERTY() TObjectPtr<UVolumetricCloudComponent> HillsClouds;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> DayNightSky;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> DayNightSkyMID;
    UPROPERTY(Transient) TWeakObjectPtr<AFPSWeatherManager> SkyWeather;
    TWeakObjectPtr<UMaterialInstanceDynamic> WetGroundMaterial;
    float WeatherLookupLeft=0.f,LastGroundWetness=-1.f;
    float ForestWindUpdateLeft=0.f;
    TSharedPtr<FTemperateForestWindState> ForestWindState;
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
    TArray<TSharedPtr<FStreamableHandle>> PendingResidentAppearances;
    TSharedPtr<FTemperateBackdropState> Backdrop;
    TemperateRiver::FPlanPtr RiverPlan;
    TArray<double> FrameSamples;
    double Noise(double X, double Y, uint32 Salt) const;
    double PathDistance(double X, double Y) const;
    double ForestWeight(double X, double Y) const;
    bool ForestTreeCandidate(int32 X,int32 Y,FTemperatePlacement& Out) const;
    bool TreeCandidate(int32 GX, int32 GY, FTemperatePlacement& Out) const;
    bool FitVegetationPlacement(FTemperatePlacement& Plant,const FBox& MeshBox,ETemperatePlantKind Kind) const;
    void GetVegetationPlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out) const;
    void GetBasePlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool IncludeRegrowth=false) const;
    void GatherBasePlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool IncludeRegrowth) const;
    void GetRockPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool IncludeDepleted=false) const;
    const TArray<FTemperatePlacement>& UpdateVegetationRockMask(const FBox& Bounds,double PlantReach,
        TSharedPtr<HillsPlacement::FVegetationRockMask>& Mask,double UpcomingPlantReach=0.) const;
    void ExcludeRockFootprints(const FBox& Bounds,TArray<FTemperatePlacement>& Plants,
        TSharedPtr<HillsPlacement::FVegetationRockMask>& Mask) const;
    void GetGrassPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    void AddClearingFlowerPatch(int32 GX,int32 GY,double TileSize,const FBox2D& Bounds,
        const FTemperateFlowerFamily& Family,uint32 PatchKey,TArray<FTemperatePlacement>& Out) const;
    void GetForestUnderstoryPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    /** Small embedded surface stones that match the ground material's dry/gravel patches. */
    void GetGroundDebrisPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    void GetUplandGroundPatches(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const;
    bool GetQuarryLakeSlopeCover(const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool bShrubs,int32* CompletedRows=nullptr) const;
    void GetRiverPlantPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    void GetRiverShrubPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    void GetRiverPebblePlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    void GetShoreRockCompanions(const FBox& Bounds, const TArray<FTemperatePlacement>& Supports,
        TArray<FTemperatePlacement>& Out) const;
    /** Fallen logs and exposed roots inside forest. Rock-layer lifetime and collision. */
    void GetForestFloorPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    /** Big rock modules embedded into steep hillsides. Same rock layer, never mineable. */
    void GetCliffPlacements(const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    void AddQuarryRockLoadPaths(TArray<FSoftObjectPath>& Paths) const;
    static const FSoftObjectPath& QuarrySlopeStoneMesh(uint32 Variant,bool bLedge);
    void GetWhiteCliffPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool bIncludeChips=false,int32 Section=INDEX_NONE) const;
    bool WithinQuarryReach(const FVector& Position,double Reach) const;
    void StreamQuarry(TConstArrayView<FVector> ViewCenters);
    void GetNurseLogPlacements(const FBox& Bounds,const TArray<FTemperatePlacement>& Supports,TArray<FTemperatePlacement>& Ferns,TArray<FTemperatePlacement>* Floor) const;
    void GetHabitatCompanions(const FBox& Bounds,const TArray<FTemperatePlacement>& Supports,bool Trees,
        TArray<FTemperatePlacement>& Plants,TArray<FTemperatePlacement>* Floor) const;
    void GetVisualAnchorPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const;
    void BeginForestVillage();
    void TickForestVillage();
    void BuildForestVillageGround();
    double ForestVillageHeight(double X, double Y) const;
    bool LoadVillageSettlement();
    void BeginStreaming();
    void TickStreaming();
    UFUNCTION() void BindStreamedVillageBuildings();
    void RefreshVillageStreetLighting();
    TWeakObjectPtr<AActor> StreamedTavern;
    TWeakObjectPtr<class AHillsWindmill> StreamedWindmill;
    TWeakObjectPtr<AActor> StreamedBakery;
    TWeakObjectPtr<AActor> StreamedGunshop;
    TWeakObjectPtr<class AVillageBaker> BakeryResident;
    void EndStreaming();
    void LoadNextEnvironmentStage();
    void TickResidentAppearanceLoads();
    void TickPreparation();
    void ActivateVegetationLayer(int32 Layer);
    void SetVegetationGenerationRadius(int32 Layer,float Radius);
    void TickVegetationFrontier();
    void BuildValleyFog();
    void TickBackdrop(bool bCanopyAssetsReady);
    void BeginSkyClouds();
    void ActivateSkyClouds();
    void ActivateDayNightSky();
    void TickDayNightSky();
    void TickForestWind(float DeltaSeconds);
    void EndDayNightSky();
    bool IsBackdropReady() const;
    void SetBackdropCellVisible(FIntPoint Cell, bool Visible);
    /** Instantiates the canopy silhouettes generated by the backdrop worker job. */
    void SpawnBackdropCanopy();
    void EndBackdrop();
    void ResolveSession();
    void RunAudit();
    void AuditCheck(bool Pass, const TCHAR* Message);
    void InvalidateTerrainCells(const FVector2D& Center, double Radius);
    void PersistTerrainEdits();
    void AddTerrainEdit(const TemperateHillsSurface::FTerrainEdit& Edit);
    /** Coarse spatial index (bucket -> indices into TerrainEdits), rebuilt on every change. */
    void RebuildEditBuckets();
    uint32 TerrainEditRevision=0;
    /** Clears PCG ground cover inside one edit's footprint. */
    int32 ClearCoverForEdit(const TemperateHillsSurface::FTerrainEdit& Edit);
    bool IsGroundCoverMesh(const class UStaticMesh* Mesh) const;
    TArray<TemperateHillsSurface::FTerrainEdit> TerrainEdits;
    // M4 联机：客户端等复制会话就绪后只初始化一次；服务端/单机共用后半段管线。
    bool bClientWorldInit = false;
    // V2 出生点会沿谷地搜索；PCG 每个候选都会问一次，必须缓存。
    mutable bool bStartLocationCached = false;
    mutable FVector CachedStartLocation = FVector::ZeroVector;
    bool StartWorldPipeline();
    void ConvertNetEdits();
    void SyncNetEdits();
    TMap<int64, TArray<int32>> EditBuckets;
    double NextCoverSweep = 0;
    FTemperateChapelSite ChapelSite;
    FTemperateVillageSite VillageSite;
    UPROPERTY(ReplicatedUsing=OnRep_VillageWall) bool bVillageWallRepaired=false;
    UPROPERTY(ReplicatedUsing=OnRep_VillageBlacksmith) bool bVillageBlacksmithRepaired=false;
    UPROPERTY(ReplicatedUsing=OnRep_VillagePlansUnlocked) uint8 VillagePlansUnlocked=0;
    UPROPERTY(ReplicatedUsing=OnRep_VillageBakery) bool bVillageBakeryRepaired=false;
    UFUNCTION() void OnRep_VillageBakery();
    UPROPERTY(ReplicatedUsing=OnRep_VillageGunshop) bool bVillageGunshopRepaired=false;
    UFUNCTION() void OnRep_VillageGunshop();
    UPROPERTY(Replicated) bool bGarrisonMechanics=false;
    UPROPERTY(Replicated) uint16 SiegeRanks=0;
    UPROPERTY(Transient) TObjectPtr<class AVillageMechanicalWorkshop> MechanicalWorkshop;
    void UpdateMechanicalWorkshop();
    FTransform MechanicalWorkshopPose() const;
    bool MechanicalWorkshopLotOccupied() const;
    FGuid VillageDefenseGeneration;
    UFUNCTION() void OnRep_VillagePlansUnlocked(uint8 PreviousPlans);
    bool CommitVillagePlanRepair(uint16 PlanBit, int32 RequiredVersion, const TCHAR* SaveError, FText& FailureReason);
    UFUNCTION() void OnRep_VillageBlacksmith();
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> VillageWallParts;
    UPROPERTY(Transient) TArray<TObjectPtr<class AVillageDefenseSection>> VillageDefenseParts;
    UPROPERTY(Transient) TObjectPtr<class AVillagePlantingDisplay> VillagePlantingDisplay;
    UFUNCTION() void OnRep_VillageWall();
    void BuildVillagePerimeter();
    friend class AVillageDefenseStairs;
    void RefreshVillageGateStairs(const class AVillageDefenseStairs* Arriving=nullptr);
    FTimerHandle VillageGateStairRetry;
    void ClearVillagePerimeter();
    void PlanAbandonedVillage(const TemperateForestWater::FPlanPtr& SeedWater);
    bool bSettlementPlanned=false;
    UPROPERTY(Transient) TObjectPtr<AActor> ChapelDoor;
    UPROPERTY(Transient) TObjectPtr<AActor> ChapelShrine;
    void AssembleOldChapel();
};

UCLASS()
class FPSGAME_API ATemperateHillsGameMode : public AFPSGAMEGameMode
{
    GENERATED_BODY()
public:
    virtual void RestartPlayer(AController* NewPlayer) override;
};
