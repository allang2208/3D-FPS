#include "ColdSteelCurrency.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelStatusModel.h"

bool ColdSteelCurrency::Credit(FColdSteelProfile& P,int64 Amount)
{
    if(Amount<=0 || P.Souls<0 || P.Souls>MaxSouls || Amount>MaxSouls-P.Souls)return false;
    P.Souls+=Amount;return true;
}

bool ColdSteelCurrency::Debit(FColdSteelProfile& P,int64 Amount)
{
    if(Amount<=0 || P.Souls<Amount)return false;
    P.Souls-=Amount;return true;
}

bool ColdSteelCurrency::Normalize(FColdSteelProfile& P,bool& Changed,FString& Reason)
{
    Changed=false;
    if(P.SoulCurrencyVersion<0 || P.SoulCurrencyVersion>1 || P.Souls<0 || P.Souls>MaxSouls || P.ServerSoulCredits<0 || P.ServerSoulCredits>MaxSouls || P.ServerSoulDebits<0 || P.ServerSoulDebits>MaxSouls)
    {Reason=TEXT("灵魂余额或版本无效，原档保留");return false;}
    int64 Total=P.Souls;
    TSet<FString> RetiredIds;
    for(const auto& Item:P.Items)if(IsCurrency(Item.Definition))
    {
        if(Item.Count<=0 || Item.Count>MaxSouls-Total || Item.InstanceId.IsEmpty() || RetiredIds.Contains(Item.InstanceId))
        {Reason=TEXT("旧货币数量无效，原档保留");return false;}
        Total+=Item.Count;RetiredIds.Add(Item.InstanceId);
    }
    Changed=P.SoulCurrencyVersion!=1 || !RetiredIds.IsEmpty();
    P.Souls=Total;P.SoulCurrencyVersion=1;
    P.Items.RemoveAll([](const auto& Item){return IsCurrency(Item.Definition);});
    // Existing tribute instances carry presentation snapshots as well as their stable effect keys.
    for(auto& Item:P.Items)if(Item.Data.Contains(TEXT("金币")))
    {Item.Data.ReplaceInline(TEXT("金币"),TEXT("灵魂"),ESearchCase::CaseSensitive);Changed=true;}
    for(int32 Index=0;Index<P.Hotbar.Num();++Index)
        if(RetiredIds.Contains(P.Hotbar[Index]) || (P.HotbarDefinitions.IsValidIndex(Index)&&IsCurrency(P.HotbarDefinitions[Index])))
        {P.Hotbar[Index].Reset();if(P.HotbarDefinitions.IsValidIndex(Index))P.HotbarDefinitions[Index].Reset();Changed=true;}
    for(auto& Binding:P.QuickBindings)
        if(RetiredIds.Contains(Binding.ItemId)||IsCurrency(Binding.ItemDefinition))
        {Binding=FColdSteelQuickBinding();Changed=true;}
    return true;
}

bool UColdSteelStatusModel::GrantSouls(int64 Amount)
{
    SyncRuntime();auto Next=Snapshot();
    if(!ColdSteelCurrency::Credit(Next,Amount)){Message=TEXT("灵魂数量无效或已达上限");return false;}
    return PersistState(MoveTemp(Next),false);
}

bool UColdSteelStatusModel::CreditCombatSouls(FColdSteelProfile& P,int64 Amount) const
{
    if(bNetShadowProfile && Amount>ColdSteelCurrency::MaxSouls-P.ServerSoulCredits)return false;
    if(!ColdSteelCurrency::Credit(P,Amount))return false;
    if(bNetShadowProfile)P.ServerSoulCredits+=Amount;
    return true;
}

bool ColdSteelCurrency::MergeServerCredits(FColdSteelProfile& Local,const FColdSteelProfile& Server)
{
    // A cumulative server grant watermark merges racing kill rewards and local spending once.
    // Taking max(balance) would refund purchases; copying the mirror would discard local purchases.
    const int64 Delta=FMath::Max<int64>(0,Server.ServerSoulCredits-Local.ServerSoulCredits);
    if(Delta>0 && !Credit(Local,Delta))return false;
    const int64 DebitDelta=FMath::Max<int64>(0,Server.ServerSoulDebits-Local.ServerSoulDebits);
    if(DebitDelta>0&&!Debit(Local,DebitDelta))return false;
    Local.ServerSoulDebits=FMath::Max(Local.ServerSoulDebits,Server.ServerSoulDebits);
    Local.ServerSoulCredits=FMath::Max(Local.ServerSoulCredits,Server.ServerSoulCredits);
    return true;
}

bool UColdSteelStatusModel::SpendSouls(int64 Amount)
{
    SyncRuntime();auto Next=Snapshot();
    if(!ColdSteelCurrency::Debit(Next,Amount)){Message=TEXT("灵魂不足");return false;}
    return PersistState(MoveTemp(Next),false);
}
