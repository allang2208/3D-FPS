#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "ColdSteelInventoryTypes.generated.h"

USTRUCT(BlueprintType)
struct FColdSteelItem
{
    GENERATED_BODY()
    UPROPERTY() FString InstanceId;
    UPROPERTY() FString Definition;
    // Full source data (including processing/attachment fields); never stripped on transfer.
    UPROPERTY() FString Data;
    UPROPERTY() int64 Count = 1;
    UPROPERTY() int64 StackMax = 1;
    UPROPERTY() int32 Width = 1;
    UPROPERTY() int32 Height = 1;
    UPROPERTY() int32 Place = 0; // 0 backpack, 1 equipment, 2 world, 4 warehouse (3 is UI hotbar)
    UPROPERTY() int32 Cell = 0;
    UPROPERTY() int32 BackpackCell = -1;
    UPROPERTY() FString Map;
    UPROPERTY() FVector Position = FVector::ZeroVector;
    UPROPERTY() float Cooldown = 0;
    UPROPERTY() int32 Magazine = 30;
    UPROPERTY() int32 Reserve = 90;
};

USTRUCT()
struct FColdSteelProfile
{
    GENERATED_BODY()
    UPROPERTY() int32 Version = 1;
    UPROPERTY() int64 Generation = 0;
    UPROPERTY() FString Name = TEXT("轮回者");
    UPROPERTY() FString Class = TEXT("初心者");
    UPROPERTY() int32 Level = 1;
    UPROPERTY() int64 Experience = 0;
    UPROPERTY() int32 Points = 0;
    UPROPERTY() int32 Kills = 0;
    UPROPERTY() int32 ActiveWeaponSlot = 6;
    UPROPERTY() TMap<FName, int32> Attributes;
    UPROPERTY() TArray<FColdSteelItem> Items;
    UPROPERTY() TArray<FString> Hotbar;
    UPROPERTY() TArray<FString> HotbarDefinitions;
    UPROPERTY() float Health = 200;
    UPROPERTY() float Mana = 250;
    UPROPERTY() int32 WarehousePages = 5;
    UPROPERTY() TArray<FString> ArmoryReceived;
};

UCLASS()
class UColdSteelProfileSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FColdSteelProfile Profile;
};

struct FColdSteelProposal
{
    bool bValid = false;
    int64 Revision = 0;
    int32 ActiveWeaponSlot = -1;
    FString Reason;
    TArray<FColdSteelItem> Items;
};

namespace ColdSteelInventory
{
    FPSGAME_API FString Text(const FColdSteelItem& Item, const TCHAR* Key);
    FPSGAME_API double Number(const FColdSteelItem& Item, const TCHAR* Key, double Default = 0);
    FPSGAME_API bool Flag(const FColdSteelItem& Item, const TCHAR* Key);
    FPSGAME_API FIntPoint Footprint(const FColdSteelItem& Item);
    FPSGAME_API bool Compatible(const FColdSteelItem& A, const FColdSteelItem& B);
    FPSGAME_API bool CanEquip(const FColdSteelItem& Item, int32 Slot);
    FPSGAME_API bool Locked(const TArray<FColdSteelItem>& Items, int32 Slot);
    FPSGAME_API int32 Owner(const TArray<FColdSteelItem>& Items, int32 Place, int32 Cell);
    FPSGAME_API bool Fits(const TArray<FColdSteelItem>& Items, const FColdSteelItem& Item, int32 Cell);
    FPSGAME_API bool Insert(TArray<FColdSteelItem>& Items, FColdSteelItem Item, int32 Preferred = -1);
    FPSGAME_API FColdSteelProposal Move(const TArray<FColdSteelItem>& Items, const FString& Id, int32 Place, int32 Cell);
    FPSGAME_API bool Validate(const FColdSteelProfile& Profile, FString& Reason);
    FPSGAME_API const TArray<FString>& SlotNames();
}
