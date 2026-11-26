#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelInventoryTypes.h"
#include "Engine/TimerHandle.h"
#include "../Movement/StableHorseMarket.h"
#include "ColdSteelShopModel.generated.h"
class UColdSteelStatusModel;
class AVillageArtisanMerchant;
class AVillageBaker;
class AVillageGunshopCounter;
class AVillageHerbalist;
class AVillageTavernKeeper;
struct FColdSteelResidentMenu;
struct FColdSteelInventoryRequest;
struct FColdSteelShopSelection { FString Id; int64 Count = 1; };
struct FColdSteelShopSaleLine { FColdSteelItem Item; int64 Count = 1; int64 UnitPrice = 0; };
struct FColdSteelShopQuote
{
    TArray<FColdSteelShopSaleLine> Lines;
    int64 Total = 0;
    uint32 BasketRevision = 0;
};
DECLARE_MULTICAST_DELEGATE(FColdSteelShopChanged);

/** Pending selections stay in the backpack. A confirmed trade is one profile commit. */
UCLASS()
class FPSGAME_API UColdSteelShopModel : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    void BeginSession();
    bool BeginArtisanSession(AVillageArtisanMerchant* Seller);
    bool BeginBakerSession(AVillageBaker* Seller);
    bool BeginGunshopSession(AVillageGunshopCounter* Counter);
    bool SellsSingleItems() const;
    bool BeginTavernSession(AVillageTavernKeeper* Seller);
    bool BeginHerbalistSession(AVillageHerbalist* Seller);
    bool BeginStableSession(AActor* Seller);
    bool IsStableShop() const;
    bool BuyHorse(FGuid Id);
    const TArray<FStableHorseOffer>& HorseOffers() const { return StableOffers; }
    int32 HorseMarketDay() const { return StableDay; }
    bool IsTradePending() const { return bCommitting; }
    bool IsArtisanShop() const { return !Merchant.IsExplicitlyNull(); }
    bool IsTavernShop() const;
    bool IsHerbalistShop() const;
    bool IsPurchaseOnly() const { return Menu != nullptr; }
    void WatchSeller(FSimpleDelegate OnLeft);
    FString MerchantName() const;
    static bool ExecuteNetworkTrade(UColdSteelStatusModel* Profile,const FColdSteelInventoryRequest& Request,const FString& HostSlot,FString& Reason);
    void NetworkTradeFinished(bool Success,const FString& Reason);
    void EndSession();
    virtual void Deinitialize() override;
    bool IsOpen() const { return bOpen; }
    static constexpr int32 MaxSaleLines = 128;
    const TArray<FColdSteelItem>& Stock() const { return Shelf; }
    const TArray<FColdSteelShopSelection>& Selection() const { return Basket; }
    int64 BuyPrice(const FString& Definition) const;
    int64 SellPrice(const FColdSteelItem& Item) const;
    bool CanSell(const FColdSteelItem& Item) const;
    bool AddToSale(const FString& Id);
    void RemoveFromSale(const FString& Id);
    bool SetSaleCount(const FString& Id, int64 Count);
    void ClearSale();
    bool QuoteSale(FColdSteelShopQuote& Out) const;
    bool Buy(const FString& StockItemId, int32 Count);
    bool ConfirmSale(const FColdSteelShopQuote& Quote);
    const FString& ResultMessage() const { return Message; }
    FColdSteelShopChanged OnChanged;
private:
    bool OpenProfile();
    bool BeginMenuSession(AActor* Seller);
    bool SellerHasLeft() const;
    void RefreshArtisanStock();
    bool RefreshHorseOffers();
    TWeakObjectPtr<class AFPSWeatherManager> StableClock;
    TArray<FStableHorseOffer> StableOffers;
    FGuid StableProfile;
    int32 StableDay=INDEX_NONE;
    void ProfileChanged();
    bool Fail(const FString& Reason);
    bool CanTrade();
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    FDelegateHandle ProfileHandle;
    TWeakObjectPtr<AVillageArtisanMerchant> Merchant;
    TWeakObjectPtr<AActor> MenuSeller;
    const FColdSteelResidentMenu* Menu = nullptr;
    TWeakObjectPtr<class APawn> BuyerPawn;
    FTimerHandle ReachTimer;
    FDelegateHandle StockHandle;
    TArray<FColdSteelItem> Shelf;
    TArray<FColdSteelShopSelection> Basket;
    mutable TMap<FString,FVector2D> SaleRules;
    FString Message;
    uint32 BasketRevision = 0;
    bool bOpen = false;
    bool bCommitting = false;
    bool bPendingSale = false;
    uint32 PendingSaleRevision = 0;
};
