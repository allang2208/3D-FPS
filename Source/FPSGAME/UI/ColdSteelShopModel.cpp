#include "ColdSteelShopModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "GameFramework/PlayerController.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelCurrency.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
using namespace ColdSteelInventory;

void UColdSteelShopModel::BeginSession()
{
    EndSession();
    Model = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Model) return;
    bOpen = true;
    for (const TCHAR* Id : {TEXT("bread"), TEXT("baguette_bread"), TEXT("mineral_water"), TEXT("soda_can")})
    {
        auto Item = Model->CreateItem(Id);
        if (!Item.Data.IsEmpty()) Shelf.Add(MoveTemp(Item));
    }
    ProfileHandle = Model->OnChanged.AddUObject(this, &ThisClass::ProfileChanged);
    Message = TEXT("拖动或右键加入待售栏，确认成交前物品仍在背包中");
    OnChanged.Broadcast();
}

void UColdSteelShopModel::EndSession()
{
    if (Model && ProfileHandle.IsValid()) Model->OnChanged.Remove(ProfileHandle);
    ProfileHandle.Reset();
    bOpen = false; Basket.Reset(); Shelf.Reset(); SaleRules.Reset(); ++BasketRevision;
    bCommitting=false;bPendingSale=false;
}

void UColdSteelShopModel::Deinitialize() { EndSession(); OnChanged.Clear(); Super::Deinitialize(); }

int64 UColdSteelShopModel::BuyPrice(const FString& Definition) const
{
    const auto* Item = Shelf.FindByPredicate([&Definition](const auto& I) { return I.Definition == Definition; });
    const double Price = Item ? Number(*Item, TEXT("price"), 0) : 0;
    return FMath::IsFinite(Price) && Price >= 1 && Price <= 1000000000. ? FMath::FloorToInt64(Price) : 0;
}

int64 UColdSteelShopModel::SellPrice(const FColdSteelItem& Item) const
{
    if (!Model || Item.bIncineratorAmmo || ColdSteelCurrency::IsCurrency(Item.Definition)) return 0;
    if (!SaleRules.Contains(Item.Definition))
    {
        const auto Base = Model->CreateItem(Item.Definition);
        // Search collectibles carry an authored recovery value. Read the trusted
        // catalogue, not an instance's saved/client-supplied price fields.
        const double SellValue=Item.Definition.StartsWith(TEXT("search_"))
            ? Number(Base,TEXT("sell_souls"),Number(Base,TEXT("price"),0)*.5)
            : Number(Base,TEXT("price"),0)*.5;
        const double BasePrice = Base.Data.IsEmpty() || Flag(Base, TEXT("unsellable")) || Flag(Base, TEXT("questItem"))
            ? 0 : SellValue;
        if(SaleRules.Num()>=128)SaleRules.Reset();
        SaleRules.Add(Item.Definition,FVector2D(BasePrice,Number(Base,TEXT("maxUses"),1)));
    }
    const auto Rule=SaleRules.FindChecked(Item.Definition);
    double Price = Rule.X;
    const double MaxUses = Rule.Y;
    if (MaxUses > 1) Price *= FMath::Clamp(Number(Item, TEXT("remainingUses"), MaxUses) / MaxUses, 0., 1.);
    return FMath::IsFinite(Price) && Price >= 1 && Price <= double(ColdSteelCurrency::MaxSouls)
        ? FMath::FloorToInt64(Price) : 0;
}

bool UColdSteelShopModel::CanSell(const FColdSteelItem& Item) const
{
    return (Item.Place == 0 || Item.Place == ColdSteelCompartment::Place) && Item.Container.IsEmpty()
        && Item.Count > 0 && !Flag(Item,TEXT("unsellable")) && !Flag(Item,TEXT("questItem")) && SellPrice(Item) > 0;
}

bool UColdSteelShopModel::Fail(const FString& Reason)
{ Message = Reason; OnChanged.Broadcast(); return false; }

