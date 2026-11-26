#include "ApprenticeMaterials.h"
#include "../Building/CraftingSystem.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"

bool ApprenticeMaterials::Grant(UColdSteelStatusModel& Model, FColdSteelProfile&& Next, const FString& GuestSlot,
    const FString& Receipt, const TArray<FColdSteelCraftingInput>& Inputs, FString& Message)
{
    auto* Pawn = Model.RuntimePawn();
    if (!Pawn || !Pawn->HasAuthority() || Inputs.IsEmpty() || Model.IsStagingNetworkContainer())
    {
        Message = TEXT("工坊材料暂时无法发放，请稍后再试。");
        return false;
    }
    if (!GuestSlot.IsEmpty() || !Pawn->IsLocallyControlled())
    {
        const auto* Owner = Pawn->GetPlayerState<AColdSteelPlayerState>();
        if (!Owner || Owner->GetShadowModel() != &Model || GuestSlot.IsEmpty() || Owner->CampfireGuestSlot() != GuestSlot)
        {
            Message = TEXT("角色档案正在同步，请稍后再试。");
            return false;
        }
    }
    TArray<FString> Granted;
    for (const auto& Input : Inputs)
    {
        const FColdSteelItem Item = Model.CreateItem(Input.Item, Input.Count);
        if (Input.Count <= 0 || Item.Data.IsEmpty())
        {
            Message = TEXT("教学材料资料尚未就绪。");
            return false;
        }
        if (!ColdSteelInventory::Insert(Next.Items, Item))
        {
            Message = TEXT("背包装不下整套材料。腾出空间，再来领取。");
            return false;
        }
        Granted.Add(FString::Printf(TEXT("%s × %lld"), *ColdSteelInventory::Text(Item, TEXT("name")), Input.Count));
    }
    if (!Model.CommitCampfireState(MoveTemp(Next), Receipt, GuestSlot))
    {
        Message = Model.ResultMessage();
        return false;
    }
    Message = TEXT("材料已放入背包：") + FString::Join(Granted, TEXT("、")) + TEXT("。");
    return true;
}
