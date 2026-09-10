#include "ColdSteelInventoryTypes.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace ColdSteelInventory
{
static TSharedPtr<FJsonObject> Object(const FColdSteelItem& Item)
{
    TSharedPtr<FJsonObject> Result;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data), Result);
    return Result;
}
FString Text(const FColdSteelItem& Item, const TCHAR* Key) { auto O = Object(Item); FString V; if(O) O->TryGetStringField(Key,V); return V; }
double Number(const FColdSteelItem& Item, const TCHAR* Key, double Default) { auto O=Object(Item); double V=Default; if(O) O->TryGetNumberField(Key,V); return V; }
bool Flag(const FColdSteelItem& Item, const TCHAR* Key) { auto O=Object(Item); bool V=false; if(O) O->TryGetBoolField(Key,V); return V; }
FIntPoint Footprint(const FColdSteelItem& I)
{
    const FString Type=Text(I,TEXT("weaponType")),Ranged=Text(I,TEXT("rangedType")),Category=Text(I,TEXT("category")),Slot=Text(I,TEXT("equipSlot"));
    const bool Firearm=Type==TEXT("rifle")||!Ranged.IsEmpty()||Category==TEXT("weapon_ranged");
    auto O=Object(I);const bool Two=O&&O->HasField(TEXT("isTwoHanded"))?Flag(I,TEXT("isTwoHanded")):Firearm;
    if(Firearm&&Type!=TEXT("pistol")&&Ranged!=TEXT("pistol")&&Two)return FIntPoint(5,2);
    const int32 W=Number(I,TEXT("grid_w")),H=Number(I,TEXT("grid_h"));if(W>0&&H>0)return FIntPoint(W,H);
    if(Type==TEXT("pistol"))return FIntPoint(3,2);
    if(Type==TEXT("shield")||Type==TEXT("spellbook")||Type==TEXT("magic_book")||Category==TEXT("magic_book"))return FIntPoint(2,3);
    if(Firearm)return FIntPoint(8,2);
    if(Category==TEXT("weapon_melee"))return Two?FIntPoint(2,4):FIntPoint(1,3);
    if(!Type.IsEmpty()||Category==TEXT("weapon"))return Two?FIntPoint(8,2):FIntPoint(3,2);
    if(Slot==TEXT("armor"))return FIntPoint(3,4);
    if(Slot==TEXT("helmet")||Slot==TEXT("gloves")||Slot==TEXT("boots"))return FIntPoint(2,2);
    if(Slot==TEXT("cloak")||Slot==TEXT("backpack"))return FIntPoint(3,3);
    if(Slot==TEXT("belt"))return FIntPoint(2,1);
    return FIntPoint(1,1);
}
const TArray<FString>& SlotNames() { static const TArray<FString> Names={TEXT("左耳环"),TEXT("头盔"),TEXT("右耳环"),TEXT("手套"),TEXT("项链"),TEXT("披风"),TEXT("主手武器"),TEXT("铠甲"),TEXT("副手武器"),TEXT("主手武器2"),TEXT("腰带"),TEXT("副手武器2"),TEXT("额外物品"),TEXT("靴子"),TEXT("背包装备")}; return Names; }
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
    if(Slot<0 || Slot>=15 || I.Count!=1) return false;
    const FString Type=Text(I,TEXT("weaponType")), Category=Text(I,TEXT("category")), Off=Text(I,TEXT("offhandType"));
    const bool Support=Type==TEXT("shield")||Type==TEXT("spellbook")||Type==TEXT("magic_book")||Off==TEXT("shield")||Off==TEXT("spellbook")||Off==TEXT("magic_book")||Category==TEXT("magic_book");
    const bool Weapon=!Type.IsEmpty()||Category.Contains(TEXT("weapon"))||!Text(I,TEXT("rangedType")).IsEmpty();
    if(Slot==6||Slot==9) return Weapon&&!Support;
    if(Slot==8||Slot==11) return Support&&!Flag(I,TEXT("isTwoHanded"));
    static const TCHAR* Keys[]={TEXT("earring"),TEXT("helmet"),TEXT("ring1"),TEXT("gloves"),TEXT("necklace"),TEXT("cloak"),TEXT("weapon"),TEXT("armor"),TEXT("offhand"),TEXT("weapon2"),TEXT("belt"),TEXT("ring2"),TEXT("extra"),TEXT("boots"),TEXT("backpack")};
    return !Weapon && Text(I,TEXT("equipSlot"))==Keys[Slot];
}
int32 Owner(const TArray<FColdSteelItem>& Items,int32 Place,int32 Cell)
{
    for(int32 N=0;N<Items.Num();++N) { const auto& I=Items[N]; if(I.Place!=Place) continue;
        if(Place!=0) { if(I.Cell==Cell) return N; }
        else if(Cell>=0&&Cell<72&&Cell%18>=I.Cell%18&&Cell%18<I.Cell%18+I.Width&&Cell/18>=I.Cell/18&&Cell/18<I.Cell/18+I.Height) return N;
    } return INDEX_NONE;
}
bool Locked(const TArray<FColdSteelItem>& Items,int32 Slot)
{
    if(Slot!=8&&Slot!=11) return false;
    int32 N=Owner(Items,1,Slot==8?6:9);
    return N>=0 && Flag(Items[N],TEXT("isTwoHanded"));
}
bool Fits(const TArray<FColdSteelItem>& Items,const FColdSteelItem& I,int32 Cell)
{
    if(Cell<0||Cell>=72||I.Width<1||I.Height<1||Cell%18+I.Width>18||Cell/18+I.Height>4) return false;
    for(int32 Y=0;Y<I.Height;++Y) for(int32 X=0;X<I.Width;++X) if(Owner(Items,0,Cell+Y*18+X)>=0) return false;
    return true;
}
bool Insert(TArray<FColdSteelItem>& Items,FColdSteelItem I,int32 Preferred)
{
    if(I.Count<=0||I.StackMax<=0) return false;
    auto Next=Items;
    for(auto& T:Next) if(T.Place==0&&Compatible(T,I)) { const int64 Amount=FMath::Min(I.Count,T.StackMax-T.Count); T.Count+=Amount; I.Count-=Amount; if(!I.Count){Items=MoveTemp(Next);return true;} }
    bool First=true;
    while(I.Count>0) {
        int32 Cell=Fits(Next,I,Preferred)?Preferred:-1;
        if(Cell<0) for(int32 C=0;C<72;++C) if(Fits(Next,I,C)){Cell=C;break;}
        if(Cell<0) return false;
        auto Part=I; Part.Place=0; Part.Cell=Cell; Part.Map.Empty(); Part.Position=FVector::ZeroVector; Part.Count=FMath::Min(I.Count,I.StackMax);
        if(!First) Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Next.Add(Part); I.Count-=Part.Count; First=false; Preferred=-1;
    }
    Items=MoveTemp(Next); return true;
}
FColdSteelProposal Move(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Place,int32 Cell)
{
    FColdSteelProposal R; R.Items=Items; R.Reason=TEXT("目标位置无法容纳物品");
    const int32 From=Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(From<0||(Place!=0&&Place!=1)||Items[From].Place>1) return R;
    auto Moving=Items[From]; const int32 OldPlace=Moving.Place,OldCell=Moving.Cell;
    if(Place==OldPlace&&Cell==OldCell){R.bValid=true;if(Place==1&&(Cell==6||Cell==9))R.ActiveWeaponSlot=Cell;return R;}
    R.Items.RemoveAt(From);
    if(Place==1) {
        if(Cell==6||Cell==9)R.ActiveWeaponSlot=Cell;
        if(!CanEquip(Moving,Cell)){R.Reason=TEXT("物品与装备槽不兼容");return R;}
        if(Locked(Items,Cell)){R.Reason=TEXT("双手武器占用，请先卸下主手");return R;}
        if(OldPlace==1) {
            int32 Target=Owner(R.Items,1,Cell);
            if(Target>=0) { if(!CanEquip(R.Items[Target],OldCell)) return R; R.Items[Target].Cell=OldCell; }
        } else {
            TArray<int32> Displaced={Cell};
            if(Flag(Moving,TEXT("isTwoHanded"))) Displaced.Add(Cell==6?8:11);
            for(int32 S:Displaced) { int32 N=Owner(R.Items,1,S); if(N>=0) {auto Old=R.Items[N]; R.Items.RemoveAt(N); if(!Insert(R.Items,Old,OldCell))return R;} }
        }
        if(OldPlace==0)Moving.BackpackCell=OldCell;
        Moving.Place=1;Moving.Cell=Cell; R.Items.Add(Moving);
    } else {
        if(Cell==-1 && OldPlace==1) { if(!Insert(R.Items,Moving,Moving.BackpackCell))return R; }
        else {
            if(Cell<0||Cell>=72||Cell%18+Moving.Width>18||Cell/18+Moving.Height>4){R.Reason=TEXT("物品超出背包边界，请向内移动");return R;}
            TSet<int32> Blockers;
            for(int32 Y=0;Y<Moving.Height;++Y) for(int32 X=0;X<Moving.Width;++X){int32 N=Owner(R.Items,0,Cell+Y*18+X);if(N>=0)Blockers.Add(N);}
            if(Blockers.Num()>1){R.Reason=TEXT("目标覆盖多件物品，请先腾出完整空间");return R;}
            if(Blockers.Num()==1) {
                int32 N=*Blockers.CreateConstIterator(); auto Other=R.Items[N];
                if(OldPlace==0&&Compatible(Moving,Other)) {
                    const int64 Amount=FMath::Min(Moving.Count,Other.StackMax-Other.Count); if(Amount<=0){R.Reason=TEXT("目标堆叠已满");return R;}
                    R.Items[N].Count+=Amount; Moving.Count-=Amount; if(Moving.Count>0)R.Items.Add(Moving);
                    R.bValid=true;return R;
                }
                R.Items.RemoveAt(N); Moving.Place=0;Moving.Cell=Cell;
                if(!Fits(R.Items,Moving,Cell))return R;
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
        const int32 N=Owner(R.Items,1,S);auto Offhand=R.Items[N];R.Items.RemoveAt(N);if(!Insert(R.Items,Offhand))return R;
    }
    R.bValid=true; R.Reason.Empty();return R;
}
bool Validate(const FColdSteelProfile& P,FString& Reason)
{
    Reason=TEXT("存档数据未通过校验，保留原文件");
    if((P.Version!=1&&P.Version!=2)||P.WarehousePages<1||P.WarehousePages>500||P.Level<1||P.Level>10000||P.Experience<0||P.Points<0||P.Kills<0||P.Generation<0||P.Items.Num()>10000||P.Hotbar.Num()!=4||P.HotbarDefinitions.Num()!=4||!FMath::IsFinite(P.Health)||!FMath::IsFinite(P.Mana)||P.Health<0||P.Mana<0)return false;
    if(P.Experience >= (20ll+P.Level*20ll+P.Level*int64(P.Level)*12)*8)return false;
    if(P.ActiveWeaponSlot!=6&&P.ActiveWeaponSlot!=9)return false;
    for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")}) {auto V=P.Attributes.Find(Key);if(!V||*V<0||*V>1000000)return false;}
    TSet<FString> Ids;TArray<FColdSteelItem> Placed;
    for(const auto& I:P.Items) {
        if(I.InstanceId.IsEmpty()||Ids.Contains(I.InstanceId)||I.Definition.IsEmpty()||!Object(I)||I.Count<=0||I.StackMax<1||I.Count>I.StackMax||I.StackMax>9007199254740991ll||I.Width<1||I.Width>18||I.Height<1||I.Height>4||I.Place<0||(I.Place>2&&I.Place!=4)||!FMath::IsFinite(I.Cooldown)||I.Cooldown<0||I.Magazine<0||I.Reserve<0)return false;
        Ids.Add(I.InstanceId);
        if(Footprint(I)!=FIntPoint(I.Width,I.Height))return false;
        if(I.Place==0&&!Fits(Placed,I,I.Cell))return false;
        if(I.Place==1&&(!CanEquip(I,I.Cell)||Owner(Placed,1,I.Cell)>=0))return false;
        if(I.Place==2&&(I.Map.IsEmpty()||I.Position.ContainsNaN()||I.WorldRotation.ContainsNaN()))return false;
        if(I.Place==4&&(I.Cell<0||I.Cell>=P.WarehousePages*20||Owner(Placed,4,I.Cell)>=0))return false;
        Placed.Add(I);
    }
    for(int32 S:{8,11})if(Locked(Placed,S)&&Owner(Placed,1,S)>=0)return false;
    Reason.Empty();return true;
}
}