bool UColdSteelShopModel::CanTrade()
{
    if (!bOpen || !Model || bCommitting) return false;
    if(Model->IsCampfireInventoryPending())return Fail(TEXT("上一笔物品操作正在结算"));
    return true;
}

bool UColdSteelShopModel::AddToSale(const FString& Id)
{
    if (!bOpen || !Model || bCommitting) return false;
    const auto* Item = Model->FindItem(Id);
    if (!Item || !CanSell(*Item)) return Fail(TEXT("仅可出售背包或夹层中有售价的物品；已装备物品请先卸下"));
    if (Basket.ContainsByPredicate([&Id](const auto& Entry) { return Entry.Id == Id; }))
        return Fail(TEXT("该物品已在待售栏中，可在下方修改数量"));
    if(Basket.Num()>=MaxSaleLines)return Fail(TEXT("单次最多出售 128 组物品，请先结算当前待售栏"));
    Basket.Add({Id, Item->Count}); ++BasketRevision;
    Message = TEXT("已加入待售栏，尚未出售"); OnChanged.Broadcast(); return true;
}

void UColdSteelShopModel::RemoveFromSale(const FString& Id)
{
    if(!bOpen||bCommitting)return;
    if (Basket.RemoveAll([&Id](const auto& Entry) { return Entry.Id == Id; }))
    { ++BasketRevision; Message = TEXT("已移出待售栏"); OnChanged.Broadcast(); }
}

bool UColdSteelShopModel::SetSaleCount(const FString& Id, int64 Count)
{
    if(!bOpen||bCommitting)return false;
    auto* Entry = Basket.FindByPredicate([&Id](const auto& E) { return E.Id == Id; });
    const auto* Item = Model ? Model->FindItem(Id) : nullptr;
    if (!Entry || !Item || Count < 1 || Count > Item->Count) return Fail(TEXT("出售数量超出持有数量"));
    if (Entry->Count != Count) { Entry->Count = Count; ++BasketRevision; OnChanged.Broadcast(); }
    return true;
}

void UColdSteelShopModel::ClearSale()
{ if(!bOpen||bCommitting)return;Basket.Reset(); ++BasketRevision; Message = TEXT("已清空待售选择，物品保留原处"); OnChanged.Broadcast(); }

void UColdSteelShopModel::ProfileChanged()
{
    if (!bOpen || bCommitting) return;
    const int32 Removed = Basket.RemoveAll([this](const auto& E)
    { const auto* I = Model->FindItem(E.Id); return !I || !CanSell(*I) || E.Count > I->Count; });
    if (Removed) { ++BasketRevision; Message = TEXT("部分物品已变化，已从待售栏移除，请重新选择"); }
    OnChanged.Broadcast();
}

bool UColdSteelShopModel::QuoteSale(FColdSteelShopQuote& Out) const
{
    Out = {}; Out.BasketRevision = BasketRevision;
    if (!bOpen || !Model || Basket.IsEmpty()) return false;
    for (const auto& Entry : Basket)
    {
        const auto* Item = Model->FindItem(Entry.Id);
        if (!Item || !CanSell(*Item) || Entry.Count < 1 || Entry.Count > Item->Count) return false;
        const int64 Price = SellPrice(*Item);
        if (Entry.Count > (ColdSteelCurrency::MaxSouls - Out.Total) / Price) return false;
        Out.Lines.Add({*Item, Entry.Count, Price}); Out.Total += Price * Entry.Count;
    }
    return Out.Total > 0;
}

