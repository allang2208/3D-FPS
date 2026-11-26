#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelContainerSearchSubsystem.generated.h"

class APlayerController;
class UColdSteelInventoryReply;

// Discovery is personal and temporary; the existing container remains the inventory authority.
UCLASS()
class UColdSteelContainerSearchSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    static bool CanAccess(const APawn* Pawn,const AActor* Target);
    static bool Resolve(AActor* Target,FString& Key,int32& Pages,FString& Caption);
    static bool Hidden(const APlayerController* Player,const FColdSteelItem& Item);
    void Begin(APlayerController* Player,AActor* Target);
    void Close(APlayerController* Player,AActor* Target);
    void CloseLocal(APlayerController* Player,AActor* Target);
    bool IsActive(const APlayerController* Player,const AActor* Target=nullptr) const;
    bool HasViewers(const AActor* Target) const;
    bool IsSearching(const APlayerController* Player,const FString& Key) const;
    void FillView(APlayerController* Player,UColdSteelInventoryReply& Reply);
    void ApplyView(APlayerController* Player,AActor* Target,const UColdSteelInventoryReply& Reply);
    bool ValidateChange(APlayerController* Player,const TArray<FColdSteelItem>& Before,const TArray<FColdSteelItem>& After,FString& Reason) const;
    void ObserveChange(APlayerController* Player,const TArray<FColdSteelItem>& Before,const TArray<FColdSteelItem>& After);
    float Progress(const APlayerController* Player,const FString& ItemId) const;
    FString Status(const APlayerController* Player,const FString& Key) const;
private:
    struct FRecord
    {
        TSet<FString> Revealed;
        FString Searching;
        float Elapsed=0,Duration=0;
        int32 Total=0,Found=0;
    };
    struct FViewer
    {
        TMap<FString,FRecord> Records;
        TWeakObjectPtr<AActor> Anchor;
        FString Key;
        double UpdatedAt=0;
    };
    TMap<TWeakObjectPtr<APlayerController>,FViewer> Viewers;
    TMap<FString,float> RaritySeconds;
    float EquipmentSeconds=1.2f;
    bool bSettingsLoaded=false;
    float TickAccumulator=0;
    static FString Canonical(const FString& Key);
    const FViewer* Find(const APlayerController* Player) const;
    const TArray<FColdSteelItem>* Contents(APlayerController* Player,const FString& Key) const;
    float DurationFor(const FColdSteelItem& Item);
    bool Reconcile(FRecord& Record,const FString& Key,const TArray<FColdSteelItem>& Items);
    void Notify(APlayerController* Player,AActor* Target);
};
