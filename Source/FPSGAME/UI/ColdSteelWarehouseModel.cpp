#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
using namespace ColdSteelInventory;
FColdSteelProposal UColdSteelStatusModel::ProposeWarehouse(const FString& Id,int32 Place,int32 Cell) const
{
    auto R=ColdSteelWarehouse::Transfer(Current.Items,Id,Place,Cell,WarehouseCapacity(),WarehousePage);R.Revision=Current.Generation;return R;
}
bool UColdSteelStatusModel::TransferWarehouse(const FString& Id,int32 Place,int32 Cell){SyncRuntime();return CommitProposal(ProposeWarehouse(Id,Place,Cell));}
bool UColdSteelStatusModel::GrantStartingArmory()
{
    // The six migrated weapons were retired by the user.
    return true;
}
bool UColdSteelStatusModel::WarehouseBatch(bool bMatching)
{
    SyncRuntime();auto P=Snapshot();TSet<FString> Names;TArray<FColdSteelItem> Sources;
    for(const auto& I:P.Items)if(I.Place==0)Names.Add(Text(I,TEXT("name")));
    for(const auto& I:P.Items)if((bMatching&&I.Place==4&&Names.Contains(Text(I,TEXT("name"))))||(!bMatching&&I.Place==0))Sources.Add(I);
    Sources.Sort([&](const auto& A,const auto& B){if(!bMatching&&(Text(A,TEXT("category"))==TEXT("gold"))!=(Text(B,TEXT("category"))==TEXT("gold")))return Text(A,TEXT("category"))==TEXT("gold");return A.Cell>B.Cell;});
    int32 Moved=0,Blocked=0;
    for(const auto& I:Sources){auto R=ColdSteelWarehouse::Transfer(P.Items,I.InstanceId,bMatching?0:4,-1,WarehouseCapacity(),WarehousePage);
        if(!R.bValid){Blocked=Sources.Num()-Moved;break;}P.Items=MoveTemp(R.Items);++Moved;}
    if(Moved&&!CommitState(P))return false;
    Message=FString::Printf(TEXT("已%s %d 格物品；%d 格保留原处"),bMatching?TEXT("取出"):TEXT("存入"),Moved,Blocked);OnChanged.Broadcast();return true;
}
bool UColdSteelStatusModel::SortWarehouse(const FString& Mode,int32 Category)
{
    if(Mode!=TEXT("rarity")&&Mode!=TEXT("price")&&Mode!=TEXT("category"))return false;
    SyncRuntime();auto P=Snapshot();TArray<FColdSteelItem> Stored;
    for(const auto& I:P.Items)if(I.Place==4)Stored.Add(I);
    const TArray<FString> Rarities={TEXT("common"),TEXT("uncommon"),TEXT("rare"),TEXT("epic"),TEXT("mythic"),TEXT("legendary")};
    Stored.StableSort([&](const auto& A,const auto& B){
        int32 AC=ColdSteelWarehouse::Category(A),BC=ColdSteelWarehouse::Category(B);
        if(Mode==TEXT("category")&&(AC==Category)!=(BC==Category))return AC==Category;
        if(Mode==TEXT("price")&&Number(A,TEXT("price"))!=Number(B,TEXT("price")))return Number(A,TEXT("price"))>Number(B,TEXT("price"));
        if(Mode==TEXT("category")&&AC!=Category&&AC!=BC)return AC<BC;
        int32 AR=FMath::Max(0,Rarities.Find(Text(A,TEXT("rarity")))),BR=FMath::Max(0,Rarities.Find(Text(B,TEXT("rarity"))));
        if(AR!=BR)return AR>BR;if(Mode==TEXT("rarity")&&AC!=BC)return AC<BC;
        return Text(A,TEXT("name"))<Text(B,TEXT("name"));
    });
    P.Items.RemoveAll([](const auto& I){return I.Place==4;});
    for(int32 N=0;N<Stored.Num();++N){Stored[N].Cell=N;P.Items.Add(Stored[N]);}
    if(!CommitState(P))return false;WarehousePage=0;OnChanged.Broadcast();return true;
}
int64 UColdSteelStatusModel::CountMaterial(const FString& Def)const
{
    int64 Count=0;for(const auto& I:Current.Items)if((I.Place==0||I.Place==4)&&I.Definition==Def)Count+=I.Count;return Count;
}
bool UColdSteelStatusModel::ConsumeMaterial(const FString& Def,int64 Amount)
{
    if(Amount<=0||CountMaterial(Def)<Amount)return false;
    SyncRuntime();auto P=Snapshot();int64 Left=Amount;
    for(int32 Place:{0,4})for(int32 N=P.Items.Num()-1;N>=0&&Left>0;--N){auto& I=P.Items[N];if(I.Place!=Place||I.Definition!=Def)continue;int64 Used=FMath::Min(Left,I.Count);I.Count-=Used;Left-=Used;}
    P.Items.RemoveAll([](const auto& I){return I.Count<=0;});return CommitState(P);
}
bool UColdSteelStatusModel::AddWarehouseItem(const FColdSteelItem& Item,int32 Preferred)
{
    SyncRuntime();auto P=Snapshot();
    if(Preferred<0)for(int32 C=WarehousePage*20;C<FMath::Min(WarehouseCapacity(),(WarehousePage+1)*20);++C)if(Owner(P.Items,4,C)<0){Preferred=C;break;}
    return ColdSteelWarehouse::Insert(P.Items,Item,WarehouseCapacity(),Preferred)&&CommitState(P);
}
int64 UColdSteelStatusModel::WarehouseRemainingCapacity(const FColdSteelItem& Item)const
{
    if(Item.Definition.IsEmpty()||Item.StackMax<1||Item.StackMax>9007199254740991ll)return 0;
    int32 Used=0;int64 Total=0;
    auto Add=[&](int64 N){Total+=FMath::Min(N,MAX_int64-Total);};
    for(const auto& I:Items())if(I.Place==4){++Used;if(Compatible(I,Item))Add(FMath::Max<int64>(0,I.StackMax-I.Count));}
    for(int32 N=Used;N<WarehouseCapacity();++N)Add(Item.StackMax);return Total;
}
int64 UColdSteelStatusModel::DepositWarehouseAmount(const FColdSteelItem& Item)
{
    auto Part=Item;Part.Count=FMath::Min(FMath::Max<int64>(0,Item.Count),WarehouseRemainingCapacity(Item));
    return Part.Count>0&&AddWarehouseItem(Part)?Part.Count:0;
}
bool UColdSteelStatusModel::RetrieveAllFromWarehouse()
{
    SyncRuntime();auto P=Snapshot();const auto Original=P.Items;bool Changed=false;
    for(const auto& I:Original)if(I.Place==4){auto R=ColdSteelWarehouse::Transfer(P.Items,I.InstanceId,0,-1,WarehouseCapacity(),WarehousePage);if(!R.bValid)break;P.Items=MoveTemp(R.Items);Changed=true;}
    return !Changed||CommitState(P);
}
int64 UColdSteelStatusModel::CountWarehouseMaterial(TFunctionRef<bool(const FColdSteelItem&)> Predicate)const
{
    int64 Total=0;for(const auto& I:Items())if(I.Place==4&&Predicate(I))Total+=FMath::Min(I.Count,MAX_int64-Total);return Total;
}
int64 UColdSteelStatusModel::ConsumeWarehouseMaterial(TFunctionRef<bool(const FColdSteelItem&)> Predicate,int64 Amount)
{
    if(Amount<=0)return 0;SyncRuntime();auto P=Snapshot();int64 Left=Amount;
    for(int32 N=P.Items.Num()-1;N>=0&&Left>0;--N){auto& I=P.Items[N];if(I.Place!=4||!Predicate(I))continue;int64 Used=FMath::Min(Left,I.Count);I.Count-=Used;Left-=Used;}
    if(Left==Amount)return 0;P.Items.RemoveAll([](const auto& I){return I.Count<=0;});return CommitState(P)?Amount-Left:0;
}
