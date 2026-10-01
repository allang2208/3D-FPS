#include "ColdSteelInventoryTypes.h"
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
FColdSteelProposal Transfer(const TArray<FColdSteelItem>& Items,const FString& Id,int32 Destination,int32 Cell,FIntPoint Grid,int32 Orientation)
{
    FColdSteelProposal R;R.Items=Items;R.Reason=TEXT("无法移动：空间不足或目标无效，物品保留原处");
    const int32 From=Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(From<0||Grid.X<1||Grid.Y<1)return R;
    const int32 Capacity=Grid.X*Grid.Y;
    auto I=Items[From];const int32 OldPlace=I.Place,OldCell=I.Cell;
    // 背包装备槽(14)里的背包不进夹层：卸下背包必须走背包格路径，让规则层校验扩展格并自动搬夹层。
    if(OldPlace==1&&OldCell==14){R.Reason=TEXT("背包装备请先卸到背包");return R;}
    if(OldPlace!=0&&OldPlace!=1&&OldPlace!=4&&OldPlace!=Place)return R;
    if(Destination!=Place&&Destination!=0&&Destination!=1)return R;
    if(Destination==Place&&Cell>=Capacity)return R;
    // 背包与夹层落点都带待提交朝向；装备来源保持作者朝向（目的地不会是装备槽以外的其他格子形状）。
    if(Destination==Place||Destination==0)ApplyOrientation(I,Orientation);
    if(OldPlace==Destination&&Cell==OldCell&&I.Width==Items[From].Width&&I.Height==Items[From].Height){R.bValid=true;R.Reason.Empty();return R;}
    if(Destination==Place&&Cell<0)
    {
        int32 Found=-1;for(int32 C=0;C<Capacity;++C)if(Fits(Items,I,C,Grid)){Found=C;break;}
        if(Found<0)return R;Cell=Found;
    }
    R.Items.RemoveAt(From);
    if(Destination==Place)
    {
        I.Container.Empty();
        if(Cell<0){if(!InsertCompartment(R.Items,I,Grid))return R;}
        else
        {
            TSet<int32> Blockers;
            for(int32 Y=0;Y<I.Height;++Y)for(int32 X=0;X<I.Width;++X){const int32 N=Owner(R.Items,Place,Cell+Y*Grid.X+X,FString(),Grid);if(N>=0)Blockers.Add(N);}
            if(Blockers.Num()>1){R.Reason=TEXT("没有足够的连续空间，请先腾出夹层格");return R;}
            if(Blockers.Num()==1)
            {
                auto& T=R.Items[*Blockers.CreateConstIterator()];
                if(Compatible(T,I))
                {
                    const int64 Amount=FMath::Min(I.Count,T.StackMax-T.Count);
                    if(Amount<=0){R.Reason=TEXT("目标堆叠已满");return R;}
                    T.Count+=Amount;I.Count-=Amount;
                    if(I.Count>0){I.Place=OldPlace;I.Cell=OldCell;R.Items.Add(I);} // 余量回原位
                    R.bValid=true;R.Reason.Empty();return R;
                }
                // 单件占用＝交换：被压物品回到本次移动腾出的位置（夹层原格或背包原格）。
                TArray<FColdSteelItem> Displaced;for(int32 N=R.Items.Num()-1;N>=0;--N)if(Blockers.Contains(N)){Displaced.Add(R.Items[N]);R.Items.RemoveAt(N);}
                I.Place=Place;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);
                for(auto& D:Displaced)
                {
                    bool bBack=false;
                    if(OldPlace==Place)bBack=Fits(R.Items,D,OldCell,Grid);
                    else if(OldPlace==0)bBack=ColdSteelInventory::Fits(R.Items,D,OldCell);
                    if(!bBack){R.Items=Items;R.Reason=TEXT("没有连续空间安置被交换物品");return R;}
                    D.Place=OldPlace==Place?Place:0;D.Cell=OldCell;D.Map.Empty();D.Position=FVector::ZeroVector;D.Container.Empty();
                    R.Items.Add(D);
                }
            }
            else {I.Place=Place;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);}
        }
    }
    else if(Destination==1)
    {
        // 夹层直接穿装备：与仓库 Transfer 的装备分支同口径（占用单槽/双手占副手槽），
        // 被换下的装备回到夹层腾出的原格，放不下则整次取消。
        if(!CanEquip(I,Cell)||Locked(R.Items,Cell)){R.Reason=TEXT("物品与装备槽不兼容或被双手武器占用");return R;}
        TSet<int32> Blockers;
        if(const int32 N=Owner(R.Items,1,Cell);N>=0)Blockers.Add(N);
        if(Flag(I,TEXT("isTwoHanded"))&&(Cell==6||Cell==9)){const int32 N=Owner(R.Items,1,Cell==6?8:11);if(N>=0)Blockers.Add(N);}
        TArray<FColdSteelItem> Displaced;for(int32 N=R.Items.Num()-1;N>=0;--N)if(Blockers.Contains(N)){Displaced.Add(R.Items[N]);R.Items.RemoveAt(N);}
        I.Place=1;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);
        for(auto& D:Displaced)
        {
            if(!Fits(R.Items,D,OldCell,Grid)){R.Items=Items;R.Reason=TEXT("夹层放不下被交换装备");return R;}
            D.Place=Place;D.Cell=OldCell;D.Map.Empty();D.Position=FVector::ZeroVector;R.Items.Add(D);
        }
        if(Cell==6||Cell==9)R.ActiveWeaponSlot=Cell;
    }
    else
    {
        I.Container.Empty();
        if(Cell<0)
        {
            if(!Insert(R.Items,I)&&CanRotate(I)){ApplyOrientation(I,I.bRotated?0:1);if(!Insert(R.Items,I))return R;}
        }
        else
        {
            const int32 BagRowCount=BagRows(R.Items);
            if(Cell<0||Cell>=BagRowCount*18||Cell%18+I.Width>18||Cell/18+I.Height>BagRowCount){R.Reason=TEXT("物品超出背包边界，请向内移动");return R;}
            TSet<int32> Blockers;
            for(int32 Y=0;Y<I.Height;++Y)for(int32 X=0;X<I.Width;++X){const int32 N=Owner(R.Items,0,Cell+Y*18+X);if(N>=0)Blockers.Add(N);}
            if(Blockers.Num()>1){R.Reason=TEXT("没有足够的连续空间安置被交换物品");return R;}
            if(Blockers.Num()==1)
            {
                auto& T=R.Items[*Blockers.CreateConstIterator()];
                if(Compatible(T,I))
                {
                    const int64 Amount=FMath::Min(I.Count,T.StackMax-T.Count);
                    if(Amount<=0){R.Reason=TEXT("目标堆叠已满");return R;}
                    T.Count+=Amount;I.Count-=Amount;
                    if(I.Count>0){I.Place=Place;I.Cell=OldCell;R.Items.Add(I);} // 余量留在夹层原格
                    R.bValid=true;R.Reason.Empty();return R;
                }
                TArray<FColdSteelItem> Displaced;for(int32 N=R.Items.Num()-1;N>=0;--N)if(Blockers.Contains(N)){Displaced.Add(R.Items[N]);R.Items.RemoveAt(N);}
                I.Place=0;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);
                for(auto& D:Displaced)
                {
                    // 被压的背包物品换进夹层腾出的原格；放不下则整次移动取消。
                    if(!Fits(R.Items,D,OldCell,Grid)){R.Items=Items;R.Reason=TEXT("夹层放不下被交换物品");return R;}
                    D.Place=Place;D.Cell=OldCell;D.Map.Empty();D.Position=FVector::ZeroVector;D.Container.Empty();R.Items.Add(D);
                }
            }
            else {I.Place=0;I.Cell=Cell;I.Map.Empty();I.Position=FVector::ZeroVector;R.Items.Add(I);}
        }
    }
    R.bValid=true;R.Reason.Empty();return R;
}
}
}
