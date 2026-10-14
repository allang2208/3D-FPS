#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RootCrownRootField.generated.h"

class ARootCrownRigPreview;
class UStaticMeshComponent;
class USphereComponent;
class UDynamicMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;

USTRUCT()
struct FRootCrownGroundPath
{
    GENERATED_BODY()
    UPROPERTY() TArray<FVector_NetQuantize10> Points;
};
UENUM()
enum class ERootCrownMinePhase:uint8 { Growing, Armed, Triggered, Exploded, Disarmed, Expired };
USTRUCT()
struct FRootCrownMineState
{
    GENERATED_BODY()
    UPROPERTY() FVector_NetQuantize10 Position;
    UPROPERTY() FVector_NetQuantizeNormal Normal=FVector::UpVector;
    UPROPERTY() ERootCrownMinePhase Phase=ERootCrownMinePhase::Growing;
    UPROPERTY() double ChangedAt=0.;
};

/** One server-owned group of three persistent proximity mines. */
UCLASS()
class FPSGAME_API ARootCrownRootField:public AActor
{
    GENERATED_BODY()
public:
    ARootCrownRootField();
    bool Prepare(ARootCrownRigPreview* Crown,APawn* Target);
    void FinishCast();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Layout) TObjectPtr<ARootCrownRigPreview> Source;
    UPROPERTY(ReplicatedUsing=OnRep_Layout) TArray<FRootCrownGroundPath> Paths;
    UPROPERTY(ReplicatedUsing=OnRep_Layout) TArray<FRootCrownMineState> Mines;
    UPROPERTY(Replicated) double StartedAt=0.;
    UPROPERTY(Replicated) float TriggerRadius=140.f;
    UPROPERTY(Replicated) float BlastRadius=280.f;
    UPROPERTY(Replicated) float FuseSeconds=.45f;
    UPROPERTY(Replicated) float Lifetime=25.f;
    float BlastDamage=60.f;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Knots;
    UPROPERTY() TArray<TObjectPtr<USphereComponent>> KnotShapes;
    UPROPERTY(Transient) TArray<TObjectPtr<UDynamicMeshComponent>> Veins;
    UPROPERTY(Transient) TArray<TObjectPtr<UDynamicMeshComponent>> Signals;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Fragments;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> VeinMIDs;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> SignalMIDs;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> KnotMIDs;
    UFUNCTION() void OnRep_Layout();
    bool TraceScene(const FVector& A,const FVector& B,FHitResult& Hit) const;
    bool FloorAt(const FVector& Expected,FVector& Out,FVector* Normal=nullptr) const;
    bool GroundPath(const FVector& Start,const FVector& End,FRootCrownGroundPath& Path) const;
    bool PathOpen(const FRootCrownGroundPath& Path) const;
    bool ExposureTo(int32 Index,APawn* Player,float& Distance) const;
    bool CanShoot(int32 Index) const;
    void ArmMines();
    void SetPhase(int32 Index,ERootCrownMinePhase Phase);
    void Detonate(int32 Index);
    void BuildPresentation();
    void BuildSignal(int32 Index);
    void UpdatePresentation(float Age);
    void PresentBurst(int32 Index,bool Damaging);
    float DamageKnot(int32 Index,float Damage);
    double Clock() const;
    float Age() const;
    float Health[3]{80.f,80.f,80.f};
    ERootCrownMinePhase Presented[3]{ERootCrownMinePhase::Growing,ERootCrownMinePhase::Growing,ERootCrownMinePhase::Growing};
    bool bPresentationBuilt=false;
};
