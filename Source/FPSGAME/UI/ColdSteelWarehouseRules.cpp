#include "ColdSteelWarehouseRules.h"
using namespace ColdSteelInventory;
namespace ColdSteelWarehouse
{
bool Insert(TArray<FColdSteelItem>& Items,FColdSteelItem I,int32 Capacity,int32 Preferred)
{
    if(I.Count<=0||I.StackMax<=0||Capacity<1||Preferred>=Capacity)return false;
    auto Next=Items;
    TArray<int32> Order;
    if(Preferred>=0)Order.Add(Preferred);
    for(int32 C=0;C<Capacity;++C)if(C!=Preferred)Order.Add(C);
    for(int32 C:Order){const int32 N=Owner(Next,Place,C);if(N>=0&&Compatible(Next[N],I)){
        const int64 Added=FMath::Min(I.Count,Next[N].StackMax-Next[N].Count);
        Next[N].Count+=Added;I.Count-=Added;if(!I.Count){Items=MoveTemp(Next);return true;}
    }}
    bool First=true;
    for(int32 C:Order)if(Owner(Next,Place,C)<0){
        auto Part=I;Part.Place=Place;Part.Cell=C;Part.Map.Empty();Part.Position=FVector::ZeroVector;
        Part.Count=FMath::Min(I.Count,I.StackMax);
        if(!First)Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Next.Add(Part);First=false;I.Count-=Part.Count;if(!I.Count){Items=MoveTemp(Next);return true;}
    }
    return false;
}
FColdSteelProposal Transfer(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Destination,int32 Cell,int32 Capacity,int32 Page)
{
    FColdSteelProposal R;R.Items=Items;R.Reason=TEXT("无法移动：空间不足或目标无效，物品保留原处");
    const int32 From=Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(From<0||Cell< -1||Capacity<1)return R;
    auto I=Items[From];const int32 OldPlace=I.Place,OldCell=I.Cell;
    if(OldPlace!=0&&OldPlace!=1&&OldPlace!=Place)return R;
    if(Destination!=Place&&!(OldPlace==Place&&Destination==0))return R;
    if(Destination==Place&&Cell>=Capacity)return R;
    if(OldPlace==Place&&Destination==Place){
        if(Cell<0||Cell==OldCell)return R;
        const int32 Target=Owner(R.Items,Place,Cell);
        if(Target>=0)R.Items[Target].Cell=OldCell;
        R.Items[From].Cell=Cell;R.bValid=true;R.Reason.Empty();return R;
    }
    R.Items.RemoveAt(From);
    if(Destination==Place){
        int32 Preferred=Cell;
        if(Preferred<0)for(int32 C=FMath::Clamp(Page,0,(Capacity-1)/20)*20;C<FMath::Min(Capacity,(Page+1)*20);++C)if(Owner(R.Items,Place,C)<0){Preferred=C;break;}
        const int32 Target=Cell>=0?Owner(R.Items,Place,Cell):-1;
        if(Target>=0&&!Compatible(R.Items[Target],I)){
            auto Other=R.Items[Target];R.Items.RemoveAt(Target);
            if(!ColdSteelInventory::Insert(R.Items,Other,OldPlace==0?OldCell:-1))return R;
            I.Place=Place;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);
        }else if(Cell>=0&&Target<0){
            I.Place=Place;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);
        }else if(!Insert(R.Items,I,Capacity,Preferred))return R;
    }else if(Cell==-1){if(!ColdSteelInventory::Insert(R.Items,I))return R;}
    else {
        if(Cell<0||Cell>=72)return R;
        const int32 Target=Owner(R.Items,0,Cell);
        if(Target>=0&&Compatible(R.Items[Target],I)){
            // Explicit merge fills the chosen stack first, then compatible stacks/free rectangles.
            auto& T=R.Items[Target];const int64 N=FMath::Min(I.Count,T.StackMax-T.Count);T.Count+=N;I.Count-=N;
            if(I.Count>0&&!ColdSteelInventory::Insert(R.Items,I))return R;
        }else {
            FColdSteelItem Other;const bool Displaced=Target>=0;
            if(Displaced){Other=R.Items[Target];R.Items.RemoveAt(Target);}
            if(!Fits(R.Items,I,Cell))return R;
            I.Place=0;I.Cell=Cell;R.Items.Add(I);
            if(Displaced){Other.Place=Place;Other.Cell=OldCell;R.Items.Add(Other);}
        }
    }
    R.bValid=true;R.Reason.Empty();return R;
}
int32 Category(const FColdSteelItem& I)
{
    const FString C=Text(I,TEXT("category")),Slot=Text(I,TEXT("equipSlot"));
    if(C==TEXT("weapon_melee"))return 0;if(C==TEXT("weapon_ranged"))return 1;
    if(Text(I,TEXT("weaponType"))==TEXT("shield"))return 2;
    if(!Slot.IsEmpty()&&Slot!=TEXT("weapon"))return 3;
    const TArray<FString> Names={TEXT("weapon"),TEXT("weapon_ranged"),TEXT("shield"),TEXT("armor"),TEXT("consumable"),TEXT("enhancement"),TEXT("material"),TEXT("tribute"),TEXT("gold")};
    const int32 N=Names.Find(C);return N<0?9:N;
}
}
