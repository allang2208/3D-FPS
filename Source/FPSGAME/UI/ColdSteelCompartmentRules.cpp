#include "ColdSteelInventoryTypes.h"
#include "ColdSteelWarehouseRules.h"
#include "ColdSteelSwapPlacement.h"
using namespace ColdSteelInventory;

// 夹层（Place 5）是背包装备撑出的独立格空间：网格尺寸＝长×宽（列×行），由装备的背包
// 字段（bagCompartmentColumns/Rows）定义，容量＝列×行。占用是纯几何矩形（Owner 已带
// 夹层分支，折行按传入网格），本文件只负责"放进去/在夹层内挪动/放回背包/穿装备"的
// 转移规则，不与仓库分页逻辑纠缠。
namespace ColdSteelInventory
{
namespace ColdSteelCompartment
{
bool Fits(const TArray<FColdSteelItem>& Items,const FColdSteelItem& I,int32 Cell,FIntPoint Grid)
{
    if(Grid.X<1||Grid.Y<1)return false;
    if(Cell<0||Cell>=Grid.X*Grid.Y||I.Width<1||I.Height<1||Cell%Grid.X+I.Width>Grid.X||Cell/Grid.X+I.Height>Grid.Y) return false;
    // 折行必须用调用方传入的网格：加载校验时装备栏可能还没进 Items，按表推导会得到零网格
    // 而跳过重叠判定，坏档就会漏检。
    for(int32 Y=0;Y<I.Height;++Y)for(int32 X=0;X<I.Width;++X)if(Owner(Items,Place,Cell+Y*Grid.X+X,FString(),Grid)>=0) return false;
    return true;
}
static bool InsertCompartment(TArray<FColdSteelItem>& Items,FColdSteelItem I,FIntPoint Grid,int32 Preferred=-1)
{
    if(I.Count<=0||I.StackMax<=0||Grid.X<1)return false;
    const int32 Capacity=Grid.X*Grid.Y;
    auto Next=Items;
    for(auto& T:Next)if(T.Place==Place&&Compatible(T,I)){const int64 Amount=FMath::Min(I.Count,T.StackMax-T.Count);T.Count+=Amount;I.Count-=Amount;if(!I.Count){Items=MoveTemp(Next);return true;}}
    bool First=true;
    while(I.Count>0)
    {
        int32 Cell=Fits(Next,I,Preferred,Grid)?Preferred:-1;
        if(Cell<0)for(int32 C=0;C<Capacity;++C)if(Fits(Next,I,C,Grid)){Cell=C;break;}
        if(Cell<0)return false;
        auto Part=I;Part.Place=Place;Part.Cell=Cell;Part.Map.Empty();Part.Position=FVector::ZeroVector;Part.Container.Empty();Part.Count=FMath::Min(I.Count,I.StackMax);
        if(!First)Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Next.Add(Part);First=false;I.Count-=Part.Count;Preferred=-1;
    }
    Items=MoveTemp(Next);return true;
}
FColdSteelProposal Transfer(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Destination,int32 Cell,FIntPoint Grid,int32 WarehouseCapacity,int32 Orientation)
{
    FColdSteelProposal R;R.Items=Items;R.Reason=TEXT("无法移动：空间不足或目标无效，物品保留原处");
    const int32 From=Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(From<0||Grid.X<1||Grid.Y<1||Cell< -1)return R;
    const FColdSteelItem Source=Items[From];
    const int32 OldPlace=Source.Place,OldCell=Source.Cell;
    if(OldPlace!=0&&OldPlace!=1&&OldPlace!=4&&OldPlace!=Place)return R;
    if(Destination!=Place&&!(OldPlace==Place&&(Destination==0||Destination==1)))return R;
    auto Work=Items;Work.RemoveAt(From);
    auto Moving=Source;ApplyOrientation(Moving,Destination==1?0:Orientation);
    Moving.Container.Empty();Moving.Map.Empty();Moving.Position=FVector::ZeroVector;
    auto Complete=[&]()
    {
        R.Items=MoveTemp(Work);R.bValid=true;R.Reason.Empty();return R;
    };
    // Reuse the backpack's bounded joint placement search with the source grid's
    // column count. Equipment return permits rotation; explicit grid swaps do not.
    auto ReturnItems=[&](const TArray<FColdSteelItem>& Returned,bool AutoRotate,bool BagFallback)->bool
    {
        if(Returned.IsEmpty())return true;
        int32 ReturnPlace=OldPlace==1?0:OldPlace;
        FIntPoint ReturnGrid=ReturnPlace==Place?CompartmentGrid(Work):FIntPoint(18,ReturnPlace==4?ColdSteelWarehouse::Rows:BagRows(Work));
        const int32 Start=ReturnPlace==4?OldCell/ColdSteelWarehouse::CellsPerPage*ColdSteelWarehouse::CellsPerPage:0;
        if(ReturnPlace==4)ReturnGrid.Y=FMath::Min(ReturnGrid.Y,(WarehouseCapacity-Start)/18);
        auto Anchor=Source;
        if(OldPlace==1)Anchor.Cell=0;
        else if(ReturnPlace==Place&&ReturnGrid.X>0)
            Anchor.Cell=FMath::Min(OldCell/Grid.X,FMath::Max(0,ReturnGrid.Y-1))*ReturnGrid.X+FMath::Min(OldCell%Grid.X,ReturnGrid.X-1);
        bool Exhausted=false;
        if(PlaceDisplaced(Work,Returned,Anchor,Cell,Exhausted,ReturnPlace,Start,ReturnGrid.Y,ReturnPlace==4?Source.Container:FString(),AutoRotate,ReturnGrid.X))return true;
        if(BagFallback&&ReturnPlace==Place)
        {
            Anchor.Cell=0;Anchor.Place=0;
            bool BagExhausted=false;
            if(PlaceDisplaced(Work,Returned,Anchor,0,BagExhausted,0,0,BagRows(Work),FString(),true))return true;
            Exhausted|=BagExhausted;
        }
        R.Reason=Exhausted?TEXT("自动摆放较复杂，请调整空间后重试"):TEXT("没有连续空间安置被交换物品，原布局保留");
        return false;
    };
    if(Destination==1)
    {
        if(!CanEquip(Moving,Cell)||Locked(Work,Cell)){R.Reason=TEXT("物品与装备槽不兼容或被双手武器占用");return R;}
        TArray<FColdSteelItem> Returned;
        const int32 Offhand=Flag(Moving,TEXT("isTwoHanded"))&&(Cell==6||Cell==9)?(Cell==6?8:11):-1;
        for(int32 N=Work.Num()-1;N>=0;--N)if(Work[N].Place==1&&(Work[N].Cell==Cell||Work[N].Cell==Offhand))
        {Returned.Add(Work[N]);Work.RemoveAt(N);}
        Moving.Place=1;Moving.Cell=Cell;Work.Add(Moving);
        if(!ReconcileBagCapacity(Items,Work,R.Reason)||!ReturnItems(Returned,true,true))return R;
        if(Cell==6||Cell==9)R.ActiveWeaponSlot=Cell;
        return Complete();
    }
    if(OldPlace==1&&OldCell==14&&Cell<0)
    {R.Reason=TEXT("背包装备不能放入自身夹层，请先卸到背包或拖到另一件背包装备上替换");return R;}
    if(Cell<0)
    {
        auto InsertAuto=[&](const FColdSteelItem& I){return Destination==Place?InsertCompartment(Work,I,Grid):ColdSteelInventory::Insert(Work,I);};
        bool Inserted=InsertAuto(Moving);
        if(!Inserted&&CanRotate(Moving)){ApplyOrientation(Moving,Moving.bRotated?0:1);Inserted=InsertAuto(Moving);}
        if(!Inserted){R.Reason=TEXT("空间不足，物品保留原处");return R;}
        return Complete();
    }
    const FIntPoint TargetGrid=Destination==Place?Grid:FIntPoint(18,BagRows(Work));
    if(Cell>=TargetGrid.X*TargetGrid.Y||Cell%TargetGrid.X+Moving.Width>TargetGrid.X||Cell/TargetGrid.X+Moving.Height>TargetGrid.Y)
    {R.Reason=TEXT("物品超出网格边界，请向内移动");return R;}
    TSet<int32> Blockers;
    for(int32 Y=0;Y<Moving.Height;++Y)for(int32 X=0;X<Moving.Width;++X)
        if(const int32 N=Owner(Work,Destination,Cell+Y*TargetGrid.X+X,FString(),Grid);N>=0)Blockers.Add(N);
    if(Blockers.Num()==1)
    {
        auto& Target=Work[*Blockers.CreateConstIterator()];
        if(Compatible(Target,Moving))
        {
            const int64 Amount=FMath::Min(Moving.Count,Target.StackMax-Target.Count);
            if(Amount<=0){R.Reason=TEXT("目标堆叠已满");return R;}
            Target.Count+=Amount;
            if(Moving.Count>Amount){auto Remainder=Source;Remainder.Count-=Amount;Work.Add(Remainder);}
            return Complete();
        }
    }
    TArray<FColdSteelItem> Returned;
    for(int32 N=Work.Num()-1;N>=0;--N)if(Blockers.Contains(N)){Returned.Add(Work[N]);Work.RemoveAt(N);}
    Moving.Place=Destination;Moving.Cell=Cell;Work.Add(Moving);
    if(OldPlace==1)
    {
        // The compatible item under the actual drop anchor takes the vacated
        // equipment slot. Additional covered items and the offhand return jointly.
        const int32 Pick=Returned.IndexOfByPredicate([&](const auto& I)
        {
            return I.Cell%TargetGrid.X<=Cell%TargetGrid.X&&Cell%TargetGrid.X<I.Cell%TargetGrid.X+I.Width
                &&I.Cell/TargetGrid.X<=Cell/TargetGrid.X&&Cell/TargetGrid.X<I.Cell/TargetGrid.X+I.Height
                &&CanEquip(I,OldCell)&&!Locked(Work,OldCell);
        });
        if(Pick>=0)
        {
            auto Replacement=Returned[Pick];Returned.RemoveAt(Pick);ApplyOrientation(Replacement,0);
            if(Flag(Replacement,TEXT("isTwoHanded"))&&(OldCell==6||OldCell==9))
                if(const int32 N=Owner(Work,1,OldCell==6?8:11);N>=0){Returned.Add(Work[N]);Work.RemoveAt(N);}
            Replacement.Place=1;Replacement.Cell=OldCell;Replacement.Container.Empty();Replacement.Map.Empty();Replacement.Position=FVector::ZeroVector;
            Work.Add(Replacement);
            if(OldCell==6||OldCell==9)R.ActiveWeaponSlot=OldCell;
        }
        else if(OldCell==14)
        {R.Reason=TEXT("背包装备不能放入自身夹层，请拖到另一件背包装备上替换");return R;}
        if(!ReconcileBagCapacity(Items,Work,R.Reason))return R;
        // A capacity change must not silently relocate the player's explicit drop.
        const auto* Placed=Work.FindByPredicate([&](const auto& I){return I.InstanceId==Id;});
        if(!Placed||Placed->Place!=Destination||Placed->Cell!=Cell)
        {R.Reason=TEXT("更换后的夹层无法容纳当前落点，请先把背包装备卸到背包");return R;}
    }
    if(!ReturnItems(Returned,OldPlace==1,false))return R;
    return Complete();
}
}
}
