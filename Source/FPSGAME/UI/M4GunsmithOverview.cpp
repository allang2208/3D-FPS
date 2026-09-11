#include "M4GunsmithWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace {
TSharedRef<STextBlock> Text(const FString& S,int32 Size,FLinearColor Color,bool Number=false)
{return SNew(STextBlock).Text(FText::FromString(S)).Font(Number?ColdSteelUI::NumberFont(Size):ColdSteelUI::TextFont(Size)).ColorAndOpacity(Color).AutoWrapText(true);}
FString Value(double N,int32 Digits,const TCHAR* Unit){return FString::Printf(TEXT("%.*f%s"),Digits,N,Unit);}
}
void UM4GunsmithWidget::RefreshPresentation()
{
    PreviewMotion=1.f;
    auto* G=Model();auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* I=P->FindItem(G->Instance());if(!I||!G->Weapon(G->Definition()))return;
    const auto S=G->Calculate(G->Definition(),G->Draft());
    const auto B=G->Calculate(G->Definition(),bCompareFactory?FGunsmithParts():G->Installed(*I));
    Overview.Reset();
    auto Row=[this](const TCHAR* Name,double Before,double After,int32 Digits,const TCHAR* Unit,bool Lower=false)
    {
        const double D=After-Before;FGunsmithOverviewRow R;R.Label=Name;R.Current=Value(Before,Digits,Unit);R.Final=Value(After,Digits,Unit);
        R.Delta=FMath::Abs(D)<.00001?TEXT("—"):FString(D>0?TEXT("+"):TEXT(""))+Value(D,Digits,Unit);
        R.Benefit=FMath::Abs(D)<.00001?0:((D>0)!=Lower?1:-1);Overview.Add(R);
    };
    const double AttackSpeed=FMath::Max(1.f,P->Derived(TEXT("aspd")));
    Row(TEXT("开镜耗时"),B.ADS*1000,S.ADS*1000,0,TEXT(" ms"),true);
    Row(TEXT("弹匣容量"),B.Capacity,S.Capacity,0,TEXT(" 发"));
    Row(TEXT("普通换弹"),B.Reload,S.Reload,2,TEXT(" s"),true);
    Row(TEXT("空仓换弹"),B.EmptyReload,S.EmptyReload,2,TEXT(" s"),true);
    Row(TEXT("射击间隔"),B.Interval*1000/AttackSpeed,S.Interval*1000/AttackSpeed,0,TEXT(" ms"),true);
    Row(TEXT("射速"),60*AttackSpeed/B.Interval,60*AttackSpeed/S.Interval,0,TEXT(" /min"));
    Row(TEXT("基础命中伤害"),B.Damage+P->Derived(TEXT("atk")),S.Damage+P->Derived(TEXT("atk")),0,TEXT(""));
    Row(TEXT("后坐力 ↓"),B.Recoil,S.Recoil,1,TEXT(""),true);
    Row(TEXT("枪械稳定性 ↑"),B.Handling.Stability,S.Handling.Stability,1,TEXT(" 分"));
    Row(TEXT("首发上跳"),B.Handling.FirstShotDegrees(),S.Handling.FirstShotDegrees(),3,TEXT("°"),true);
    Row(TEXT("连射上跳/发"),B.Handling.MaxVerticalDegrees(),S.Handling.MaxVerticalDegrees(),3,TEXT("°"),true);
    Row(TEXT("抖动幅度指数 ↓"),B.Shake,S.Shake,1,TEXT(""),true);
    Row(TEXT("镜头回稳90%"),B.Handling.ADSRecoveryMilliseconds(),S.Handling.ADSRecoveryMilliseconds(),0,TEXT(" ms"),true);
    Row(TEXT("腰射散布系数"),B.Spread,S.Spread,2,TEXT("×"),true);
    Row(TEXT("最大命中距离"),B.Range,S.Range,0,TEXT(" m"));
    if(S.Speed<=0)Overview.Add({TEXT("子弹速度"),TEXT("即时命中"),TEXT("即时命中"),TEXT("—"),0});
    else Row(TEXT("子弹速度"),B.Speed,S.Speed,0,TEXT(" m/s"));
    const auto BeforeParts=bCompareFactory?FGunsmithParts():G->Installed(*I);
    Overview.Add({TEXT("瞄具倍率"),BeforeParts.FindRef(TEXT("optic"))==TEXT("lpvo_1_6x")?TEXT("1–6×"):BeforeParts.FindRef(TEXT("optic"))==TEXT("prism_scope_2x")?TEXT("2×"):TEXT("1×"),G->Draft().FindRef(TEXT("optic"))==TEXT("lpvo_1_6x")?TEXT("1–6×"):G->Draft().FindRef(TEXT("optic"))==TEXT("prism_scope_2x")?TEXT("2×"):TEXT("1×"),TEXT("—"),0});
    Overview.Add({TEXT("机械瞄具"),BeforeParts.Contains(TEXT("optic"))?TEXT("折下"):TEXT("竖起"),G->Draft().Contains(TEXT("optic"))?TEXT("折下"):TEXT("竖起"),TEXT("—"),0});
    StatusText=FString::Printf(TEXT("待应用 · %d 项     %s"),G->Pending(),*G->Message());
    if(OptionScroll)
    {
        const auto* Options=G->Weapon(G->Definition())->Options.Find(SelectedCategory);
        FString Signature=G->Definition()+TEXT("|")+SelectedCategory;
        if(Options)for(const auto& O:*Options)Signature+=TEXT("|")+O.Id+O.Name+O.Description;
        if(Signature!=OptionsSignature)
        {
            const bool ChangedCategory=OptionsCategory!=SelectedCategory;
            OptionScroll->ClearChildren();OptionCards.Reset();OptionsSignature=Signature;OptionsCategory=SelectedCategory;
            if(Options)for(const auto& O:*Options)
            {
                auto Card=BuildOption(SelectedCategory,O.Id);OptionCards.Add(O.Id,Card);
                OptionScroll->AddSlot().Padding(0,0,10,4)[Card];
            }
            if(ChangedCategory)OptionScroll->ScrollToStart();
        }
    }
    if(ModificationList)
    {
        ModificationList->ClearChildren();
        for(const auto& SlotKey:G->Slots())if(const auto* O=G->Option(G->Definition(),SlotKey,G->Draft().FindRef(SlotKey)))
        {
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,2)[Text(O->Name,15,ColdSteelUI::TextPrimary)];
            for(const auto& Effect:O->Effects)ModificationList->AddSlot().AutoHeight().Padding(8,0,0,1)[Text(Effect.Key,13,Effect.Value>0?ColdSteelUI::Success:Effect.Value<0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary)];
        }
        if(S.ActiveParts==0)ModificationList->AddSlot().AutoHeight()[Text(TEXT("原厂配置 · 无已选改造部件"),14,ColdSteelUI::TextSecondary)];
    }
    if(OverviewList)
    {
        OverviewList->ClearChildren();
        auto Cells=[](const TArray<FString>& Values,int32 FontSize,FLinearColor FinalColor,bool Heading)
        {
            auto H=SNew(SHorizontalBox);const float Widths[]={1.28f,1.f,1.f,.9f};
            for(int32 J=0;J<4;++J)H->AddSlot().FillWidth(Widths[J]).VAlign(VAlign_Center).Padding(3,1)
                [Text(Values[J],FontSize,J>=2?FinalColor:ColdSteelUI::TextSecondary,!Heading&&J>0)];
            return H;
        };
        OverviewList->AddSlot().AutoHeight()[Cells({TEXT("项目"),bCompareFactory?TEXT("原厂"):TEXT("当前"),TEXT("改造后"),TEXT("变化")},13,ColdSteelUI::Accent,true)];
        for(const auto& R:Overview)
        {
            const auto Color=R.Benefit>0?ColdSteelUI::Success:R.Benefit<0?ColdSteelUI::Warning:ColdSteelUI::TextPrimary;
            FString Hint;
            if(R.Label.Contains(TEXT("稳定性")))Hint=TEXT("0–100分，越高越好。综合开火抖动幅度与回稳速度；原厂参考值50分，不代表命中率。");
            else if(R.Label.Contains(TEXT("回稳")))Hint=TEXT("开镜状态下，镜头震荡包络衰减90%的理论时间。不会自动把瞄准点拉回开火前的位置。");
            else if(R.Label.Contains(TEXT("上跳")))Hint=TEXT("控制瞄准方向的逐发垂直后坐角度。首发为完全恢复后的第一枪；连射值为第9发起的单发上限，不包含随机晃动。");
            else if(R.Label.Contains(TEXT("后坐力")))Hint=TEXT("后坐力指数，越低越好。统一参考值100；配件倍率相乘，实际射击与面板使用相同结果。");
            OverviewList->AddSlot().AutoHeight().Padding(0,0,0,1)[SNew(SBorder).BorderImage(&RowBrush).Padding(4,0).ToolTipText(FText::FromString(Hint))[Cells({R.Label,R.Current,R.Final,R.Delta},13,Color,false)]];
        }
    }
}
