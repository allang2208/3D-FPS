#pragma once
#include "ColdSteelInventoryTypes.h"
#include "HAL/PlatformTime.h"

template<typename FCheck>
void RunColdSteelMultiSwapRulesAudit(const FColdSteelProfile& Base,FCheck Check)
{
    using namespace ColdSteelInventory;
    auto Item=[](const TCHAR* Id,int32 W,int32 H,int32 Cell){FColdSteelItem I;I.InstanceId=Id;I.Definition=Id;I.Width=W;I.Height=H;I.Cell=Cell;I.Data=FString::Printf(TEXT("{\"grid_w\":%d,\"grid_h\":%d}"),W,H);return I;};
    auto Valid=[&](const FColdSteelProposal& P){auto Profile=Base;Profile.Items=P.Items;FString Reason;return P.bValid&&Validate(Profile,Reason);};
    auto At=[](const FColdSteelProposal& P,const TCHAR* Id){const auto* I=P.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Id;});return I?I->Cell:-1;};
    TArray<FColdSteelItem> Items={Item(TEXT("large"),5,2,0),Item(TEXT("a"),1,1,8),Item(TEXT("b"),1,1,9),Item(TEXT("c"),2,2,10)};
    const auto P=Move(Items,TEXT("large"),0,8);
    Check(Valid(P)&&At(P,TEXT("large"))==8&&At(P,TEXT("a"))==0&&At(P,TEXT("b"))==1&&At(P,TEXT("c"))==2,TEXT("multi swap preserves translated mixed-size layout inside source footprint"));
    auto Reversed=Items;Reversed.Swap(0,3);Reversed.Swap(1,2);const auto Q=Move(Reversed,TEXT("large"),0,8);
    Check(Valid(Q)&&At(P,TEXT("a"))==At(Q,TEXT("a"))&&At(P,TEXT("b"))==At(Q,TEXT("b"))&&At(P,TEXT("c"))==At(Q,TEXT("c")),TEXT("multi swap placement independent of array order"));
    Items={Item(TEXT("large"),5,2,0),Item(TEXT("square"),2,2,9),Item(TEXT("bar"),3,1,11)};
    const auto Backtrack=Move(Items,TEXT("large"),0,8);
    Check(Valid(Backtrack)&&At(Backtrack,TEXT("square"))==0&&At(Backtrack,TEXT("bar"))==2,TEXT("backtracking moves centered square aside to fit long bar in source region"));
    // Overlapping source/target needs cells outside the source's remaining strip.
    Items={Item(TEXT("large"),5,2,0),Item(TEXT("a"),2,2,5)};
    Check(Valid(Move(Items,TEXT("large"),0,1)),TEXT("partially overlapping swap uses nearby continuous empty space"));
    // Fill every cell except the moving and displaced rectangles: no fallback space.
    for(int32 C=0;C<72;++C)if(Owner(Items,0,C)<0)Items.Add(Item(*FString::Printf(TEXT("fixed%d"),C),1,1,C));
    const auto Impossible=Move(Items,TEXT("large"),0,1);
    Check(!Impossible.bValid&&Impossible.Items.Num()==Items.Num()&&At(Impossible,TEXT("large"))==0&&At(Impossible,TEXT("a"))==5,TEXT("fragmented full bag rejects atomically despite sufficient total area"));
    Items={Item(TEXT("large"),5,2,0)};
    for(int32 Y=0;Y<2;++Y)for(int32 X=0;X<5;++X)Items.Add(Item(*FString::Printf(TEXT("small%d"),Y*5+X),1,1,8+X+18*Y));
    for(int32 C=0;C<72;++C)if(Owner(Items,0,C)<0)Items.Add(Item(*FString::Printf(TEXT("fixed%d"),C),1,1,C));
    const double Start=FPlatformTime::Seconds();const auto Full=Move(Items,TEXT("large"),0,8);
    Check(Valid(Full)&&Full.Items.Num()==Items.Num(),TEXT("full backpack swaps one large item for ten instances without spare cells"));
    bool Stable=true;for(const auto& I:Items)if(I.InstanceId.StartsWith(TEXT("fixed")))Stable&=At(Full,*I.InstanceId)==I.Cell;
    Check(Stable,TEXT("multi swap leaves every unrelated neighbour anchored"));
    UE_LOG(LogTemp,Display,TEXT("InventoryDrag: multi swap full-bag elapsed_ms=%.3f"),(FPlatformTime::Seconds()-Start)*1000);
}
