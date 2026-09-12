#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "../FPSGAMEGameMode.h"
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

/** Curated environment references. No level/assembly imports from the source packs. */
UCLASS(BlueprintType)
class FPSGAME_API UTemperateHillsAssets : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TObjectPtr<UMaterialInterface> GroundMaterial;
    UPROPERTY(EditAnywhere) TObjectPtr<UMaterialInterface> ValleyFogMaterial;
    UPROPERTY(EditAnywhere) TSubclassOf<AActor> ValleyFogClass;
    UPROPERTY(EditAnywhere) TObjectPtr<UStaticMesh> TrunkCollisionMesh;
    UPROPERTY(EditAnywhere) TArray<TObjectPtr<USkeletalMesh>> Trees;
    UPROPERTY(EditAnywhere) TArray<TObjectPtr<UStaticMesh>> Rocks;
    UPROPERTY(EditAnywhere) TArray<TObjectPtr<UStaticMesh>> Shrubs;
    UPROPERTY(EditAnywhere) TArray<TObjectPtr<UStaticMesh>> Grass;
    UPROPERTY(EditAnywhere) TArray<TObjectPtr<UPCGGraph>> Graphs;
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
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hills") bool bReady = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hills") FGuid WorldId;
    UFUNCTION(BlueprintPure, Category="Hills") FVector GetStartLocation() const;
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
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Trunks;
    UPROPERTY() TObjectPtr<ACameraActor> AuditCamera;
    FString Slot;
    FString AuditDir;
    bool bAudit = false;
    bool bNullAudit = false;
    bool bAuditPassed = true;
    int32 AuditStage = 0;
    double AuditNext = 0;
    double StartSeconds = 0;
    bool bAwaitingTerrain = false;
    double TerrainReadyDeadline = 0;
    TArray<double> FrameSamples;
    double Noise(double X, double Y, uint32 Salt) const;
    double PathDistance(double X, double Y) const;
    double ForestWeight(double X, double Y) const;
    bool TreeCandidate(int32 GX, int32 GY, FTemperatePlacement& Out) const;
    void BuildTerrain();
    void BuildVegetation();
    void BuildValleyFog();
    void ResolveSession();
    void FinishTerrainStartup();
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
