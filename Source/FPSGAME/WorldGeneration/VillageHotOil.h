#pragma once
#include "VillageDefenseSection.h"
#include "../Combat/CombatStatusFormula.h"
#include "VillageOilSpread.h"
#include "VillageHotOil.generated.h"

class UNiagaraComponent;
class UNiagaraSystem;
class UInstancedStaticMeshComponent;
class UDynamicMeshComponent;
class USplineMeshComponent;
class UPointLightComponent;
class UAudioComponent;

USTRUCT()
struct FVillageOilSurfacePacket
{
    GENERATED_BODY()
    UPROPERTY() TArray<uint8> Bytes;
    UPROPERTY() uint16 Serial=0;
    bool NetSerialize(FArchive& Ar,UPackageMap*,bool& Success);
    bool operator==(const FVillageOilSurfacePacket& Other) const {return Serial==Other.Serial;}
};
template<> struct TStructOpsTypeTraits<FVillageOilSurfacePacket> : TStructOpsTypeTraitsBase2<FVillageOilSurfacePacket>
{
    enum { WithNetSerializer=true, WithIdenticalViaEquality=true };
};

UCLASS()
class UVillageOilDamage : public UStatusMagicDamage { GENERATED_BODY() };

namespace VillageHotOil
{
    inline constexpr float Reach=300.f, Radius=500.f, Life=10.f, Exposure=.25f;
    FSoftObjectPath Asset(const TCHAR* Name);
    UMaterialInterface* BodyMaterial();
}

UCLASS()
class AVillageOilKettle final : public AVillageDefenseSection
{
    GENERATED_BODY()
public:
    AVillageOilKettle();
    static FSoftObjectPath MeshPath(){return VillageHotOil::Asset(TEXT("SM_OilHearth"));}
    virtual void Tick(float Delta) override;
protected:
    virtual void BeginPlay() override;
    virtual void ApplyHealth() override;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Liquid;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Bubbles;
    UPROPERTY() TObjectPtr<UNiagaraComponent> Vapour;
    UPROPERTY() TObjectPtr<UPointLightComponent> HearthGlow;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> SurfaceMID;
    struct FBubble { FVector2D XY; double Born=-1.,Life=.5,Radius=2.; };
    TArray<FBubble> Boil;
    FRandomStream BoilRandom;
    double NextBubble=0.,NextVent=0.,NextVapour=0.;
    friend class UVillageOilMotionReviewCommandlet;
    FVector2D VentXY=FVector2D::ZeroVector;
    int32 BurstIndex=0;
    void AdvanceBoil(double Now);
};

UCLASS()
class AVillageOilField final : public AActor
{
    GENERATED_BODY()
public:
    AVillageOilField();
    FVector_NetQuantize10 Lip;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float Delta) override;
private:
    UPROPERTY(Replicated) FVector_NetQuantize10 PourFrom;
    UPROPERTY(Replicated) double Started=0.;
    UPROPERTY(Replicated) uint16 FlowSeed=0;
    UPROPERTY(Replicated) uint64 UpgradeRanks=0;
    UPROPERTY(Replicated) bool bDirectSplash=false;
    UPROPERTY(Replicated) bool bIgnoreFriendlies=false;
    uint64 InitialUpgradeRanks=0;
    UPROPERTY(ReplicatedUsing=OnRep_Surface) FVillageOilSurfacePacket SurfacePacket;
public:
    void ConfigureTrebuchetSplash(const FVector& SplashOrigin,uint64 Ranks,bool bFriendlySafe)
    {
        Lip=SplashOrigin;
        InitialUpgradeRanks=Ranks;
        bDirectSplash=true;
        bIgnoreFriendlies=bFriendlySafe;
    }
private:
    float FieldDamage() const;
    float FieldRadius() const;
    float FieldLife() const;
    int32 FieldBurnStacks() const;
    UFUNCTION() void OnRep_Surface();
    void PublishSurface();
    friend class UVillageOilSurveySubsystem;
#if WITH_DEV_AUTOMATION_TESTS
    friend class FVillageTrebuchetHotOilTest;
#endif
    int32 SurveyStep(int32 Allowance);
    TUniquePtr<FVillageOilSpread> SurveyWork;
    double NextSupportCheck=0.;
    bool bSurfaceDirty=false;
    uint16 DisplayedSupportRevision=0;
    void PresentSurface();
    UPROPERTY() TObjectPtr<UDynamicMeshComponent> Pool;
    UPROPERTY() TObjectPtr<USplineMeshComponent> Stream;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Splash;
    TArray<FVector> SplashVelocity;
    void UpdateSplash(float WetAge);
    UPROPERTY() TObjectPtr<UNiagaraComponent> FireFront;
    UPROPERTY() TObjectPtr<UPointLightComponent> FireLight;
    UPROPERTY() TObjectPtr<UAudioComponent> FireAudio;
    struct FFireBand
    {
        FIntVector Path=FIntVector(-1,-1,-1);
        FVector Points[3];
        float Scale[3]={};
        float Arrival[3]={};
        float LastBirth=0.f;
        int32 Richest=INDEX_NONE;
    };
    TArray<FFireBand> FireBands;
    TArray<int32> HotCells;
    TArray<FVector4> UploadedFireRoots;
    TArray<FVector4> ScratchFireRoots;
    TBitArray<> ScratchSeenBits;
    FVector4 FireView=FVector4(0,0,0,0);
    int32 ActiveBands=0,ActivePockets=0;
    TArray<float> FireEvents;
    int32 FireEventCursor=0;
    int32 FireSurveyExtent=INDEX_NONE;
    float NextFireUpdate=0.f;
    float NextWindUpdate=0.f;
    bool bDetailedFire=false;
    bool bIgniteSoundPlayed=false;
    bool bFinalPulseDone=false;
    void BuildFireBands();
    void UpdateFireRoots(float WetAge);
    void UpdateFireFront(float WetAge);
    float BurnMagicAttack=0.f;
    TMap<TWeakObjectPtr<APawn>,double> NextContact;
    FVillageOilSpread Spread;
    double DropSeconds=0.;
    void UpdateStream(double Age);
    double NextSample=0.;
    bool bFollowedHands=false;
    void Pulse(double Now);
};