bool UColdSteelShopModel::Buy(const FString& Definition, int32 Count)
{
    if (!CanTrade()) return false;
    const int64 UnitPrice = BuyPrice(Definition);
    if (UnitPrice <= 0 || Count < 1 || Count > 99) return Fail(TEXT("请选择有效商品，购买数量为 1～99"));
    if(GetWorld()->GetNetMode()!=NM_Standalone)
    {
        auto* PC=GetGameInstance()->GetFirstLocalPlayerController();auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
        FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Shop;R.Mode=TEXT("shop.buy");R.Definition=FName(*Definition);R.Count=Count;
        bPendingSale=false;bCommitting=true;if(!PS||!PS->RequestInventoryAction(R)){bCommitting=false;return Fail(TEXT("交易正在等待角色同步"));}
        if(bCommitting){Message=TEXT("交易已提交，等待结算");OnChanged.Broadcast();}return true;
    }
    Model->SyncRuntime(); auto Next = Model->Snapshot();
    if (!ColdSteelCurrency::Debit(Next, UnitPrice * Count)) return Fail(TEXT("灵魂不足"));
    if (!Insert(Next.Items, Model->CreateItem(Definition, Count))) return Fail(TEXT("背包空间不足，未扣除灵魂"));
    bool Saved = false;
    { TGuardValue<bool> Guard(bCommitting, true); Saved = Model->CommitState(MoveTemp(Next)); }
    if (!Saved) return Fail(Model->ResultMessage());
    Message = FString::Printf(TEXT("购买成功 · 花费 %lld 灵魂"), UnitPrice * Count);
    OnChanged.Broadcast(); return true;
}

bool UColdSteelShopModel::ConfirmSale(const FColdSteelShopQuote& Quote)
{
    if (!CanTrade()) return false;
    if (Quote.BasketRevision != BasketRevision || Quote.Lines.IsEmpty()) return Fail(TEXT("待售选择已变化，请重新确认"));
    Model->SyncRuntime();
    FColdSteelShopQuote Current;
    if (!QuoteSale(Current) || Current.Total != Quote.Total || Current.Lines.Num() != Quote.Lines.Num())
        return Fail(TEXT("物品或售价已变化，请重新确认"));
    // Confirmation protects item contents on both standalone and network transactions.
    for(int32 Index=0;Index<Quote.Lines.Num();++Index)
    {
        const auto& Line=Quote.Lines[Index];const auto& Now=Current.Lines[Index];
        auto LiveItem=Now.Item;LiveItem.Cooldown=Line.Item.Cooldown;
        if(Line.Count!=Now.Count||Line.UnitPrice!=Now.UnitPrice
            ||!FColdSteelItem::StaticStruct()->CompareScriptStruct(&LiveItem,&Line.Item,0))
            return Fail(TEXT("待售物品已变化，请重新确认"));
    }
    if(GetWorld()->GetNetMode()!=NM_Standalone)
    {
        auto* PC=GetGameInstance()->GetFirstLocalPlayerController();auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
        FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Shop;R.Mode=TEXT("shop.sell");R.Count=Quote.Total;
        for(const auto& Line:Quote.Lines)
        {
            auto& Entry=R.TradeItems.AddDefaulted_GetRef();Entry.Key=Line.Item.InstanceId;Entry.Value=Line.Count;
        }
        bPendingSale=true;PendingSaleRevision=BasketRevision;
        bCommitting=true;if(!PS||!PS->RequestInventoryAction(R)){bCommitting=false;bPendingSale=false;return Fail(TEXT("交易正在等待角色同步"));}
        if(bCommitting){Message=TEXT("交易已提交，等待结算");OnChanged.Broadcast();}return true;
    }
    auto Next = Model->Snapshot();
    for (int32 Index = 0; Index < Quote.Lines.Num(); ++Index)
    {
        const auto& Line = Quote.Lines[Index];
        auto* Item = Next.Items.FindByPredicate([&Line](const auto& I) { return I.InstanceId == Line.Item.InstanceId; });
        Item->Count -= Line.Count;
    }
    Next.Items.RemoveAll([](const auto& Item) { return Item.Count <= 0; });
    if (!ColdSteelCurrency::Credit(Next, Quote.Total)) return Fail(TEXT("灵魂余额已达上限，未出售物品"));
    bool Saved = false;
    { TGuardValue<bool> Guard(bCommitting, true); Saved = Model->CommitState(MoveTemp(Next)); }
    if (!Saved) return Fail(Model->ResultMessage());
    Basket.Reset(); ++BasketRevision;
    Message = FString::Printf(TEXT("出售成功 · 获得 %lld 灵魂"), Quote.Total);
    OnChanged.Broadcast(); return true;
}

