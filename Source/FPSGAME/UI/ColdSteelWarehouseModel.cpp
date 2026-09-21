#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
using namespace ColdSteelInventory;
FColdSteelProposal UColdSteelStatusModel::ProposeWarehouse(const FString& Id,int32 Place,int32 Cell,int32 Orientation) const
{
    auto R=ColdSteelWarehouse::Transfer(Current.Items,Id,Place,Cell,WarehouseCapacity(),WarehousePage,Orientation);R.Revision=Current.Generation;return R;
}
bool UColdSteelStatusModel::TransferWarehouse(const FString& Id,int32 Place,int32 Cell,int32 Orientation){SyncRuntime();return CommitProposal(ProposeWarehouse(Id,Place,Cell,Orientation));}
bool UColdSteelStatusModel::GrantStartingArmory()
{
    auto State=Snapshot();bool Changed=false;
    for (const TCHAR* Definition : {TEXT("ue_a762"), TEXT("ue_akm"), TEXT("ue_qbz191"), TEXT("ue_ash12"), TEXT("ue_m1911"), TEXT("ue_dan_wesson715"), TEXT("ue_rune_sword")})
    {
        if(State.ArmoryReceived.Contains(Definition))continue;
        auto Gun=CreateItem(Definition);if(Gun.Data.IsEmpty())return false;
        Gun.Magazine=FString(Definition)==TEXT("ue_rune_sword")?0:FString(Definition)==TEXT("ue_m1911")?7:FString(Definition)==TEXT("ue_dan_wesson715")?6:FString(Definition)==TEXT("ue_ash12")?20:30;
        if(!ColdSteelWarehouse::Insert(State.Items,Gun,WarehouseCapacity()))return false;
        if(FString(Definition)==TEXT("ue_ash12"))
        {
            if(!AddAmmoToState(State,TEXT("ammo_127"),80))return false;
        }
        if(FString(Definition)==TEXT("ue_qbz191"))
        {
            if(!AddAmmoToState(State,TEXT("ammo_58"),120))return false;
        }
        if(FString(Definition)==TEXT("ue_m1911"))
        {
            if(!AddAmmoToState(State,TEXT("ammo_45acp"),70))return false;
        }
        if(FString(Definition)==TEXT("ue_dan_wesson715"))
        {
            if(!AddAmmoToState(State,TEXT("ammo_357"),60))return false;
        }
        State.ArmoryReceived.Add(Definition);Changed=true;
    }
    return !Changed || CommitState(State);
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
    Message=FString::Printf(TEXT("已%s %d 件物品；%d 件保留原处"),bMatching?TEXT("取出"):TEXT("存入"),Moved,Blocked);OnChanged.Broadcast();return true;
}
bool UColdSteelStatusModel::StoreMatchingToWarehouse()
{
    SyncRuntime();auto P=Snapshot();TSet<FString> StoredDefinitions;TArray<FString> Sources;
    for(const auto& I:P.Items)if(I.Place==4)StoredDefinitions.Add(I.Definition);
    for(const auto& I:P.Items)
    {
        if(I.Place!=0||!StoredDefinitions.Contains(I.Definition))continue;
        const FString Category=Text(I,TEXT("category"));
        // Exclude gear by item type, including unequipped weapons and equipment in the backpack.
        if(Category.Contains(TEXT("weapon"))||Category==TEXT("armor")||Category==TEXT("shield")||Category==TEXT("magic_book")
            ||!Text(I,TEXT("equipSlot")).IsEmpty()||!Text(I,TEXT("weaponType")).IsEmpty()
            ||!Text(I,TEXT("rangedType")).IsEmpty()||!Text(I,TEXT("offhandType")).IsEmpty())continue;
        Sources.Add(I.InstanceId);
    }
    int32 Moved=0,Blocked=0;
    for(const auto& Id:Sources)
    {
        auto R=ColdSteelWarehouse::Transfer(P.Items,Id,4,-1,WarehouseCapacity(),WarehousePage);
        if(!R.bValid){++Blocked;continue;}
        P.Items=MoveTemp(R.Items);++Moved;
    }
    if(Moved&&!CommitState(P))return false;
    Message=Sources.IsEmpty()?TEXT("没有可存入的同类物品；武器与装备不参与")
        :FString::Printf(TEXT("已存入 %d 件同类物品；%d 件保留在背包"),Moved,Blocked);
    OnChanged.Broadcast();return true;
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
    for(auto I:Stored){int32 Cell=-1;for(int32 C=0;C<WarehouseCapacity();++C)if(ColdSteelWarehouse::Fits(P.Items,I,C,WarehouseCapacity())){Cell=C;break;}
        if(Cell<0){Message=TEXT("无法整理，原布局保留");return false;}I.Cell=Cell;P.Items.Add(I);}
    if(!CommitState(P))return false;WarehousePage=0;OnChanged.Broadcast();return true;
}
int64 UColdSteelStatusModel::CountMaterial(const FString& Def)const
{
    if(AmmoType(Def))return PouchCount(Def);
    int64 Count=0;for(const auto& I:Current.Items)if((I.Place==0||I.Place==4)&&I.Definition==Def)Count+=I.Count;return Count;
}
bool UColdSteelStatusModel::ConsumeMaterial(const FString& Def,int64 Amount)
{
    if(AmmoType(Def))return SpendAmmo(Def,Amount);
    if(Amount<=0||CountMaterial(Def)<Amount)return false;
    SyncRuntime();auto P=Snapshot();int64 Left=Amount;
    for(int32 Place:{0,4})for(int32 N=P.Items.Num()-1;N>=0&&Left>0;--N){auto& I=P.Items[N];if(I.Place!=Place||I.Definition!=Def)continue;int64 Used=FMath::Min(Left,I.Count);I.Count-=Used;Left-=Used;}
    P.Items.RemoveAll([](const auto& I){return I.Count<=0;});return CommitState(P);
}
bool UColdSteelStatusModel::AddWarehouseItem(const FColdSteelItem& Item,int32 Preferred)
{
    if(AmmoType(Item.Definition))return GrantAmmo(Item.Definition,Item.Count);
    SyncRuntime();auto P=Snapshot();
    if(Preferred<0)for(int32 C=WarehousePage*ColdSteelWarehouse::CellsPerPage;C<FMath::Min(WarehouseCapacity(),(WarehousePage+1)*ColdSteelWarehouse::CellsPerPage);++C)if(ColdSteelWarehouse::Fits(P.Items,Item,C,WarehouseCapacity())){Preferred=C;break;}
    return ColdSteelWarehouse::Insert(P.Items,Item,WarehouseCapacity(),Preferred)&&CommitState(P);
}
int64 UColdSteelStatusModel::WarehouseRemainingCapacity(const FColdSteelItem& Item)const
{
    if(AmmoType(Item.Definition))return ColdSteelAmmo::MaxCount-PouchCount(Item.Definition);
    if(Item.Definition.IsEmpty()||Item.StackMax<1||Item.StackMax>9007199254740991ll)return 0;
    if(Item.Width<1||Item.Width>18||Item.Height<1||Item.Height>ColdSteelWarehouse::Rows)return 0;
    int64 Total=0;TArray<uint32> Occupied;Occupied.Init(0,WarehouseCapacity()/18);
    auto Add=[&](int64 N){Total+=FMath::Min(N,MAX_int64-Total);};
    for(const auto& I:Items())if(I.Place==4){if(Compatible(I,Item))Add(FMath::Max<int64>(0,I.StackMax-I.Count));for(int32 Y=0;Y<I.Height;++Y)Occupied[I.Cell/18+Y]|=((1u<<I.Width)-1)<<(I.Cell%18);}
    for(int32 C=0;C<WarehouseCapacity();++C){
        if(C%18+Item.Width>18||(C%ColdSteelWarehouse::CellsPerPage)/18+Item.Height>ColdSteelWarehouse::Rows)continue;
        const uint32 Mask=((1u<<Item.Width)-1)<<(C%18);bool Free=true;
        for(int32 Y=0;Y<Item.Height;++Y)if(Occupied[C/18+Y]&Mask){Free=false;break;}
        if(Free){Add(Item.StackMax);for(int32 Y=0;Y<Item.Height;++Y)Occupied[C/18+Y]|=Mask;}
    }
    return Total;
}
int64 UColdSteelStatusModel::DepositWarehouseAmount(const FColdSteelItem& Item)
{
    if(AmmoType(Item.Definition))return GrantAmmo(Item.Definition,Item.Count)?Item.Count:0;
    auto Part=Item;Part.Count=FMath::Min(FMath::Max<int64>(0,Item.Count),WarehouseRemainingCapacity(Item));
    return Part.Count>0&&AddWarehouseItem(Part)?Part.Count:0;
}
bool UColdSteelStatusModel::RetrieveAllFromWarehouse()
{
    SyncRuntime();auto P=Snapshot();const auto Original=P.Items;int32 Moved=0,Blocked=0;
    for(const auto& I:Original)if(I.Place==4){auto R=ColdSteelWarehouse::Transfer(P.Items,I.InstanceId,0,-1,WarehouseCapacity(),WarehousePage);if(!R.bValid){++Blocked;continue;}P.Items=MoveTemp(R.Items);++Moved;}
    if(Moved&&!CommitState(P))return false;
    Message=FString::Printf(TEXT("已取出 %d 件物品；%d 件保留在仓库"),Moved,Blocked);OnChanged.Broadcast();return true;
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
