#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HillsContinuityAudit.generated.h"

class APlayerController;
class AFPSGAMECharacter;
class ANurseZombie;
class ATemperateHillsWorld;
class AChapelShrine;
class AFPSWeatherManager;
class FJsonValue;

/** Explicit opt-in fixture, restricted to an isolated copied-save project. */
UCLASS()
class AHillsContinuityAudit : public AActor
{
    GENERATED_BODY()
public:
    AHillsContinuityAudit();
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) int32 Phase=0;
    UPROPERTY(Replicated) TObjectPtr<AActor> Target;
    UPROPERTY(Replicated) FVector Point=FVector::ZeroVector;
    UPROPERTY(Replicated) float Expected=0.f;
    UFUNCTION(Server,Reliable) void ServerReport(int32 Step,bool Pass,const FString& Text);
    UFUNCTION(Client,Reliable) void ClientExit();
    bool Director=false;
private:
    UFUNCTION() void PlayerWasHit(AActor* Victim,float Damage,const class UDamageType* Type,AController* SourceController,AActor* Causer);
    void RunHost();
    void RunClient();
    void Send(int32 Step,AActor* Object=nullptr,FVector Position=FVector::ZeroVector,float Value=0.f);
    void Record(const FString& Case,bool Pass,const FString& Detail=FString());
    void Finish();
    bool SetPewPositions();
    bool SetGroundPositions();
    bool Bind();
    double Started=0.,Began=0.,NextLog=0.;
    int32 Previous=-1,Reported=0;
    bool Requested=false,Passed=true,SawEnter=false,SawExit=false,GroundFloor=false,Jumped=false;
    bool WalkStarted=false;
    FString Detail;
    FVector StartPosition=FVector::ZeroVector,GuestSeat=FVector::ZeroVector,GuestAim=FVector::ZeroVector;
    FTransform Pew;
    int32 GuestSlot=-1;
    float PlayerHealth=0.f;
    int32 NativePlayerHits=0;
    bool Restart=false,WaitingLogout=false;
    TWeakObjectPtr<APlayerController> Host,Guest;
    TWeakObjectPtr<AHillsContinuityAudit> Peer;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AChapelShrine> Shrine;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    TWeakObjectPtr<ANurseZombie> Bait;
    TArray<TSharedPtr<FJsonValue>> Checks;
};