void UColdSteelShopModel::NetworkTradeFinished(bool Success,const FString& Reason)
{
    if(!bCommitting)return;
    bCommitting=false;
    if(Success&&bPendingSale&&PendingSaleRevision==BasketRevision){Basket.Reset();++BasketRevision;}
    bPendingSale=false;if(!bOpen)return;
    ProfileChanged();Message=Reason;OnChanged.Broadcast();
}
bool UColdSteelShopModel::ExecuteNetworkTrade(UColdSteelStatusModel* Profile,const FColdSteelInventoryRequest& R,const FString& HostSlot,FString& Reason)
{
    if(!Profile||!Profile->GetWorld()||Profile->GetWorld()->GetNetMode()==NM_Client)return false;
    auto* Session=NewObject<UColdSteelShopModel>(Profile->GetGameInstance());Session->Model=Profile;
    auto Next=Profile->Snapshot();int64 Credit=0,Debit=0;
    if(R.Mode==TEXT("shop.buy"))
    {
        const FString Id=R.Definition.ToString();
        if(Id!=TEXT("bread")&&Id!=TEXT("baguette_bread")&&Id!=TEXT("mineral_water")&&Id!=TEXT("soda_can"))return false;
        if(R.Count<1||R.Count>99)return false;
        auto Item=Profile->CreateItem(Id,int32(R.Count));
        const double Price=Number(Item,TEXT("price"),0);
        if(!FMath::IsFinite(Price)||Price<1||Price>1000000000.)return false;
        Debit=FMath::FloorToInt64(Price)*R.Count;
        if(!ColdSteelCurrency::Debit(Next,Debit)){Reason=TEXT("灵魂不足");return false;}
        if(!Insert(Next.Items,Item)){Reason=TEXT("背包空间不足，未扣除灵魂");return false;}
    }
    else if(R.Mode==TEXT("shop.sell"))
    {
        if(R.TradeItems.IsEmpty()||R.TradeItems.Num()>MaxSaleLines){Reason=TEXT("单次出售数量无效，请重新选择");return false;}
        for(const auto& Entry:R.TradeItems)
        {
            auto* I=Next.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Entry.Key;});
            if(!I||!Session->CanSell(*I)||Entry.Value<1||Entry.Value>I->Count){Reason=TEXT("待售物品已变化");return false;}
            const int64 Price=Session->SellPrice(*I);
            if(Entry.Value>(ColdSteelCurrency::MaxSouls-Credit)/Price)return false;
            Credit+=Price*Entry.Value;I->Count-=Entry.Value;
        }
        if(Credit!=R.Count){Reason=TEXT("售价已变化，请重新确认");return false;}
        Next.Items.RemoveAll([](const auto& I){return I.Count<=0;});
        if(!ColdSteelCurrency::Credit(Next,Credit)){Reason=TEXT("灵魂已达上限，未出售物品");return false;}
    }
    else return false;
    if(!HostSlot.IsEmpty())
    {
        if(Credit>ColdSteelCurrency::MaxSouls-Next.ServerSoulCredits||Debit>ColdSteelCurrency::MaxSouls-Next.ServerSoulDebits)return false;
        Next.ServerSoulCredits+=Credit;Next.ServerSoulDebits+=Debit;
    }
    if(!Profile->CommitCampfireState(MoveTemp(Next),TEXT("Inventory"),HostSlot)){Reason=Profile->ResultMessage();return false;}
    Reason=Credit>0?FString::Printf(TEXT("出售成功 · 获得 %lld 灵魂"),Credit):FString::Printf(TEXT("购买成功 · 花费 %lld 灵魂"),Debit);
    return true;
}
