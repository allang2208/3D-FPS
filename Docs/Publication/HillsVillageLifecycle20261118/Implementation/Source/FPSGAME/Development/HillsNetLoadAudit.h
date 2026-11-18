#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "HillsNetLoadAudit.generated.h"

/** Opt-in, copied-save two-process probe. Never created in a production world. */
UCLASS()
class UHillsNetLoadAudit : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
private:
    void Frame();
    void SyncLoad(const struct FNetSyncLoadReport& Report);
    void ActorSpawned(class AActor* Actor);
    void Save(const FString& Name,const TSharedRef<class FJsonObject>& Json);
    void Finish(bool Passed,const FString& Detail);
    void Event(const FString& Name);
    bool Exists(const TCHAR* Name) const;
    FString Output,Role,Phase=TEXT("loading");
    double Started=0,PreviousFrame=0,NextTick=0,ReadyAt=0,AllAt=0;
    int32 Step=0,MaxMonsters=0;
    bool Done=false,Late=false,ClockSet=false,Positioned=false;
    TWeakObjectPtr<class APawn> PositionedGuest;
    struct FFrameSample { double Time,Ms; uint64 Frame; FString Phase; };
    TArray<FFrameSample> Frames;
    TArray<TSharedPtr<class FJsonValue>> Events,Loads;
    FDelegateHandle FrameHandle,LoadHandle,SpawnHandle;
    FDelegateHandle GcBeginHandle,GcEndHandle;
    double GcStarted=0;
};
