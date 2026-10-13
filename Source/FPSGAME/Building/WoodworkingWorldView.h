#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Async/Future.h"
#include "WoodworkingWorldView.generated.h"

class UCameraComponent;
class UDynamicMeshComponent;
class UMaterialInterface;
class UWoodworkingSystem;
class UStaticMeshComponent;
struct FStreamableHandle;
struct FWoodworkingWorldMesh;

/** Local transient world presentation. Gameplay mask/timing/scoring remain in the subsystem. */
UCLASS(Transient,NotBlueprintable)
class FPSGAME_API AWoodworkingWorldView : public AActor
{
    GENERATED_BODY()
public:
    AWoodworkingWorldView();
    bool Prepare(APlayerController* Player,UStaticMeshComponent* Station,UWoodworkingSystem* System);
    void Enter();
    void Leave();
    bool Ready() const;
    bool Prepared() const;
    bool Failed() const {return bFailed;}
    bool MeshBudgetFailure() const {return bMeshBudgetFailure;}
    bool Healthy() const;
    const FString& Status() const {return Notice;}
    bool CursorToWork(FVector2D ViewportPixel,FVector2D& Work) const;
    void Zoom(float Steps);
    void ResetCamera();
    void InvalidateBoard();
    void SetScreenInsets(FMargin Insets);
    void SetReview(bool Enabled);
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void MaterialsReady();
    void UpdateCamera();
    void UpdateStock();
    void UpdateSawGuide();
    void RestorePlayer();
    void UpdateEffects(float DeltaSeconds);
    struct FChip {FVector Position,Velocity;float Age=0;};
    TArray<FChip> Chips;
    FMargin ScreenInsets=FMargin(20,100,20,230);
    FVector2D LastViewport=FVector2D::ZeroVector;
    uint64 LastCut=0,LastPeel=0;
    float WasteAge=2;
    FVector WasteStart=FVector::ZeroVector;
    FRotator WasteRotation=FRotator::ZeroRotator;
    bool bReview=false;
    int8 SawGuideState=-1;
    TWeakObjectPtr<APlayerController> PC;
    TWeakObjectPtr<AActor> PreviousView;
    TWeakObjectPtr<APawn> WorkingPawn;
    TWeakObjectPtr<UStaticMeshComponent> Workbench;
    TWeakObjectPtr<UWoodworkingSystem> System;
    TSharedPtr<FStreamableHandle> MaterialLoad;
    TFuture<TSharedPtr<FWoodworkingWorldMesh,ESPMode::ThreadSafe>> Pending;
    FVector SawOrigin=FVector::ZeroVector;
    double UnitsPerPixel=.22,ZoomFactor=1,NextMesh=0;
    uint64 Epoch=1;
    int32 AppliedRevision=-1,QueuedRevision=-1;
    FName ObservedPattern;
    FString Notice;
    bool bEntered=false,bHiddenPawn=false,bMaterialsReady=false,bFailed=false,bStockReady=false;
    bool bMeshBudgetFailure=false;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UDynamicMeshComponent> Stock;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UDynamicMeshComponent> Markings;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UDynamicMeshComponent> Effects;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UDynamicMeshComponent> Waste;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UDynamicMeshComponent> SawGuide;
    UPROPERTY() TSoftObjectPtr<UMaterialInterface> StockMaterial;
    UPROPERTY() TSoftObjectPtr<UMaterialInterface> MarkMaterial;
};
