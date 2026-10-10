#include "ColdSteelInventoryTypes.h"
#include "ColdSteelItemReadCache.h"
#include "ColdSteelItemRarity.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "ColdSteelSwapPlacement.h"
#include "ColdSteelWarehouseRules.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace ColdSteelInventory
{
static TSharedPtr<FJsonObject> Object(const FColdSteelItem& Item)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelInventory_ParseItem);
    TSharedPtr<FJsonObject> Result;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data), Result);
    return Result;
}
// Scalar lookups never mutate the parsed data. Key by the complete payload so
// crafting, attachments and same-instance edits take effect on the next read.
// Keep mutable Object() results separate (Compatible removes identity fields).
static TSharedPtr<const FJsonObject> ReadOnlyObject(const FColdSteelItem& Item)
{
    return ColdSteelItemData::Read(Item.Data);
}
FString Text(const FColdSteelItem& Item, const TCHAR* Key)
{
    auto O=ReadOnlyObject(Item);FString V;
    if(O)
    {
        if((FCString::Strcmp(Key,TEXT("rarity"))==0||FCString::Strcmp(Key,TEXT("grade"))==0)&&ColdSteelItemRarity::IsEquipment(*O))return V;
        O->TryGetStringField(Key,V);
    }
    return V;
}
double Number(const FColdSteelItem& Item, const TCHAR* Key, double Default) { auto O=ReadOnlyObject(Item); double V=Default; if(O) O->TryGetNumberField(Key,V); return V; }
bool Flag(const FColdSteelItem& Item, const TCHAR* Key) { if((IsDualPistol(Item)||Text(Item,TEXT("weaponType"))==TEXT("staff")) && FCString::Strcmp(Key,TEXT("isTwoHanded"))==0)return false; auto O=ReadOnlyObject(Item); bool V=false; if(O) O->TryGetBoolField(Key,V); return V; }
FIntPoint BaseFootprint(const FColdSteelItem& I)
{
    const FString Type=Text(I,TEXT("weaponType")),Ranged=Text(I,TEXT("rangedType")),Category=Text(I,TEXT("category")),Slot=Text(I,TEXT("equipSlot"));
    const bool Firearm=Type==TEXT("rifle")||!Ranged.IsEmpty()||Category==TEXT("weapon_ranged");
    auto O=ReadOnlyObject(I);const bool Two=O&&O->HasField(TEXT("isTwoHanded"))?Flag(I,TEXT("isTwoHanded")):Firearm;
    if(I.Definition==TEXT("wood"))return FIntPoint(1,2);
    if(Firearm&&Type!=TEXT("pistol")&&Ranged!=TEXT("pistol")&&Two)return FIntPoint(5,2);
    const int32 W=Number(I,TEXT("grid_w")),H=Number(I,TEXT("grid_h"));if(W>0&&H>0)return FIntPoint(W,H);
    if(Type==TEXT("pistol"))return FIntPoint(3,2);
    if(Type==TEXT("shield")||Type==TEXT("spellbook")||Type==TEXT("magic_book")||Category==TEXT("magic_book"))return FIntPoint(2,3);
    if(Firearm)return FIntPoint(8,2);
    if(Category==TEXT("weapon_melee"))return Two?FIntPoint(2,4):FIntPoint(1,3);
    if(!Type.IsEmpty()||Category==TEXT("weapon"))return Two?FIntPoint(8,2):FIntPoint(3,2);
    if(Slot==TEXT("armor"))return FIntPoint(3,4);
    if(Slot==TEXT("pants"))return FIntPoint(2,3);
    if(Slot==TEXT("helmet")||Slot==TEXT("gloves")||Slot==TEXT("boots"))return FIntPoint(2,2);
    if(Slot==TEXT("cloak")||Slot==TEXT("backpack"))return FIntPoint(3,3);
    if(Slot==TEXT("belt"))return FIntPoint(2,1);
    return FIntPoint(1,1);
}
FIntPoint Footprint(const FColdSteelItem& I)
{
    const FIntPoint Base=BaseFootprint(I);
    return I.bRotated?FIntPoint(Base.Y,Base.X):Base;
}
void ApplyOrientation(FColdSteelItem& Item,int32 Orientation)
{
    // Square items keep a single footprint shape; the flag stays false so their art never turns.
    if(Orientation>=0&&CanRotate(Item))Item.bRotated=Orientation!=0;
    const FIntPoint Size=Footprint(Item);Item.Width=Size.X;Item.Height=Size.Y;
}
const TArray<FString>& SlotNames() { static const TArray<FString> Names={TEXT("左耳环"),TEXT("头盔"),TEXT("右耳环"),TEXT("手套"),TEXT("项链"),TEXT("披风"),TEXT("主手武器"),TEXT("铠甲"),TEXT("副手武器"),TEXT("主手武器2"),TEXT("腰带"),TEXT("副手武器2"),TEXT("额外物品"),TEXT("鞋靴"),TEXT("背包装备"),TEXT("裤子")}; return Names; }
int32 EquippedBag(const TArray<FColdSteelItem>& Items)
{
    for(int32 N=0;N<Items.Num();++N)if(Items[N].Place==1&&Items[N].Cell==14)return N;
    return INDEX_NONE;
}
int32 BagRows(const TArray<FColdSteelItem>& Items)
{
    const int32 Bag=EquippedBag(Items);
    // 背包装备按 bagExtraCells 每 18 格撑出一行；字段缺失或非正时保持基础 4 行。
    if(Bag<0)return 4;
    return 4+FMath::Max(0,int32(Number(Items[Bag],TEXT("bagExtraCells"))))/18;
}
int32 CompartmentCells(const TArray<FColdSteelItem>& Items)
{
    const auto G=CompartmentGrid(Items);return G.X*G.Y;
}
FIntPoint CompartmentGridOf(const FColdSteelItem& BagItem)
{
    // 夹层尺寸约定＝长×宽（列×行）：bagCompartmentColumns/bagCompartmentRows，
    // 缺省 6×6（便携背包口径）；bagCompartmentCells 只作"是否定义夹层"的开关，
    // 容量一律＝列×行，两套数字不再各自维护。
    if(Number(BagItem,TEXT("bagCompartmentCells"))<=0)return FIntPoint::ZeroValue;
    const int32 Cols=FMath::Clamp(int32(Number(BagItem,TEXT("bagCompartmentColumns"),6)),1,ColdSteelCompartment::MaxColumns);
    const int32 RowsN=FMath::Clamp(int32(Number(BagItem,TEXT("bagCompartmentRows"),6)),1,ColdSteelCompartment::MaxRows);
    return FIntPoint(Cols,RowsN);
}
FIntPoint CompartmentGrid(const TArray<FColdSteelItem>& Items)
{
    const int32 Bag=EquippedBag(Items);
    return Bag<0?FIntPoint::ZeroValue:CompartmentGridOf(Items[Bag]);
}
bool Compatible(const FColdSteelItem& A,const FColdSteelItem& B)
{
    if(Text(A,TEXT("category"))==TEXT("gold") && Text(B,TEXT("category"))==TEXT("gold")) return true;
    if(A.StackMax<=1||A.StackMax!=B.StackMax||A.Definition!=B.Definition||A.Cooldown!=B.Cooldown)return false;
    auto Left=Object(A),Right=Object(B);if(!Left||!Right)return false;
    // Match Godot dictionary equality: ordering and placement metadata are not identity.
    for(const TCHAR* Key:{TEXT("instance_id"),TEXT("itemId"),TEXT("slot"),TEXT("backpack_slot"),TEXT("stack"),TEXT("_price"),TEXT("grid_x"),TEXT("grid_y"),TEXT("grid_w"),TEXT("grid_h")}){Left->RemoveField(Key);Right->RemoveField(Key);}
    return FJsonValue::CompareEqual(FJsonValueObject(Left),FJsonValueObject(Right));
}
bool CanEquip(const FColdSteelItem& I,int32 Slot)
{
    if(Slot<0 || Slot>=SlotNames().Num() || I.Count!=1) return false;
    const FString Type=Text(I,TEXT("weaponType")), Category=Text(I,TEXT("category")), Off=Text(I,TEXT("offhandType"));
    if(Type==TEXT("staff"))return Slot==6||Slot==9;
    const bool Support=Type==TEXT("shield")||Type==TEXT("spellbook")||Type==TEXT("magic_book")||Off==TEXT("shield")||Off==TEXT("spellbook")||Off==TEXT("magic_book")||Category==TEXT("magic_book");
    const bool Weapon=!Type.IsEmpty()||Category.Contains(TEXT("weapon"))||!Text(I,TEXT("rangedType")).IsEmpty();
    if(Slot==6||Slot==9) return Weapon&&!Support;
    if(Slot==8||Slot==11) return (Support||IsDualPistol(I))&&!Flag(I,TEXT("isTwoHanded"));
    static const TCHAR* Keys[]={TEXT("earring"),TEXT("helmet"),TEXT("ring1"),TEXT("gloves"),TEXT("necklace"),TEXT("cloak"),TEXT("weapon"),TEXT("armor"),TEXT("offhand"),TEXT("weapon2"),TEXT("belt"),TEXT("ring2"),TEXT("extra"),TEXT("boots"),TEXT("backpack"),TEXT("pants")};
    return !Weapon && Text(I,TEXT("equipSlot"))==Keys[Slot];
}
int32 Owner(const TArray<FColdSteelItem>& Items,int32 Place,int32 Cell)
{
    static const FString GlobalWarehouse;
    return Owner(Items,Place,Cell,GlobalWarehouse);
}
int32 Owner(const TArray<FColdSteelItem>& Items,int32 Place,int32 Cell,const FString& Container,FIntPoint CompGrid)
{
    for(int32 N=0;N<Items.Num();++N) { const auto& I=Items[N]; if(I.Place!=Place) continue;
        if(Place==4&&I.Container!=Container) continue; // 仓库格空间按储物容器分域
        if(Place!=0&&Place!=4&&Place!=ColdSteelCompartment::Place) { if(I.Cell==Cell) return N; continue; }
        if(Cell<0) continue;
        if(Place==ColdSteelCompartment::Place)
        {
            // 夹层按装备定义的列数折行；边界由 Fits/调用方按容量先行裁剪，这里只做纯几何匹配
            // （加载校验显式传整表预算网格，装备栏后置时也能正确判重叠）。
            const int32 Columns=CompGrid.X>0?CompGrid.X:CompartmentGrid(Items).X;
            if(Columns<1)continue;
            if(Cell%Columns>=I.Cell%Columns&&Cell%Columns<I.Cell%Columns+I.Width
                &&Cell/Columns>=I.Cell/Columns&&Cell/Columns<I.Cell/Columns+I.Height) return N;
            continue;
        }
        if(Place==4&&Cell/ColdSteelWarehouse::CellsPerPage!=I.Cell/ColdSteelWarehouse::CellsPerPage) continue; // 仓库跨页不算占用
        if(Cell%18>=I.Cell%18&&Cell%18<I.Cell%18+I.Width&&Cell/18>=I.Cell/18&&Cell/18<I.Cell/18+I.Height) return N;
    } return INDEX_NONE;
}
bool Locked(const TArray<FColdSteelItem>& Items,int32 Slot)
{
    if(Slot!=8&&Slot!=11) return false;
    int32 N=Owner(Items,1,Slot==8?6:9);
    return N>=0 && Flag(Items[N],TEXT("isTwoHanded"));
}
static bool FitsRows(const TArray<FColdSteelItem>& Items,const FColdSteelItem& I,int32 Cell,int32 Rows)
{
    if(Cell<0||Cell>=Rows*18||I.Width<1||I.Height<1||Cell%18+I.Width>18||Cell/18+I.Height>Rows) return false;
    for(int32 Y=0;Y<I.Height;++Y) for(int32 X=0;X<I.Width;++X) if(Owner(Items,0,Cell+Y*18+X)>=0) return false;
    return true;
}
bool Fits(const TArray<FColdSteelItem>& Items,const FColdSteelItem& I,int32 Cell)
{
    return FitsRows(Items,I,Cell,BagRows(Items));
}
bool Insert(TArray<FColdSteelItem>& Items,FColdSteelItem I,int32 Preferred)
{
    if(I.Count<=0||I.StackMax<=0) return false;
    auto Next=Items;
    for(auto& T:Next) if(T.Place==0&&Compatible(T,I)) { const int64 Amount=FMath::Min(I.Count,T.StackMax-T.Count); T.Count+=Amount; I.Count-=Amount; if(!I.Count){Items=MoveTemp(Next);return true;} }
    const int32 Cells=BagRows(Next)*18;
    bool First=true;
    while(I.Count>0) {
        int32 Cell=Fits(Next,I,Preferred)?Preferred:-1;
        if(Cell<0) for(int32 C=0;C<Cells;++C) if(Fits(Next,I,C)){Cell=C;break;}
        if(Cell<0) return false;
        auto Part=I; Part.Place=0; Part.Cell=Cell; Part.Map.Empty(); Part.Position=FVector::ZeroVector; Part.Count=FMath::Min(I.Count,I.StackMax);
        if(!First) Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Next.Add(Part); I.Count-=Part.Count; First=false; Preferred=-1;
    }
    Items=MoveTemp(Next); return true;
}
// Automatic equipment returns may turn to fit; explicit grid drops retain
// the player's pending orientation. Insert itself remains strict for other callers.
static bool InsertEquipment(TArray<FColdSteelItem>& Items,FColdSteelItem Item,int32 Preferred=-1)
{
    if(Insert(Items,Item,Preferred))return true;
    if(!CanRotate(Item))return false;
    ApplyOrientation(Item,Item.bRotated?0:1);
    return Insert(Items,MoveTemp(Item),Preferred);
}
FColdSteelProposal Move(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Place,int32 Cell,int32 Orientation)
{
    FColdSteelProposal R; R.Items=Items; R.Reason=TEXT("目标位置无法容纳物品");
    const int32 From=Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(From<0||(Place!=0&&Place!=1)||Items[From].Place>1) return R;
    auto Moving=Items[From];
    // Equipment slots keep the authored shape; only bag placement carries an orientation.
    if(Place==0)ApplyOrientation(Moving,Orientation);
    const int32 OldPlace=Moving.Place,OldCell=Moving.Cell;
    const bool bTurned=Moving.Width!=Items[From].Width||Moving.Height!=Items[From].Height;
    if(Place==OldPlace&&Cell==OldCell&&!bTurned){R.bValid=true;if(Place==1&&(Cell==6||Cell==9))R.ActiveWeaponSlot=Cell;return R;}
    // 背包装备槽(14)占有者即将变更（卸下或被替换）的统一卸下规则：容量收缩后所有物品必须
    // 仍能存放——扩展格里放不进的随事务自动回落重排，夹层里放不进的自动搬进背包（可堆叠
    // 先并堆）；任何一步装不下（连同放回的背包本体）＝背包空间不足，整体拒绝，不发布半成品。
    const int32 BagOwner=Owner(Items,1,14);
    TArray<FColdSteelItem> BagCompartmentMigrate,BagRowOverflow;
    int32 BagChangeRows=-1; // 槽14占有者变更后的主背包行数；-1＝本次移动不改变容量。
    if(BagOwner>=0&&(From==BagOwner||(Place==1&&Cell==14&&From!=BagOwner)))
    {
        const bool bReequip=Place==1&&Cell==14;
        const FIntPoint OldGrid=CompartmentGrid(Items);
        const FIntPoint NewGrid=bReequip?CompartmentGridOf(Items[From]):FIntPoint::ZeroValue;
        const int32 NewRowCells=(bReequip?4+FMath::Max(0,int32(Number(Items[From],TEXT("bagExtraCells"))))/18:4)*18;
        BagChangeRows=NewRowCells/18;
        for(const auto& I:Items)
        {
            if(I.Place==0&&I.Cell+(I.Height-1)*18+I.Width-1>=NewRowCells)BagRowOverflow.Add(I);
            if(I.Place==ColdSteelCompartment::Place)
            {
                // 物品在旧网格里合法放置；换新网格后放不下（容量不足或列宽不够）才随事务搬进背包。
                const int32 End=I.Cell+(I.Height-1)*FMath::Max(1,OldGrid.X)+I.Width-1;
                if(End>=NewGrid.X*NewGrid.Y||I.Width>NewGrid.X)BagCompartmentMigrate.Add(I);
            }
        }
    }
    R.Items.RemoveAt(From);
    // 扩展格物品回落：从布局取出，优先落回缩减后网格的原列底部，装不下再全格找位。
    for(const auto& M:BagRowOverflow)
    {
        const int32 N=R.Items.IndexOfByPredicate([&](const auto& V){return V.InstanceId==M.InstanceId;});
        if(N<0)continue;
        auto Copy=M;R.Items.RemoveAt(N);
        const int32 RowsNow=BagRows(R.Items);
        auto TryIn=[&](FColdSteelItem& C){bool bIn=Insert(R.Items,C,(RowsNow-1)*18+C.Cell%18);if(!bIn)bIn=Insert(R.Items,C);return bIn;};
        bool bIn=TryIn(Copy);
        if(!bIn&&CanRotate(Copy)){ApplyOrientation(Copy,Copy.bRotated?0:1);bIn=TryIn(Copy);}
        if(!bIn){R.Items=Items;R.Reason=TEXT("背包空间不足，无法卸下背包装备");return R;}
    }
    for(const auto& M:BagCompartmentMigrate)
    {
        auto Copy=M;bool bIn=Insert(R.Items,Copy);
        if(!bIn&&CanRotate(Copy)){ApplyOrientation(Copy,Copy.bRotated?0:1);bIn=Insert(R.Items,Copy);}
        if(!bIn){R.Items=Items;R.Reason=TEXT("背包空间不足，无法卸下背包装备");return R;}
    }
    if(Place==1) {
        if(Cell==6||Cell==9)R.ActiveWeaponSlot=Cell;
        if(!CanEquip(Moving,Cell)){R.Reason=TEXT("物品与装备槽不兼容");return R;}
        if(Locked(Items,Cell)){R.Reason=TEXT("双手武器占用，请先卸下主手");return R;}
        if(OldPlace==1) {
            int32 Target=Owner(R.Items,1,Cell);
            if(Target>=0) { if(!CanEquip(R.Items[Target],OldCell)) return R; R.Items[Target].Cell=OldCell; }
        } else {
            TArray<int32> Slots={Cell};
            if(Flag(Moving,TEXT("isTwoHanded")))Slots.Add(Cell==6?8:11);
            TArray<FColdSteelItem> Displaced;
            for(int32 S:Slots)if(const int32 N=Owner(R.Items,1,S);N>=0){Displaced.Add(R.Items[N]);R.Items.RemoveAt(N);}
            // Keep the established placement/stacking result when it works.
            auto Packed=R.Items;bool OriginalFits=true;
            for(const auto& Old:Displaced)if(!Insert(Packed,Old,OldCell)){OriginalFits=false;break;}
            if(OriginalFits)R.Items=MoveTemp(Packed);
            else
            {
                // Plan main hand and offhand together: a greedy first placement
                // must not consume the only rectangle available to the other item.
                bool Exhausted=false;
                // 回填边界同样按移动后的行数（BagChangeRows）：换装后装备中的扩行以新背包为准，
                // 否则旧装备可能被塞进即将消失的扩展行。
                if(!PlaceDisplaced(R.Items,MoveTemp(Displaced),Items[From],Cell,Exhausted,0,0,BagChangeRows>=0?BagChangeRows:BagRows(Items),FString(),true))
                {
                    R.Items=Items;
                    R.Reason=Exhausted?TEXT("自动摆放较复杂，请调整背包空间后重试"):TEXT("尝试两种朝向后仍没有连续空间安置替换下的装备");
                    return R;
                }
            }
        }
        if(OldPlace==0)Moving.BackpackCell=OldCell;
        Moving.Place=1;Moving.Cell=Cell; R.Items.Add(Moving);
    } else {
        if(Cell==-1 && OldPlace==1) { if(!InsertEquipment(R.Items,Moving,Moving.BackpackCell)){R.Items=Items;R.Reason=TEXT("尝试两种朝向后仍没有连续空间卸下装备");return R;} }
        else {
            // 目标边界按"移动后的行数"算：卸下/换装背包的同一事务里，装备中的扩行已经
            // 不再有效（否则矮物品能落进即将消失的扩展行，卸下后越界成坏档）。
            const int32 RowsAfter=BagChangeRows>=0?BagChangeRows:BagRows(Items);
            const int32 BagCells=RowsAfter*18;
            if(Cell<0||Cell>=BagCells||Cell%18+Moving.Width>18||Cell/18+Moving.Height>RowsAfter){R.Reason=TEXT("物品超出背包边界，请向内移动");return R;}
            TSet<int32> Blockers;
            for(int32 Y=0;Y<Moving.Height;++Y) for(int32 X=0;X<Moving.Width;++X){int32 N=Owner(R.Items,0,Cell+Y*18+X);if(N>=0)Blockers.Add(N);}
            if(Blockers.Num()>0&&OldPlace==0&&!(Blockers.Num()==1&&Compatible(Moving,R.Items[*Blockers.CreateConstIterator()])))
            {
                TArray<FColdSteelItem> Displaced;
                for(int32 N=R.Items.Num()-1;N>=0;--N)if(Blockers.Contains(N)){Displaced.Add(R.Items[N]);R.Items.RemoveAt(N);}
                Moving.Place=0;Moving.Cell=Cell;R.Items.Add(Moving);
                bool Exhausted=false;
                // The vacated rect keeps its meaning; the anchor carries the pending orientation.
                auto Anchor=Moving;Anchor.Place=OldPlace;Anchor.Cell=OldCell;
                if(!PlaceDisplaced(R.Items,MoveTemp(Displaced),Anchor,Cell,Exhausted,0,0,BagRows(Items)))
                {
                    R.Items=Items;
                    R.Reason=Exhausted?TEXT("自动摆放较复杂，请调整落点后重试"):TEXT("没有足够的连续空间安置被交换物品");
                    return R;
                }
            }
            else if(Blockers.Num()>1){R.Items=Items;R.Reason=TEXT("装备槽无法同时接收多件物品，请先卸到空位");return R;}
            else if(Blockers.Num()==1) {
                int32 N=*Blockers.CreateConstIterator(); auto Other=R.Items[N];
                if(OldPlace==0&&Compatible(Moving,Other)) {
                    const int64 Amount=FMath::Min(Moving.Count,Other.StackMax-Other.Count); if(Amount<=0){R.Reason=TEXT("目标堆叠已满");return R;}
                    R.Items[N].Count+=Amount; Moving.Count-=Amount; if(Moving.Count>0)R.Items.Add(Moving);
                    R.bValid=true;return R;
                }
                R.Items.RemoveAt(N); Moving.Place=0;Moving.Cell=Cell;
                // 换装事务里以移动后的行数校验（新背包的扩行在本事务内即生效）。
                if(!FitsRows(R.Items,Moving,Cell,RowsAfter))return R;
                R.Items.Add(Moving);
                if(OldPlace==0) { if(!Fits(R.Items,Other,OldCell)){R.Reason=TEXT("原位置放不下被交换物品");return R;} }
                else if(!CanEquip(Other,OldCell)){R.Reason=TEXT("目标物品不能换入装备槽，请选空位");return R;}
                if(OldPlace==1)Other.BackpackCell=Other.Cell;
                Other.Place=OldPlace;Other.Cell=OldCell;R.Items.Add(Other);
            } else {Moving.Place=0;Moving.Cell=Cell;R.Items.Add(Moving);}
        }
    }
    for(int32 S:{8,11}) if(Locked(R.Items,S)&&Owner(R.Items,1,S)>=0){
        if(OldPlace!=1||Place!=0)return R;
        const int32 N=Owner(R.Items,1,S);auto Offhand=R.Items[N];R.Items.RemoveAt(N);if(!InsertEquipment(R.Items,Offhand)){R.Items=Items;R.Reason=TEXT("尝试两种朝向后仍没有连续空间安置副手装备");return R;}
    }
    R.bValid=true; R.Reason.Empty();return R;
}
static bool ValidateProfile(const FColdSteelProfile& P,FString& Reason,bool AllowLegacyWood)
{
    if(P.AmmoPouchVersion<0||P.AmmoPouchVersion>1){Reason=TEXT("弹药袋版本无效");return false;}
    for(const auto& Pair:P.AmmoPouch)if(Pair.Key.IsEmpty()||Pair.Value<0||Pair.Value>9007199254740991ll){Reason=TEXT("弹药袋数量无效");return false;}
    if(!ColdSteelSkills::Validate(P,Reason))return false;
    if(!ColdSteelQuickBar::Validate(P,Reason))return false;
    if(!P.GunAssemblyJob.Id.IsEmpty())
    {
        const auto& J=P.GunAssemblyJob;
        if(J.Recipe.IsNone()||J.Item.InstanceId.IsEmpty()||J.Item.Definition.IsEmpty()||!Object(J.Item)
            ||J.PartCount<1||J.PartCount>30||J.Scores.Num()!=J.PartCount||J.Misses.Num()!=J.PartCount
            ||J.InstalledMask<0||uint32(J.InstalledMask)>((1u<<FMath::Clamp(J.PartCount,1,30))-1u)
            ||!FMath::IsFinite(J.CalibrationDuration)||J.CalibrationDuration<=0
            ||!FMath::IsFinite(J.CalibrationSeconds)||J.CalibrationSeconds<0||J.CalibrationSeconds>J.CalibrationDuration+.01f
            ||!FMath::IsFinite(J.CalibrationTime)||J.CalibrationTime<0||!FMath::IsFinite(J.CalibrationError)||J.CalibrationError<0
            ||!FMath::IsFinite(J.Quality)||J.Quality<0||J.Quality>100
            ||(J.bFinished&&(uint32(J.InstalledMask)!=((1u<<FMath::Clamp(J.PartCount,1,30))-1u)||J.CalibrationSeconds<J.CalibrationDuration)))
        {Reason=TEXT("枪械拼装工件数据无效，保留原存档");return false;}
        for(float Score:J.Scores)if(!FMath::IsFinite(Score)||Score<0||Score>100)return false;
        for(int32 Misses:J.Misses)if(Misses<0||Misses>10)return false;
        if(P.Items.ContainsByPredicate([&J](const auto& I){return I.InstanceId==J.Item.InstanceId;}))
        {Reason=TEXT("拼装成品已在背包中，不能重复领取");return false;}
    }
    if(P.StaminaVersion<0||P.StaminaVersion>1||!FMath::IsFinite(P.Stamina)||P.Stamina<0||!FMath::IsFinite(P.StaminaRecoveryDelay)||P.StaminaRecoveryDelay<0||P.StaminaRecoveryDelay>60){Reason=TEXT("体力数据无效");return false;}
    const auto& Survival=P.Survival;
    const float Values[]={Survival.Hunger,Survival.Hydration,Survival.Sanity},Maxima[]={Survival.MaxHunger,Survival.MaxHydration,Survival.MaxSanity};
    for(int32 Index=0;Index<3;++Index)
        if(!FMath::IsFinite(Values[Index])||!FMath::IsFinite(Maxima[Index])||Maxima[Index]<=0.f||Values[Index]<0.f||Values[Index]>Maxima[Index])
        {Reason=TEXT("生存状态数据无效，保留原存档");return false;}
    if(!FMath::IsFinite(Survival.DeprivationSeconds)||Survival.DeprivationSeconds<0.f||Survival.DeprivationSeconds>=1.f)
    {Reason=TEXT("生存损血计时无效，保留原存档");return false;}
    if(!FMath::IsFinite(Survival.FountainBlessingSeconds)||Survival.FountainBlessingSeconds<0.f||Survival.FountainBlessingSeconds>FFPSSurvivalState::FountainBlessingDuration)
    {Reason=TEXT("喷泉赐福计时无效，保留原存档");return false;}
    Reason=TEXT("存档数据未通过校验，保留原文件");
    if((P.Version!=1&&P.Version!=2)||P.WarehouseLayoutVersion<0||P.WarehouseLayoutVersion>1||P.WarehousePages<1||P.WarehousePages>(P.WarehouseLayoutVersion?ColdSteelWarehouse::MaxPages:500)||P.Level<1||P.Level>10000||P.Experience<0||P.Points<0||P.Kills<0||P.Generation<0||P.Items.Num()>10000||P.Hotbar.Num()!=4||P.HotbarDefinitions.Num()!=4||!FMath::IsFinite(P.Health)||!FMath::IsFinite(P.Mana)||P.Health<0||P.Mana<0)return false;
    if(P.Experience >= (20ll+P.Level*20ll+P.Level*int64(P.Level)*12)*8)return false;
    if(P.ActiveWeaponSlot!=6&&P.ActiveWeaponSlot!=9)return false;
    for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")}) {auto V=P.Attributes.Find(Key);if(!V||*V<0||*V>1000000)return false;}
    TSet<FString> Ids;TSet<int32> LegacyWarehouseCells;TArray<FColdSteelItem> Placed;
    // 背包扩格与夹层容量都由装备的背包物品撑出；档案里装备栏条目可能排在后面，
    // 所以容量先按整表算好，再逐件校验（Fits 的动态行数会受"已放入集合"顺序影响）。
    const int32 ProfileBagRows=BagRows(P.Items);const FIntPoint ProfileCompGrid=CompartmentGrid(P.Items);
    for(const auto& I:P.Items) {
        if(I.VirtualMagazineAmmo<0||I.VirtualMagazineAmmo>I.Magazine){Reason=TEXT("训练弹数量无效");return false;}
        // Rows are bounded per container by Fits below; a rotated instance may exceed the backpack's four.
        if(I.InstanceId.IsEmpty()||Ids.Contains(I.InstanceId)||I.Definition.IsEmpty()||!Object(I)||I.Count<=0||I.StackMax<1||I.Count>I.StackMax||I.StackMax>9007199254740991ll||I.Width<1||I.Width>18||I.Height<1||I.Height>ColdSteelWarehouse::Rows||I.Place<0||(I.Place>2&&I.Place!=4&&I.Place!=ColdSteelCompartment::Place)||!FMath::IsFinite(I.Cooldown)||I.Cooldown<0||I.Magazine<0||I.Reserve<0)return false;
        Ids.Add(I.InstanceId);
        if(Footprint(I)!=FIntPoint(I.Width,I.Height)&&
            !(AllowLegacyWood&&I.Definition==TEXT("wood")&&I.Width==1&&I.Height==1))
        {Reason=FString::Printf(TEXT("物品占格与当前定义不一致：%s (%d×%d)"),*I.Definition,I.Width,I.Height);return false;}
        if(I.Place==0&&!FitsRows(Placed,I,I.Cell,ProfileBagRows))return false;
        if(I.Place==ColdSteelCompartment::Place&&(ProfileCompGrid.X<1||!ColdSteelCompartment::Fits(Placed,I,I.Cell,ProfileCompGrid)))return false;
        if(I.Place==1&&(!CanEquip(I,I.Cell)||Owner(Placed,1,I.Cell)>=0))return false;
        if(I.Place==2&&(I.Map.IsEmpty()||I.Position.ContainsNaN()||I.WorldRotation.ContainsNaN()))return false;
        if(I.Place==4){
            if(P.WarehouseLayoutVersion==0){if(!I.Container.IsEmpty())return false;if(I.Cell<0||I.Cell>=P.WarehousePages*20||LegacyWarehouseCells.Contains(I.Cell))return false;LegacyWarehouseCells.Add(I.Cell);}
            // 主仓库行按档案页数；储物箱行按 StoragePages 登记的自身页数（Fits 依 Container 分域查占用）。
            else {const int32 Cap=(I.Container.IsEmpty()?P.WarehousePages:FMath::Max(1,P.StoragePages.FindRef(I.Container)))*ColdSteelWarehouse::CellsPerPage;
                if(I.Cell<0||I.Cell>=Cap||!ColdSteelWarehouse::Fits(Placed,I,I.Cell,Cap))return false;}
        }
        Placed.Add(I);
    }
    for(int32 S:{8,11})if(Locked(Placed,S)&&Owner(Placed,1,S)>=0)return false;
    Reason.Empty();return true;
}
bool Validate(const FColdSteelProfile& P,FString& Reason)
{
    return ValidateProfile(P,Reason,false);
}
bool MigrateLegacyWoodFootprints(FColdSteelProfile& Profile,bool& Changed,FString& Reason)
{
    Changed=false;
    // Validate the saved layout before changing it. Only the known 1x1 wood
    // footprint is accepted here; malformed items and overlaps remain errors.
    if(!ValidateProfile(Profile,Reason,true))return false;
    auto Next=Profile;
    for(int32 N=0;N<Next.Items.Num();++N)
    {
        auto& Item=Next.Items[N];
        if(Item.Definition!=TEXT("wood")||Item.Width!=1||Item.Height!=1)continue;
        ApplyOrientation(Item,-1);
        if(Item.Place==0||(Item.Place==4&&Next.WarehouseLayoutVersion==1))
        {
            auto Others=Next.Items;Others.RemoveAt(N);
            const int32 Capacity=Item.Place==0?72:
                (Item.Container.IsEmpty()?Next.WarehousePages:FMath::Max(1,Next.StoragePages.FindRef(Item.Container)))*ColdSteelWarehouse::CellsPerPage;
            const auto FitsHere=[&](int32 Cell){return Item.Place==0?Fits(Others,Item,Cell):ColdSteelWarehouse::Fits(Others,Item,Cell,Capacity);};
            if(!FitsHere(Item.Cell))
            {
                int32 Cell=INDEX_NONE;
                for(int32 C=0;C<Capacity;++C)if(FitsHere(C)){Cell=C;break;}
                if(Cell!=INDEX_NONE)Item.Cell=Cell;
                else
                {
                    // An expanded item must never erase the profile when its
                    // old bag/crate is full. Preserve its ID/count in the main
                    // warehouse, adding a page only if existing pages are full.
                    if(Next.WarehouseLayoutVersion!=1)
                    {Reason=TEXT("旧木材占格迁移空间不足，原存档保留");return false;}
                    Item.Place=4;Item.Container.Reset();Item.BackpackCell=-1;
                    while(Cell==INDEX_NONE)
                    {
                        const int32 WarehouseCapacity=Next.WarehousePages*ColdSteelWarehouse::CellsPerPage;
                        for(int32 C=0;C<WarehouseCapacity;++C)
                            if(ColdSteelWarehouse::Fits(Others,Item,C,WarehouseCapacity)){Cell=C;break;}
                        if(Cell!=INDEX_NONE)break;
                        if(Next.WarehousePages>=ColdSteelWarehouse::MaxPages)
                        {Reason=TEXT("旧木材占格迁移空间不足，原存档保留");return false;}
                        ++Next.WarehousePages;
                    }
                    Item.Cell=Cell;
                }
            }
        }
        Changed=true;
    }
    if(!Validate(Next,Reason))return false;
    if(Changed)Profile=MoveTemp(Next);
    return true;
}
bool MigrateAuthoredGridFootprints(FColdSteelProfile& Profile,bool& Changed,FString& Reason)
{
    Changed=false;
    // 作者占格字段（grid_w/grid_h）变更后的旧实例回填：实例 Data 快照按旧尺寸
    // 自洽（缺字段＝默认 1×1），严格校验可入；迁移把当前口径写回快照并按新
    // 占格重新落位。2026-10-01：enchant_scroll_* 1×1→1×2 竖直，金属锭 1×1→2×1。
    static const struct {const TCHAR* Prefix;const TCHAR* Exact;int32 W;int32 H;} Rules[]=
    {
        {TEXT("enchant_scroll_"),nullptr,1,2},
        {nullptr,TEXT("ironIngot"),2,1},
        {nullptr,TEXT("copperIngot"),2,1},
        {nullptr,TEXT("silverIngot"),2,1},
        {nullptr,TEXT("goldIngot"),2,1},
    };
    if(!ValidateProfile(Profile,Reason,false))return false;
    auto Next=Profile;
    const FIntPoint CompGrid=CompartmentGrid(Next.Items);
    for(int32 N=0;N<Next.Items.Num();++N)
    {
        auto& Item=Next.Items[N];
        int32 W=0,H=0;
        for(const auto& Rule:Rules)
            if((Rule.Prefix&&Item.Definition.StartsWith(Rule.Prefix))||(Rule.Exact&&Item.Definition==Rule.Exact)){W=Rule.W;H=Rule.H;break;}
        if(!W||(Number(Item,TEXT("grid_w"))==W&&Number(Item,TEXT("grid_h"))==H))continue;
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)continue;
        Data->SetNumberField(TEXT("grid_w"),W);Data->SetNumberField(TEXT("grid_h"),H);
        Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
        ApplyOrientation(Item,0);
        if(Item.Place==0||(Item.Place==4&&Next.WarehouseLayoutVersion==1)||Item.Place==ColdSteelCompartment::Place)
        {
            auto Others=Next.Items;Others.RemoveAt(N);
            const int32 Capacity=Item.Place==0?BagRows(Others)*18:
                Item.Place==ColdSteelCompartment::Place?CompGrid.X*CompGrid.Y:
                (Item.Container.IsEmpty()?Next.WarehousePages:FMath::Max(1,Next.StoragePages.FindRef(Item.Container)))*ColdSteelWarehouse::CellsPerPage;
            const auto FitsHere=[&](int32 Cell){return Item.Place==0?Fits(Others,Item,Cell):
                Item.Place==ColdSteelCompartment::Place?ColdSteelCompartment::Fits(Others,Item,Cell,CompGrid):
                ColdSteelWarehouse::Fits(Others,Item,Cell,Capacity);};
            if(!FitsHere(Item.Cell))
            {
                int32 Cell=INDEX_NONE;
                for(int32 C=0;C<Capacity;++C)if(FitsHere(C)){Cell=C;break;}
                if(Cell!=INDEX_NONE)Item.Cell=Cell;
                else
                {
                    // An expanded item must never erase the profile when its
                    // old bag/crate/compartment is full. Preserve its ID/count
                    // in the main warehouse, adding a page only if needed.
                    if(Next.WarehouseLayoutVersion!=1)
                    {Reason=TEXT("旧占格迁移空间不足，原存档保留");return false;}
                    Item.Place=4;Item.Container.Reset();Item.BackpackCell=-1;
                    while(Cell==INDEX_NONE)
                    {
                        const int32 WarehouseCapacity=Next.WarehousePages*ColdSteelWarehouse::CellsPerPage;
                        for(int32 C=0;C<WarehouseCapacity;++C)
                            if(ColdSteelWarehouse::Fits(Others,Item,C,WarehouseCapacity)){Cell=C;break;}
                        if(Cell!=INDEX_NONE)break;
                        if(Next.WarehousePages>=ColdSteelWarehouse::MaxPages)
                        {Reason=TEXT("旧占格迁移空间不足，原存档保留");return false;}
                        ++Next.WarehousePages;
                    }
                    Item.Cell=Cell;
                }
            }
        }
        Changed=true;
    }
    if(!Validate(Next,Reason))return false;
    if(Changed)Profile=MoveTemp(Next);
    return true;
}
}
