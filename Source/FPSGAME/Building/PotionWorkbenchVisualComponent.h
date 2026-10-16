#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AlchemyTypes.h"
#include "AlchemyTabletop.h"
#include "PotionWorkbenchVisualComponent.generated.h"
class UStaticMeshComponent;
class USplineMeshComponent;
class UMaterialInstanceDynamic;
class UAlchemyManualComponent;
class UInstancedStaticMeshComponent;
class UAudioComponent;
class USoundBase;
class UTextRenderComponent;
struct FStreamableHandle;

UCLASS()
class FPSGAME_API UPotionWorkbenchVisualComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPotionWorkbenchVisualComponent();
    void Configure(UStaticMeshComponent* Body);
    void Present(const FAlchemyBenchState& State);
    bool Ready() const;
    bool Failed() const;
    bool MatchesSession(const APawn* Pawn,const FString& JobId) const {return bReady&&State.Operator.Get()==Pawn&&!JobId.IsEmpty()&&State.JobId==JobId;}
    FTransform ToolGrip() const;
    FTransform BottleGrip() const;
    FTransform StirFrame() const;
    FVector FocusPoint() const;
    EAlchemyOp HandTool() const;
    FAlchemyTableHit TraceTabletop(const FVector& RayOrigin,const FVector& RayDirection) const;
    bool StirPoint(const FVector& RayOrigin,const FVector& RayDirection,FVector& LocalPoint) const;
    void SetHoverTarget(const FAlchemyTableHit& Hit,bool Enabled);
    virtual void TickComponent(float Delta,ELevelTick Tick,FActorComponentTickFunction* Fn) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class AAlchemyManualNetAuditController;
    void Loaded();
    void UpdateBook();
    void UpdateThermometer();
    void UpdateIngredients();
    void CreateInteractionParts();
    void AnimateIngredients(float Time,bool Pouring);
    void AnimateBottling(float Time,float SurfaceZ,bool Active);
    void UpdateTransfer(float Time,float SurfaceZ,bool Active);
    void UpdateHoverProxies();
    void Sound(const TCHAR* Name,const FVector& LocalPoint);
    UStaticMeshComponent* Part(const TCHAR* Name) const;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Original;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> IngredientParts;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> IngredientCaps;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> HoverProxies;
    TArray<TWeakObjectPtr<UStaticMeshComponent>> HoverSources;
    TArray<FTransform> IngredientRest;
    TArray<FVector> IngredientMouth;
    TArray<bool> IngredientGranular;
    float UnitFill=0;
    UPROPERTY(Transient) TArray<TObjectPtr<USplineMeshComponent>> FlowSegments;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> TransferDrops;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> TransferMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GrainMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BottleMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BottlingMaterial;
    int32 BottleSoundSerial=INDEX_NONE;
    int32 ImpactSerial=-1;
    TMap<FString,FSoftObjectPath> IngredientAssets;
    FName IngredientRecipe;
    FString IngredientJobId;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> LiquidMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WaterMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RuneMaterial;
    UPROPERTY(Transient) TObjectPtr<UAlchemyManualComponent> Manual;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Steam;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Bubbles;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> UpperSand;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SteamMaterial;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<USoundBase>> Sounds;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> GrindAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> BoilAudio;
    UPROPERTY(Transient) TObjectPtr<UTextRenderComponent> TemperatureReadout;
    int32 DisplayedTemperature=MIN_int32;
    FAlchemyBenchState State;
    TSharedPtr<FStreamableHandle> Loading;
    bool bReady=false,bLoadFinished=false,bReturningStirrer=false;
    float Motion=0,VisualTime=0,StirrerReturnAt=0,EffectsClock=0;
    float DisplayFill=0,WaterRippleClock=0;
    FLinearColor AppliedWaterColor=FLinearColor(-1,-1,-1,-1);
    FLinearColor DisplayColor=FLinearColor(.13f,.19f,.16f),BeforePourColor=DisplayColor;
    int32 WaterObservedSerial=-1;
    EAlchemyOp PreviousTool=EAlchemyOp::Stop;
    FTransform StirrerReturnFrom;
    int32 ObservedSerial=-1,ObservedPage=-1;
    FName ObservedRecipe;
};
