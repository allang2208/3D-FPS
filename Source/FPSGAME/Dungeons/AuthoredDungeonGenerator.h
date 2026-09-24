#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AuthoredDungeonLighting.h"
#include "AuthoredDungeonGenerator.generated.h"

struct FAuthoredDungeonBuildState;
class UCharacterMovementComponent;

/** Rigid authored modules, seeded socket assembly and reserved branch sectors. */
UCLASS()
class FPSGAME_API AAuthoredDungeonGenerator : public AActor
{
    GENERATED_BODY()
public:
    AAuthoredDungeonGenerator();
    UPROPERTY(EditAnywhere, Category="Dungeon") int32 PreviewSeed=92247;
    UPROPERTY(EditAnywhere, Category="Dungeon") bool bRandomizeOnEntry=true;
    UPROPERTY(EditAnywhere, Category="Dungeon", meta=(MultiLine=true)) FString ModuleCatalogJson;
    /** Hard references keep every authored mesh/material available in packaged builds. */
    UPROPERTY(EditAnywhere, Category="Dungeon") TArray<TObjectPtr<UObject>> ModuleAssets;
    UPROPERTY(VisibleAnywhere, Category="Dungeon") int32 GeneratedSeed=0;
    UPROPERTY(VisibleAnywhere, Category="Dungeon") FString LayoutDescription;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dungeon") FString LayoutManifestJson;
    UFUNCTION(CallInEditor, Category="Dungeon") void GeneratePreview();
    /** On-demand CPU preparation report. Never represents GPU work or frame-time savings. */
    FString GetGenerationMetricsJson() const;
    bool IsPreparationPending() const { return BuildState.IsValid(); }
protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    UPROPERTY() TArray<TObjectPtr<AActor>> GeneratedActors;
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> GenerationResources;
    TSharedPtr<FAuthoredDungeonBuildState, ESPMode::ThreadSafe> BuildState;
    TArray<TWeakObjectPtr<UCharacterMovementComponent>> HeldMovement;
    uint64 GenerationSerial = 0;
    FString LastGenerationMetricsJson;
    void PrepareAssembly();
    void PumpAssembly(bool bSynchronous);
    void FinishAssembly(bool bSynchronous);
    void RollbackAssembly();
    void CancelAssembly();
    void HoldPlayers();
    void ReleasePlayers();
    void OwnGenerated(AActor* Actor, int32 ModuleIndex);
    UObject* ResolveGenerationAsset(const FString& Path);
    void Generate(int32 Seed);
    void ClearGenerated();
    void UpdateRoomLighting();
    void StartRoomLighting();
    void ResetRoomLighting();
    TArray<FAuthoredDungeonLightModule> LightModules;
    FTimerHandle RoomLightingTimer;
    double LastLightingUpdateSeconds = 0.0;
    bool bLightingOptimizationApplied = false;
};
