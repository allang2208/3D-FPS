#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Monsters/UnknownHumanoid.h"
#include "UnknownJoinAudit.generated.h"

UCLASS()
class AUnknownJoinAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) TArray<TObjectPtr<AUnknownHumanoid>> Subjects;
    UPROPERTY(Replicated) TArray<FUnknownLoadout> Loadouts;
    UPROPERTY(Replicated) TArray<FUnknownMotion> Motions;
    UPROPERTY(Replicated) TObjectPtr<class AFPSGAMECharacter> Wounded;
    UPROPERTY(Replicated) TObjectPtr<class AFPSIceWall> Wall;
    UPROPERTY(Replicated) float ExpectedHP=0;
    UPROPERTY(Replicated) double EndsAt=0;
    UPROPERTY(Replicated) int32 Phase=0;
    UPROPERTY(Replicated) int32 Probe=-1;
    UFUNCTION(Server,Reliable) void ServerObserved(int32 Index,bool bPassed,const FString& Detail);
    UFUNCTION(Client,Reliable) void ClientExit();
    int32 Finished=-1;
    bool Passed=true;
private:
    bool Seeded=false,Attached=false;
    int32 Watching=-1,Reported=-1;
    double Started=0,ExitAt=-1;
};

UCLASS()
class AUnknownJoinAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AUnknownJoinAuditGameMode();
    virtual void StartPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Logout(AController* Player) override;
    virtual void Tick(float Delta) override;
    void Observe(int32 Index,bool Passed,const FString& Detail);
private:
    UPROPERTY() TObjectPtr<AUnknownJoinAuditController> Guest;
    UPROPERTY() TArray<TObjectPtr<AUnknownHumanoid>> Subjects;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Wounded;
    UPROPERTY() TObjectPtr<AFPSIceWall> Wall;
    UPROPERTY() TObjectPtr<class UColdSteelStatusModel> PreviousModel;
    TWeakObjectPtr<APawn> PreviousPawn;
    TArray<TSharedPtr<class FJsonValue>> Rows;
    int32 Phase=0,Prepared=-1;
    double Started=0,ExitAt=-1,EndsAt=0;
    float SavedHP=0;
    bool Passed=true,Leaving=false;
    void Save();
};
