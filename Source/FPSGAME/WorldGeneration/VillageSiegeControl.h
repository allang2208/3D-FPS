#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Components/LineBatchComponent.h"
#include "VillageSiegeEngine.h"
#include "VillageSiegeControl.generated.h"

class ACameraActor;
class AFPSGAMEPlayerController;
struct FInputKeyEventArgs;
class FPrimitiveComponentId;

/** The player keeps their own pawn while the controller owns the village engine's camera and inputs. */
UCLASS()
class FPSGAME_API UVillageSiegeControl : public UActorComponent
{
    GENERATED_BODY()
public:
    UVillageSiegeControl();
    bool Active() const { return IsValid(Station); }
    const AVillageSiegeEngine* OperatedStation() const { return Active()?Station.Get():nullptr; }
    bool IsAimingBallista() const { return Active() && !Station->IsTrebuchet(); }
    bool HandleInput(const FInputKeyEventArgs& Event);
    void AddHiddenOperatorComponents(const AActor* ViewTarget,TSet<FPrimitiveComponentId>& Hidden) const;
    UFUNCTION(Server,Reliable) void ServerEnter(AVillageSiegeEngine* Engine,APawn* RequestPawn);
    virtual void TickComponent(float Delta,ELevelTick Tick,FActorComponentTickFunction* Function) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Replicated) FRotator EntryAim=FRotator::ZeroRotator;
    UPROPERTY(ReplicatedUsing=OnRep_Station) TObjectPtr<AVillageSiegeEngine> Station;
    UFUNCTION() void OnRep_Station();
    UFUNCTION(Server,Reliable) void ServerLeave(AVillageSiegeEngine* Engine);
    UFUNCTION(Server,Unreliable) void ServerPointSiege(AVillageSiegeEngine* Engine,FRotator Bearing);
    UFUNCTION(Server,Reliable) void ServerFire(AVillageSiegeEngine* Engine,float Yaw,float Elevation);
    TWeakObjectPtr<APawn> SeatPawn;
    FVector SeatLocation=FVector::ZeroVector;
    TWeakObjectPtr<AActor> PreviousView;
    TWeakObjectPtr<AVillageSiegeEngine> ViewedStation;
    UPROPERTY(Transient) TObjectPtr<ACameraActor> Camera;
    UPROPERTY(Transient) TObjectPtr<ULineBatchComponent> TrajectoryLines;
    FVillageSiegeSight Sight;
    TArray<FBatchedLine> ImpactOutline;
    FVector OutlineCenter=FVector::ZeroVector,OutlineNormal=FVector::UpVector;
    double OutlineRefreshAt=-1.;
    double OutlineRadius=0.;
    bool bOutlineHitUnit=false;
    void DrawImpactOutline(const FVector& Normal,double Now);
    float AimYaw=0.f,AimElevation=0.f;
    double NextPreview=0.;
    double LastBearingSend=-2.;
    FRotator LastSentBearing=FRotator::ZeroRotator;
    bool bMoveLocked=false;
    bool SessionValid() const;
    void ReleaseSeat();
    void RestoreView();
    void UpdateSight();
};
