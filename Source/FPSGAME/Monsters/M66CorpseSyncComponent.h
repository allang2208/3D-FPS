#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Animation/PoseSnapshot.h"
#include "M66CorpseSyncComponent.generated.h"
class AM66IncineratorMonster;

USTRUCT()
struct FM66CorpsePacket
{
    GENERATED_BODY()
    UPROPERTY() uint32 Revision=0;
    UPROPERTY() double ServerTime=0.;
    UPROPERTY() bool Frozen=false;
    UPROPERTY() FTransform MeshWorld;
    UPROPERTY() TArray<FTransform> LocalPose;
    bool NetSerialize(FArchive& Ar,UPackageMap* Map,bool& Success);
};
template<> struct TStructOpsTypeTraits<FM66CorpsePacket> : TStructOpsTypeTraitsBase2<FM66CorpsePacket>
{enum {WithNetSerializer=true};};

/** Authority alone simulates; remote bodies interpolate complete authored-scale poses. */
UCLASS()
class FPSGAME_API UM66CorpseSyncComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UM66CorpseSyncComponent();
    virtual void BeginPlay() override;
    virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    void Wake();
    const FM66CorpsePacket& State() const {return Packet;}
private:
    UPROPERTY(ReplicatedUsing=OnRep_Packet) FM66CorpsePacket Packet;
    UFUNCTION() void OnRep_Packet();
    UPROPERTY(Transient) TObjectPtr<AM66IncineratorMonster> Monster;
    FPoseSnapshot Pose;
    TArray<FTransform> PreviousPose;
    FTransform PreviousWorld;
    float BlendAge=.1f,PublishAge=0.f,PhysicsAge=0.f;
    bool bRemoteSetup=false,bImpactPlayed=false;
};
