#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MagicArrowRainTypes.h"
#include "../Weapons/Bow/AuroraBeamVisual.h"
#include "FPSMagicArrowRain.generated.h"
class UInstancedStaticMeshComponent;
class UColdSteelStatusModel;
class UAudioComponent;
struct FStreamableHandle;

USTRUCT()
struct FMagicArrowRainFlight
{
    GENERATED_BODY()
    UPROPERTY() FVector Start=FVector::ZeroVector;
    UPROPERTY() FVector Ground=FVector::ZeroVector;
    UPROPERTY() FVector Burst=FVector::ZeroVector;
    UPROPERTY() FVector SurfaceNormal=FVector::UpVector;
    UPROPERTY() double StartedAt=0;
    UPROPERTY() float FlightSeconds=1.f;
    UPROPERTY() float Radius=400.f;
    UPROPERTY() int32 Count=28;
    UPROPERTY() int32 Seed=0;
    UPROPERTY() bool bLaunched=false;
    UPROPERTY() bool bAuroraBeam=false;
    UPROPERTY() FAuroraBeamContact AuroraBlock;
};

UCLASS()
class FPSGAME_API AFPSMagicArrowRain : public AActor
{
    GENERATED_BODY()
    friend class UBowSkillTrainingAuditCommandlet;
public:
    AFPSMagicArrowRain();
    void Launch(UColdSteelStatusModel* Model,const FMagicArrowRainCast& Spell,
        const FVector& Start,const FVector& Ground,const FVector& Burst);
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Flight) FMagicArrowRainFlight Flight;
    UPROPERTY(ReplicatedUsing=OnRep_Blocked) bool bBlocked=false;
    void ApplyAuroraBeam();
    TWeakObjectPtr<AAuroraBeamVisual> Laser;
    UFUNCTION() void OnRep_Flight();
    UFUNCTION() void OnRep_Blocked();
    UFUNCTION(NetMulticast,Unreliable) void MulticastBlockedImpact(FVector_NetQuantize Point);
    UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Arrows;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Trails;
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> Assets;
    TSharedPtr<FStreamableHandle> Load;
    TWeakObjectPtr<UColdSteelStatusModel> Model;
    FMagicArrowRainCast Spell;
    TArray<FVector> RainStarts,RainEnds,RainNormals;
    TArray<float> Delays,TravelTimes;
    struct FDescentCue { float Time=0.f,Pitch=1.f,Gain=1.f;FVector Point=FVector::ZeroVector; };
    TArray<FDescentCue,TInlineAllocator<5>> DescentCues;
    TArray<TWeakObjectPtr<UAudioComponent>,TInlineAllocator<5>> DescentAudio;
    int32 NextDescentCue=0;
    bool bReady=false,bBurstPlayed=false,bImpactPlayed=false,bDamageDone=false,bRainBuilt=false;
    float PreviousFraction=0.f;
    double Clock() const;
    void BuildRain();
    void BuildDescentAudio();
    void PlayDescentAudio(float BurstAge);
    void StopDescentAudio();
    void Present(float Age);
    void Smoke(bool bImpact,float Elapsed=0.f);
    void Sound(const TCHAR* Name,const FVector& Point,float Volume);
};
