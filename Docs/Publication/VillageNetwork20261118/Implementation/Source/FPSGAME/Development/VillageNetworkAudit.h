#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VillageNetworkAudit.generated.h"

class ATemperateHillsWorld;
class AChapelNun;
class AVillageDefenseGate;
class AVillageDefenseSection;
class ANurseZombie;
class UColdSteelStatusModel;

/** Explicit opt-in fixture. Production controllers, profiles and RPCs remain in use. */
UCLASS()
class AVillageNetworkAudit : public AActor
{
    GENERATED_BODY()
public:
    AVillageNetworkAudit();
    virtual void Tick(float Dt) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) int32 Phase=0;
    UPROPERTY(Replicated) TObjectPtr<AActor> Target;
    UPROPERTY(Replicated) FVector Position=FVector::ZeroVector;
    UPROPERTY(Replicated) FVector Aim=FVector::ZeroVector;
    UPROPERTY(Replicated) float ExpectedHealth=0.f;
    UFUNCTION(Server,Reliable) void ServerResult(int32 Case,bool Passed,const FString& Detail);
    UFUNCTION(Client,Reliable) void ClientFinish();
    bool bDirector=false;
private:
    void RunClient();
    void RunHost();
    void Record(const FString& Name,bool Passed,const FString& Detail=FString());
    void Send(int32 Case,AActor* Actor=nullptr);
    void Finish();
    bool Bind();
    bool Setup();
    void PlaceConversation();
    bool StartClimb();
    bool StartRaid();
    FString RaidStatus() const;
    TWeakObjectPtr<APlayerController> Host,Guest,PreviousGuest;
    TWeakObjectPtr<AVillageNetworkAudit> Peer;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AChapelNun> Nun;
    TWeakObjectPtr<AVillageDefenseGate> Gate;
    TWeakObjectPtr<AVillageDefenseSection> Wall;
    TWeakObjectPtr<ANurseZombie> Raider;
    TArray<TSharedPtr<class FJsonValue>> Checks;
    FGuid GuestIdentity;
    int32 Stage=0,Observed=0,PreviousPhase=0;
    bool bPassed=true,bPeerPassed=false,bRequested=false,bReported=false,bFinished=false;
    FString PeerDetail;
    double Started=0.,StageAt=0.,ClientAt=0.,Next=0.;
    double NextRaidReport=0.;
    float BeforeHealth=0.f;
    FVector RaidStart=FVector::ZeroVector;
    uint32 RequestsAtStart=0,ConversationSession=0;
};

namespace VillageNetAudit
{
bool Enabled();
FString Output();
void Save(const FString& Name,const TSharedRef<class FJsonObject>& Data);
ATemperateHillsWorld* FindHills(UWorld* World);
AChapelNun* FindNun(UWorld* World);
UColdSteelStatusModel* Model(APlayerController* PC);
void Place(APlayerController* PC,FVector Position,FVector Aim,bool Walking=false);
bool GatePose(AVillageDefenseGate* Gate,bool Open,FString& Detail);
bool ShopState(UWorld* World,FString& Detail);
bool Facing(AChapelNun* Nun,APlayerController* PC,FString& Detail);
}
