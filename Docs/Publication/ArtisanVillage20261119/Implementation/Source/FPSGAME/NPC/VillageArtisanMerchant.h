#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "ResidentConversation.h"
#include "VillageArtisanMerchant.generated.h"

class USkeletalMeshComponent;
class UColdSteelStatusModel;
struct FColdSteelItem;

USTRUCT()
struct FVillageArtisanOffer
{
    GENERATED_BODY()
    UPROPERTY() FName Definition;
    UPROPERTY() FGuid Lot;
    UPROPERTY() int32 QualityPercent = 0;
};

UCLASS(Abstract)
class FPSGAME_API AVillageArtisanMerchant : public ACharacter
{
    GENERATED_BODY()
public:
    AVillageArtisanMerchant();
    static constexpr float CapsuleHalfHeight = 91.f;
    void SetLocalConversation(APlayerController* Player);
    bool CanTradeWith(const APawn* Pawn) const;
    const TCHAR* MerchantName() const { return bCarpenter ? TEXT("木匠") : TEXT("铁匠"); }
    bool IsCarpenterMerchant() const { return bCarpenter; }
    const TCHAR* TradeMode(bool bSale) const;
    const TArray<FVillageArtisanOffer>& Stock() const { return Offers; }
    bool MakeStockItem(const UColdSteelStatusModel& Profile, const FVillageArtisanOffer& Offer, FColdSteelItem& Out) const;
    void RestockSoldLot(const FGuid& Lot);
    FSimpleMulticastDelegate OnStockChanged;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

protected:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
    bool bCarpenter = false;
    virtual void BeginPlay() override;
    FResidentConversationFacing ConversationFacing;

private:
    UPROPERTY(ReplicatedUsing=OnRep_Offers) TArray<FVillageArtisanOffer> Offers;
    UFUNCTION() void OnRep_Offers();
    bool SellsDefinition(const FString& Id, const FString& Data) const;
    void Restock(FVillageArtisanOffer& Offer) const;
};
