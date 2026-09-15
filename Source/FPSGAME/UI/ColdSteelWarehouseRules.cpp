#include "ColdSteelWarehouseRules.h"
#include "ColdSteelSwapPlacement.h"
using namespace ColdSteelInventory;
namespace ColdSteelWarehouse
{
bool Fits(const TArray<FColdSteelItem>& Items,const FColdSteelItem& I,int32 Cell,int32 Capacity)
{
    if(Cell<0||Cell>=Capacity||I.Width<1||I.Height<1||Cell%Columns+I.Width>Columns||(Cell%CellsPerPage)/Columns+I.Height>Rows)return false;
    for(int32 Y=0;Y<I.Height;++Y)for(int32 X=0;X<I.Width;++X)if(Owner(Items,Place,Cell+Y*Columns+X)>=0)return false;
    return true;
}
bool MigrateLayout(FColdSteelProfile& Profile)
{
    if(Profile.WarehouseLayoutVersion==1)return true;
    FString Reason;if(Profile.WarehouseLayoutVersion!=0||!Validate(Profile,Reason))return false;
    auto Next=Profile;TArray<FColdSteelItem> Stored;
    for(const auto& I:Next.Items)if(I.Place==Place)Stored.Add(I);
    Stored.Sort([](const auto& A,const auto& B){return A.Cell<B.Cell;});Next.Items.RemoveAll([](const auto& I){return I.Place==Place;});
    for(auto I:Stored){
        int32 Target=-1;
        while(Target<0){
            const int32 Capacity=Next.WarehousePages*CellsPerPage;
            for(int32 C=0;C<Capacity;++C)if(Fits(Next.Items,I,C,Capacity)){Target=C;break;}
            if(Target<0&&++Next.WarehousePages>MaxPages)return false;
        }
        I.Cell=Target;Next.Items.Add(I);
    }
    Next.WarehouseLayoutVersion=1;if(!Validate(Next,Reason))return false;Profile=MoveTemp(Next);return true;
}
bool Insert(TArray<FColdSteelItem>& Items,FColdSteelItem I,int32 Capacity,int32 Preferred)
{
    if(I.Count<=0||I.StackMax<=0||Capacity<1||Preferred>=Capacity)return false;
    auto Next=Items;
    TArray<int32> Stacks;const int32 PreferredStack=Preferred>=0?Owner(Next,Place,Preferred):-1;
    if(PreferredStack>=0)Stacks.Add(PreferredStack);
    for(int32 N=0;N<Next.Num();++N)if(N!=PreferredStack&&Next[N].Place==Place)Stacks.Add(N);
    for(int32 N:Stacks)if(Compatible(Next[N],I)){
        const int64 Added=FMath::Min(I.Count,Next[N].StackMax-Next[N].Count);Next[N].Count+=Added;I.Count-=Added;
        if(!I.Count){Items=MoveTemp(Next);return true;}
    }
    bool First=true;
    while(I.Count>0){
        int32 Cell=Fits(Next,I,Preferred,Capacity)?Preferred:-1;
        if(Cell<0)for(int32 C=0;C<Capacity;++C)if(Fits(Next,I,C,Capacity)){Cell=C;break;}
        if(Cell<0)return false;
        auto Part=I;Part.Place=Place;Part.Cell=Cell;Part.Map.Empty();Part.Position=FVector::ZeroVector;
        Part.Count=FMath::Min(I.Count,I.StackMax);
        if(!First)Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Next.Add(Part);First=false;I.Count-=Part.Count;Preferred=-1;
    }
    Items=MoveTemp(Next);return true;
}
FColdSteelProposal Transfer(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Destination,int32 Cell,int32 Capacity,int32 Page)
{
    FColdSteelProposal R;R.Items=Items;R.Reason=TEXT("无法移动：空间不足或目标无效，物品保留原处");
    const int32 From=Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(From<0||Cell< -1||Capacity<1)return R;
    auto I=Items[From];const int32 OldPlace=I.Place,OldCell=I.Cell;
    if(OldPlace!=0&&OldPlace!=1&&OldPlace!=Place)return R;
    if(Destination!=Place&&!(OldPlace==Place&&(Destination==0||Destination==1)))return R;
    if(Destination==Place&&Cell>=Capacity)return R;
    if(OldPlace==Destination&&Cell==OldCell){R.bValid=true;R.Reason.Empty();return R;}
    if(OldPlace==Place&&Destination==Place&&Cell<0)return R;
    R.Items.RemoveAt(From);
    if(Cell==-1){
        if(Destination==0){if(!ColdSteelInventory::Insert(R.Items,I))return R;}
        else if(Destination==Place){
            int32 Preferred=-1;Page=FMath::Clamp(Page,0,(Capacity-1)/CellsPerPage);
            for(int32 C=Page*CellsPerPage;C<FMath::Min(Capacity,(Page+1)*CellsPerPage);++C)if(Fits(R.Items,I,C,Capacity)){Preferred=C;break;}
            if(!Insert(R.Items,I,Capacity,Preferred))return R;
        }else return R;
    }else{
        TSet<int32> Blockers;
        if(Destination==1){
            if(!CanEquip(I,Cell)||Locked(R.Items,Cell)){R.Reason=TEXT("物品与装备槽不兼容或被双手武器占用");return R;}
            int32 N=Owner(R.Items,1,Cell);if(N>=0)Blockers.Add(N);
            if(Flag(I,TEXT("isTwoHanded"))&&(Cell==6||Cell==9)){N=Owner(R.Items,1,Cell==6?8:11);if(N>=0)Blockers.Add(N);}
        }else{
            const int32 Row=Destination==Place?(Cell%CellsPerPage)/Columns:Cell/Columns;
            if(Cell<0||Cell>=(Destination==Place?Capacity:72)||Cell%Columns+I.Width>Columns||Row+I.Height>(Destination==Place?Rows:4)){R.Reason=TEXT("物品超出网格边界，请向内移动");return R;}
            for(int32 Y=0;Y<I.Height;++Y)for(int32 X=0;X<I.Width;++X){const int32 N=Owner(R.Items,Destination,Cell+Y*Columns+X);if(N>=0)Blockers.Add(N);}
            if(Blockers.Num()==1){auto& T=R.Items[*Blockers.CreateConstIterator()];if(Compatible(T,I)){
                const int64 Amount=FMath::Min(I.Count,T.StackMax-T.Count);if(Amount<=0){R.Reason=TEXT("目标堆叠已满");return R;}
                T.Count+=Amount;I.Count-=Amount;if(I.Count>0)R.Items.Add(I);R.bValid=true;R.Reason.Empty();return R;
            }}
        }
        TArray<FColdSteelItem> Displaced;for(int32 N=R.Items.Num()-1;N>=0;--N)if(Blockers.Contains(N)){Displaced.Add(R.Items[N]);R.Items.RemoveAt(N);}
        I.Place=Destination;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);
        if(!Displaced.IsEmpty()){
            auto Source=Items[From];const int32 ReturnPlace=OldPlace==Place?Place:0;
            if(OldPlace==1)Source.Cell=0;
            const int32 Start=ReturnPlace==Place?(OldCell/CellsPerPage)*CellsPerPage:0;
            bool Exhausted=false;
            if(!PlaceDisplaced(R.Items,MoveTemp(Displaced),Source,Cell,Exhausted,ReturnPlace,Start,ReturnPlace==Place?Rows:4)){
                R.Items=Items;R.Reason=Exhausted?TEXT("自动摆放较复杂，请调整落点后重试"):TEXT("没有连续空间安置被交换物品");return R;
            }
        }
        if(Destination==1&&(Cell==6||Cell==9))R.ActiveWeaponSlot=Cell;
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
