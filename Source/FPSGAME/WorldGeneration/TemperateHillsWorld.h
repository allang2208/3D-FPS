#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "../FPSGAMEGameMode.h"
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
struct FTemperateHillsStreamingState;
struct FTemperateBackdropState;

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
    UPROPERTY(EditAnywhere, Category="Fog", meta=(ClampMin="0",ClampMax="1")) float ValleyFogDensity = .32f;
};

/** V1 stores the world identity/seed. It does not claim harvest/building persistence. */
UCLASS()
class FPSGAME_API UTemperateHillsSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version = 1;
    UPROPERTY() int32 Seed = 122;
    UPROPERTY() FGuid WorldId;
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
    FVector SurfaceNormal(double X, double Y) const;
    void GetPlacements(int32 Layer, const FBox& Bounds, TArray<FTemperatePlacement>& Out) const;
    uint32 LayoutHash(int32 Layer) const;

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
    bool IsBackdropReady() const;
    void SetBackdropCellVisible(FIntPoint Cell, bool Visible);
    void EndBackdrop();
    void ResolveSession();
    void RunAudit();
    void AuditCheck(bool Pass, const TCHAR* Message);
};

UCLASS()
class FPSGAME_API ATemperateHillsGameMode : public AFPSGAMEGameMode
{
    GENERATED_BODY()
public:
    virtual void RestartPlayer(AController* NewPlayer) override;
};
