#include "M4GunsmithWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace {
TSharedRef<STextBlock> Text(const FString& S,int32 Size,FLinearColor Color,bool Number=false)
{return SNew(STextBlock).Text(FText::FromString(S)).Font(Number?GunsmithUI::NumberFont(Size):GunsmithUI::TextFont(Size)).ColorAndOpacity(Color).AutoWrapText(true).Justification(Number?ETextJustify::Right:ETextJustify::Left);}
FString Value(double N,int32 Digits,const TCHAR* Unit){return FString::Printf(TEXT("%.*f%s"),Digits,N,Unit);}
FLinearColor BenefitColor(int32 Benefit){return Benefit>0?ColdSteelUI::Success:Benefit<0?ColdSteelUI::Danger:GunsmithUI::Secondary;}
}
void UM4GunsmithWidget::RefreshPresentation()
{
    PreviewMotion=1.f;
    auto* G=Model();auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* I=P->FindItem(G->Instance());if(!I||!G->ModifiableWeapon(G->Definition()))return;
    if(!IsCategoryAvailable(SelectedCategory))
    {
        SelectedCategory.Reset();
        for(const auto& Key:G->Slots(G->Definition()))if(IsCategoryAvailable(Key)){SelectedCategory=Key;break;}
    }
    const auto S=G->Calculate(G->Definition(),G->Draft());
    const auto B=G->Calculate(G->Definition(),bCompareFactory?FGunsmithParts():G->Installed(*I));
    Overview.Reset();
    auto Row=[this](const TCHAR* Name,double Before,double After,int32 Digits,const TCHAR* Unit,bool Lower=false)
    {
        const double D=After-Before;FGunsmithOverviewRow R;R.Label=Name;R.Current=Value(Before,Digits,Unit);R.Final=Value(After,Digits,Unit);
        R.Delta=FMath::Abs(D)<.00001?TEXT("—"):FString(D>0?TEXT("+"):TEXT(""))+Value(D,Digits,Unit);
        R.Benefit=FMath::Abs(D)<.00001?0:((D>0)!=Lower?1:-1);Overview.Add(R);
    };
    if(IsMeleeWorkbench())AppendMeleeOverview(*I);
    else
    {
    Row(TEXT("开镜耗时"),B.ADS*1000,S.ADS*1000,0,TEXT(" ms"),true);
    Row(TEXT("弹匣容量"),B.Capacity,S.Capacity,0,TEXT(" 发"));
    // Reload rows go through the shared stack (敏捷 × 快手 × 附魔 × 配件) so the
    // panel shows the time the player actually spends.
    Row(TEXT("普通换弹"),ColdSteelWeaponStats::Reload(I,P,B.Reload),ColdSteelWeaponStats::Reload(I,P,S.Reload),2,TEXT(" s"),true);
    Row(TEXT("空仓换弹"),ColdSteelWeaponStats::Reload(I,P,B.EmptyReload),ColdSteelWeaponStats::Reload(I,P,S.EmptyReload),2,TEXT(" s"),true);
    // Shared item modifiers affect both the shot clock and the burst clock.
    const double BeforeInterval=ColdSteelWeaponStats::Interval(I,P,B.Interval);
    const double AfterInterval=ColdSteelWeaponStats::Interval(I,P,S.Interval);
    Row(S.BurstCount>1?TEXT("组内射击间隔"):TEXT("射击间隔"),BeforeInterval*1000,AfterInterval*1000,0,TEXT(" ms"),true);
    Row(S.BurstCount>1?TEXT("组内理论射速"):TEXT("射速"),60/BeforeInterval,60/AfterInterval,0,TEXT(" /min"));
    if(S.BurstCount>1)
    {
        Overview.Add({TEXT("开火模式"),TEXT("三连发"),TEXT("三连发"),TEXT("—"),0});
        const double BeforeDelay=ColdSteelWeaponStats::Interval(I,P,B.BurstDelay);
        const double AfterDelay=ColdSteelWeaponStats::Interval(I,P,S.BurstDelay);
        Row(TEXT("连发组末发后间隔"),BeforeDelay*1000,AfterDelay*1000,0,TEXT(" ms"),true);
        Row(TEXT("含组间隔理论射速"),60*B.BurstCount/((B.BurstCount-1)*BeforeInterval+FMath::Max(BeforeInterval,BeforeDelay)),60*S.BurstCount/((S.BurstCount-1)*AfterInterval+FMath::Max(AfterInterval,AfterDelay)),0,TEXT(" /min"));
    }
    auto* Enhancement=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    Row(TEXT("基础命中伤害"),Enhancement->ProcessedDamage(*I,B.Damage,P->Derived(TEXT("atk"))),Enhancement->ProcessedDamage(*I,S.Damage,P->Derived(TEXT("atk"))),1,TEXT(""));
    Row(TEXT("后坐力 ↓"),B.Recoil,S.Recoil,1,TEXT(""),true);
    Row(TEXT("枪械稳定性 ↑"),B.Handling.Stability,S.Handling.Stability,1,TEXT(" 分"));
    Row(TEXT("首发上跳"),B.Handling.FirstShotDegrees(),S.Handling.FirstShotDegrees(),3,TEXT("°"),true);
    Row(TEXT("连射上跳/发"),B.Handling.MaxVerticalDegrees(),S.Handling.MaxVerticalDegrees(),3,TEXT("°"),true);
    Row(TEXT("ADS首发水平/发"),B.Handling.FirstHorizontalDegrees(),S.Handling.FirstHorizontalDegrees(),3,TEXT("°"),true);
    Row(TEXT("ADS水平上限/发"),B.Handling.MaxHorizontalDegrees(),S.Handling.MaxHorizontalDegrees(),3,TEXT("°"),true);
    Row(TEXT("枪械稳定性·抖动指数 ↓"),B.Shake,S.Shake,1,TEXT(""),true);
    Row(TEXT("枪械稳定性·回稳90%"),B.Handling.ADSRecoveryMilliseconds(),S.Handling.ADSRecoveryMilliseconds(),0,TEXT(" ms"),true);
    Row(TEXT("腰射散布系数"),B.Spread,S.Spread,2,TEXT("×"),true);
    Row(TEXT("有效射程（全伤害）"),B.Range,S.Range,0,TEXT(" m"));
    if(S.Speed<=0)Overview.Add({TEXT("子弹速度"),TEXT("即时命中"),TEXT("即时命中"),TEXT("—"),0});
    else Row(TEXT("子弹速度"),B.Speed,S.Speed,0,TEXT(" m/s"));
    const auto BeforeParts=bCompareFactory?FGunsmithParts():G->Installed(*I);
    auto MagnificationLabel=[&](const FGunsmithParts& Parts)->FString
    {
        const FString Optic=Parts.FindRef(TEXT("optic"));
        if(Optic==TEXT("pso1_4x")||(G->Definition()==TEXT("ue_svd")&&(Optic.IsEmpty()||Optic==TEXT("false"))))return TEXT("4×");
        if(Optic==TEXT("lpvo_1_6x"))return TEXT("1–6×");
        return Optic==TEXT("prism_scope_2x")?TEXT("2×"):TEXT("1×");
    };
    Overview.Add({TEXT("瞄具倍率"),MagnificationLabel(BeforeParts),MagnificationLabel(G->Draft()),TEXT("—"),0});
    if(G->Definition()==TEXT("ue_m16a2"))Overview.Add({TEXT("机械瞄具"),TEXT("固定提把"),TEXT("固定提把"),TEXT("—"),0});
    else if(G->Definition()==TEXT("ue_akm")||G->Definition()==TEXT("ue_pkm_lowpoly")||G->Definition()==TEXT("ue_svd"))Overview.Add({TEXT("机械瞄具"),TEXT("固定机瞄"),TEXT("固定机瞄"),TEXT("—"),0});
    else Overview.Add({TEXT("机械瞄具"),BeforeParts.Contains(TEXT("optic"))?TEXT("折下"):TEXT("竖起"),G->Draft().Contains(TEXT("optic"))?TEXT("折下"):TEXT("竖起"),TEXT("—"),0});
    }
    StatusText=G->Pending()>0?FString::Printf(TEXT("待应用 · %d 项    %s"),G->Pending(),*G->Message()):TEXT("当前配置    ")+G->Message();
    if(OptionScroll)
    {
        const auto* Options=G->ModifiableWeapon(G->Definition())->Options.Find(SelectedCategory);
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
    RefreshSelectedOption();
    if(OverviewList)
    {
        OverviewList->ClearChildren();
        auto Cells=[](const TArray<FString>& Values,int32 FontSize,FLinearColor FinalColor,bool Heading)
        {
            auto H=SNew(SHorizontalBox);const float Widths[]={1.55f,.94f,.94f,.83f};
            for(int32 J=0;J<4;++J)H->AddSlot().FillWidth(Widths[J]).VAlign(VAlign_Center).Padding(4,3)
                [Text(Values[J],FontSize,J>=2?FinalColor:GunsmithUI::Secondary,!Heading&&J>0)];
            return H;
        };
        for(const auto& R:Overview)
        {
            const auto Color=BenefitColor(R.Benefit);
            FString Hint;
            if(R.Label.Contains(TEXT("回稳")))Hint=TEXT("枪械稳定性的回稳分项：开镜反馈弹簧包络衰减90%的理论时间，越短越好。最短约50ms；满分时仍保留枪体后坐回弹，不会自动把瞄准点拉回原位。");
            else if(R.Label.Contains(TEXT("抖动指数")))Hint=TEXT("枪械稳定性的幅度分项，越低越好。统一参考指数100；抖动幅度降低百分比不等于枪械稳定性评分提高百分比。");
            else if(R.Label.Contains(TEXT("稳定性")))Hint=TEXT("枪械稳定性为0–100分，越高越好。配件百分比作用于评分并相乘叠加，再决定开火抖动和回稳；参考枪械为50分。不代表命中率，不控制呼吸、移动摆动或瞄准点自动回正。");
            else if(R.Label.Contains(TEXT("上跳")))Hint=TEXT("控制瞄准方向的逐发垂直后坐角度。首发为完全恢复后的第一枪；连射值为第9发起的单发上限，不包含随机晃动。");
            else if(R.Label.Contains(TEXT("水平")))Hint=TEXT("ADS逐发水平后坐角度的绝对值，越低越好。首发向右，连射按固定左右节奏循环；上限是单发最大偏转，不是随机散布或累计偏移。配件后坐力倍率同时缩放垂直和水平角度。");
            else if(R.Label.Contains(TEXT("后坐力")))Hint=TEXT("后坐力指数，越低越好。统一参考值100；配件倍率相乘，实际射击与面板使用相同结果。");
            OverviewList->AddSlot().AutoHeight().Padding(0,0,0,1)[SNew(SBorder).BorderImage(&RowBrush).Padding(0).ToolTipText(FText::FromString(Hint))[Cells({R.Label,R.Current,R.Final,R.Delta},14,Color,false)]];
        }
    }
}
