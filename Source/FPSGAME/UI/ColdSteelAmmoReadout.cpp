#include "ColdSteelAmmoReadout.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/SizeBox.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UColdSteelAmmoReadout::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(false);SetVisibility(ESlateVisibility::HitTestInvisible);
    bPreview=FParse::Param(FCommandLine::Get(),TEXT("AmmoReadoutAudit"));
    LayoutBox=WidgetTree->ConstructWidget<USizeBox>();WidgetTree->RootWidget=LayoutBox;
    Surface=WidgetTree->ConstructWidget<UBorder>();LayoutBox->SetContent(Surface);
    Surface->SetHorizontalAlignment(HAlign_Fill);Surface->SetVerticalAlignment(VAlign_Fill);
    auto* Content=WidgetTree->ConstructWidget<UVerticalBox>();Surface->SetContent(Content);
    BuildWeaponSection(Content,false);
    HandSeparator=WidgetTree->ConstructWidget<USizeBox>();
    auto* Rule=WidgetTree->ConstructWidget<UBorder>();Rule->SetPadding(FMargin(0));
    Rule->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Border,0,FLinearColor::Transparent,0));
    HandSeparator->SetContent(Rule);Content->AddChildToVerticalBox(HandSeparator);
    BuildWeaponSection(Content,true);
    SetDualVisible(false);
    UpdateLayout(PreferredWidth,20.f);
    Present(TEXT("未装备武器"),TEXT(""),0,0,0,false,false);
}

void UColdSteelAmmoReadout::BuildWeaponSection(UVerticalBox* Parent,bool bOffhand)
{
    const float S=ColdSteelUI::PixelScale(this);
    auto Text=[&](float Pixels,bool Numeric=false,bool Bold=false){auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetFont(Numeric?ColdSteelUI::NumberFont(Pixels*.75f/S,Bold):ColdSteelUI::TextFont(Pixels*.75f/S,Bold));T->SetColorAndOpacity(ColdSteelUI::TextSecondary);return T;};
    auto& Name=bOffhand?OffhandName:Weapon;
    auto& Detail=bOffhand?OffhandCalibre:Calibre;
    auto& Rounds=bOffhand?OffhandAmmo:Current;
    auto& Reserve=bOffhand?OffhandSpare:Spare;
    auto& RoundLabel=bOffhand?OffhandMagazineLabel:MagazineLabel;
    auto& SpareLabel=bOffhand?OffhandReserveLabel:ReserveLabel;
    auto& Divider=bOffhand?OffhandSeparator:Separator;
    auto& Values=bOffhand?OffhandNumbers:Numbers;
    auto* Content=WidgetTree->ConstructWidget<UVerticalBox>();Parent->AddChildToVerticalBox(Content);
    if(bOffhand)OffhandSection=Content;
    Name=Text(16,false,true);Name->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Name->SetAutoWrapText(false);Content->AddChildToVerticalBox(Name);
    Detail=Text(12);Detail->SetAutoWrapText(false);Content->AddChildToVerticalBox(Detail);
    Divider=WidgetTree->ConstructWidget<USizeBox>();
    auto* Rule=WidgetTree->ConstructWidget<UBorder>();Rule->SetPadding(FMargin(0));
    Rule->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Border,0,FLinearColor::Transparent,0));
    Divider->SetContent(Rule);Content->AddChildToVerticalBox(Divider);
    Values=WidgetTree->ConstructWidget<UHorizontalBox>();Content->AddChildToVerticalBox(Values);
    auto* MagazineColumn=WidgetTree->ConstructWidget<UVerticalBox>();
    auto* MagazineSlot=Values->AddChildToHorizontalBox(MagazineColumn);MagazineSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    RoundLabel=Text(12);RoundLabel->SetText(FText::FromString(TEXT("弹匣")));MagazineColumn->AddChildToVerticalBox(RoundLabel);
    Rounds=Text(24,true,true);Rounds->SetAutoWrapText(false);MagazineColumn->AddChildToVerticalBox(Rounds);
    auto* ReserveColumn=WidgetTree->ConstructWidget<UVerticalBox>();
    Values->AddChildToHorizontalBox(ReserveColumn)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
    SpareLabel=Text(12);SpareLabel->SetText(FText::FromString(TEXT("备弹")));SpareLabel->SetJustification(ETextJustify::Right);ReserveColumn->AddChildToVerticalBox(SpareLabel);
    Reserve=Text(24,true);Reserve->SetAutoWrapText(false);Reserve->SetJustification(ETextJustify::Right);ReserveColumn->AddChildToVerticalBox(Reserve);
}

void UColdSteelAmmoReadout::SetDualVisible(bool Visible)
{
    const auto SectionVisibility=Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
    OffhandSection->SetVisibility(SectionVisibility);HandSeparator->SetVisibility(SectionVisibility);
}

void UColdSteelAmmoReadout::UpdateLayout(float WidthPixels,float BottomPixels)
{
    const float S=ColdSteelUI::PixelScale(this);
    if(auto* CanvasSlot=Cast<UCanvasPanelSlot>(Slot))
    {
        CanvasSlot->SetAutoSize(true);
        CanvasSlot->SetPosition(FVector2D(-20/S,-BottomPixels/S));
    }
    if(!LayoutBox||(FMath::IsNearlyEqual(LayoutWidth,WidthPixels)&&FMath::IsNearlyEqual(LayoutScale,S)))return;
    LayoutWidth=WidthPixels;LayoutScale=S;
    LayoutBox->SetWidthOverride(WidthPixels/S);LayoutBox->SetMinDesiredHeight(124/S);
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,8/S,ColdSteelUI::Border,1/S));
    Surface->SetPadding(FMargin(14/S,12/S));
    UTextBlock* Names[]={Weapon,OffhandName};UTextBlock* Details[]={Calibre,OffhandCalibre};
    UTextBlock* Rounds[]={Current,OffhandAmmo};UTextBlock* Reserves[]={Spare,OffhandSpare};
    UTextBlock* RoundLabels[]={MagazineLabel,OffhandMagazineLabel};UTextBlock* SpareLabels[]={ReserveLabel,OffhandReserveLabel};
    USizeBox* Dividers[]={Separator,OffhandSeparator};UHorizontalBox* ValueRows[]={Numbers,OffhandNumbers};
    for(int32 Index=0;Index<2;++Index)
    {
        Names[Index]->SetFont(ColdSteelUI::TextFont(16*.75f/S,true));Names[Index]->SetWrapTextAt(FMath::Max(1.f,WidthPixels-28)/S);
        Details[Index]->SetFont(ColdSteelUI::TextFont(12*.75f/S));Details[Index]->SetWrapTextAt(FMath::Max(1.f,WidthPixels-28)/S);
        Cast<UVerticalBoxSlot>(Details[Index]->Slot)->SetPadding(FMargin(0,4/S,0,0));
        Dividers[Index]->SetHeightOverride(1/S);Cast<UVerticalBoxSlot>(Dividers[Index]->Slot)->SetPadding(FMargin(0,8/S,0,8/S));
        RoundLabels[Index]->SetFont(ColdSteelUI::TextFont(12*.75f/S));SpareLabels[Index]->SetFont(ColdSteelUI::TextFont(12*.75f/S));
        Rounds[Index]->SetFont(ColdSteelUI::NumberFont(24*.75f/S,true));
        Reserves[Index]->SetFont(Index==0&&bReserveStatusText?ColdSteelUI::TextFont(16*.75f/S):ColdSteelUI::NumberFont(24*.75f/S));
        Cast<UVerticalBoxSlot>(Rounds[Index]->Slot)->SetPadding(FMargin(0,2/S,0,0));
        Cast<UVerticalBoxSlot>(Reserves[Index]->Slot)->SetPadding(FMargin(0,2/S,0,0));
        Cast<UHorizontalBoxSlot>(ValueRows[Index]->GetChildAt(0)->Slot)->SetPadding(FMargin(0,0,8/S,0));
        Cast<UHorizontalBoxSlot>(ValueRows[Index]->GetChildAt(1)->Slot)->SetPadding(FMargin(8/S,0,0,0));
    }
    HandSeparator->SetHeightOverride(1/S);Cast<UVerticalBoxSlot>(HandSeparator->Slot)->SetPadding(FMargin(0,10/S,0,10/S));
}

void UColdSteelAmmoReadout::Present(const FString& Name,const FString& Ammo,int32 Magazine,int32 Reserve,int32 Capacity,bool Reloading,bool Equipped)
{
    SetReserveStatusText(false);ReserveLabel->SetText(FText::FromString(TEXT("备弹")));
    const int32 M=FMath::Max(0,Magazine),R=FMath::Max(0,Reserve),C=FMath::Max(1,Capacity);
    const bool Low=M>0&&M<=FMath::Max(1,FMath::CeilToInt(C*.2f));
    const FLinearColor Color=!Equipped?ColdSteelUI::TextTertiary:Reloading?ColdSteelUI::Accent:M==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary;
    Weapon->SetText(FText::FromString(Equipped?Name:TEXT("未装备武器")));Calibre->SetText(FText::FromString(Equipped?Ammo:TEXT("")));
    // Never abbreviate reserves: displayed values remain exact, including large stacks.
    Current->SetText(FText::FromString(Equipped?FString::Printf(TEXT("%02d"),M):TEXT("--")));Current->SetColorAndOpacity(Color);
    Spare->SetText(FText::FromString(Equipped?FString::FromInt(R):TEXT("--")));Spare->SetColorAndOpacity(Equipped&&R==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

void UColdSteelAmmoReadout::SetReserveStatusText(bool Enabled)
{
    if(bReserveStatusText==Enabled)return;
    bReserveStatusText=Enabled;
    const float S=ColdSteelUI::PixelScale(this);
    Spare->SetFont(Enabled?ColdSteelUI::TextFont(16*.75f/S):ColdSteelUI::NumberFont(24*.75f/S));
}

void UColdSteelAmmoReadout::PresentDual(const UPistolDualWieldComponent& Dual,const UColdSteelStatusModel& Model,bool InfiniteReserve)
{
    SetReserveStatusText(false);
    UTextBlock* Names[]={Weapon,OffhandName};UTextBlock* Details[]={Calibre,OffhandCalibre};
    UTextBlock* Rounds[]={Current,OffhandAmmo};UTextBlock* Reserves[]={Spare,OffhandSpare};
    UTextBlock* RoundLabels[]={MagazineLabel,OffhandMagazineLabel};UTextBlock* SpareLabels[]={ReserveLabel,OffhandReserveLabel};
    for(int32 Index=0;Index<2;++Index)
    {
        const auto& Hand=Dual.Hand(Index);
        const bool Unlimited=Dual.InfiniteReserve(Index);
        const int32 Count=FMath::Max(0,Hand.Rounds),Capacity=FMath::Max(1,Hand.Stats.Capacity),Reserve=FMath::Max(0,Dual.Reserve(Index));
        const bool Low=Count>0&&Count<=FMath::Max(1,FMath::CeilToInt(Capacity*.2f));
        Names[Index]->SetText(FText::FromString(FString(Index==0?TEXT("主手 · "):TEXT("副手 · "))+ColdSteelInventory::Text(Hand.Item,TEXT("name"))));
        FString Detail=FString(Index==0?TEXT("左键 · "):TEXT("右键 · "))+Model.AmmoLabel(Model.AmmoDefinitionFor(Hand.Item));
        if(!Hand.PendingAmmoType.IsEmpty())if(const auto* Target=Model.AmmoType(Hand.PendingAmmoType))Detail+=TEXT(" → ")+Target->Name;
        if(Hand.Reloading)Detail+=TEXT(" · 换弹中");
        Details[Index]->SetText(FText::FromString(Detail));
        RoundLabels[Index]->SetText(FText::FromString(TEXT("弹匣")));SpareLabels[Index]->SetText(FText::FromString(TEXT("备弹")));
        Rounds[Index]->SetText(FText::FromString(FString::Printf(TEXT("%02d / %d"),Count,Capacity)));
        Rounds[Index]->SetColorAndOpacity(Hand.Reloading?ColdSteelUI::Accent:Count==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
        Reserves[Index]->SetText(FText::FromString(Unlimited?TEXT("∞"):FString::Printf(TEXT("%lld"),Model.PouchCount(Model.AmmoDefinitionFor(Hand.Item)))));
        Reserves[Index]->SetColorAndOpacity(!Unlimited&&Reserve==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    }
}

void UColdSteelAmmoReadout::PresentMelee(const FColdSteelItem& Item,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character)
{
    const auto Readout=Model.MeleeStaminaReadout(Character);
    auto Set=[](UTextBlock* Block,const FString& Value){if(Block->GetText().ToString()!=Value)Block->SetText(FText::FromString(Value));};
    Set(Weapon,ColdSteelInventory::Text(Item,TEXT("name")));Set(Calibre,TEXT("双手近战 · 左键挥砍"));
    Set(MagazineLabel,TEXT("可普通攻击次数"));Set(ReserveLabel,TEXT("体力回满时间"));
    Set(Current,Readout.bUnlimitedAttacks?TEXT("∞"):FString::FromInt(Readout.AvailableAttacks));
    Current->SetColorAndOpacity(Readout.bUnlimitedAttacks?ColdSteelUI::TextPrimary:Readout.AvailableAttacks==0?ColdSteelUI::Danger:Readout.AvailableAttacks==1?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    SetReserveStatusText(Readout.bRecoveryPaused||Readout.bRecoveryDisabled);
    if(Readout.bRecoveryDisabled)Set(Spare,TEXT("不恢复"));
    else if(Readout.bRecoveryPaused)Set(Spare,TEXT("暂停恢复"));
    else Set(Spare,FString::Printf(TEXT("%.1f s"),FMath::CeilToDouble(double(Readout.FullRecoverySeconds)*10.)/10.));
    Spare->SetColorAndOpacity(Readout.bRecoveryDisabled?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    SetDualVisible(false);
}

void UColdSteelAmmoReadout::Refresh(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model,bool MenuOpen)
{
    if(!Current)return;SetVisibility(MenuOpen?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    const auto* Item=Model?Model->Equipped():nullptr;
    if(Item&&Model&&!Model->ActiveProductionTool()&&Item->Definition==TEXT("ue_rune_sword"))
    {
        PresentMelee(*Item,*Model,Character);return;
    }
    const auto* Dual=Character?Character->DualPistols.Get():nullptr;
    const bool Akimbo=Dual&&Dual->IsActive()&&Model;
    SetDualVisible(Akimbo);
    if(Akimbo)PresentDual(*Dual,*Model,Character->HasInfiniteReserveAmmo());
    else
    {
        FString AmmoName=Model?Model->AmmoLabel(Model->AmmoDefinition()):FString();
        if(Character&&Model&&!Character->GetPendingAmmoType().IsEmpty())if(const auto* Target=Model->AmmoType(Character->GetPendingAmmoType()))AmmoName+=TEXT(" → ")+Target->Name+TEXT(" · 换弹中");
        Present(Item?ColdSteelInventory::Text(*Item,TEXT("name")):TEXT(""),AmmoName,Character?Character->GetMagazineAmmo():0,Character?Character->GetReserveAmmo():0,Character?Character->GetMagazineCapacity():0,Character&&Character->IsReloading(),Character&&Character->HasInventoryWeapon()&&Item);
        MagazineLabel->SetText(FText::FromString(TEXT("弹匣")));
        if(Character&&Item&&Character->HasInventoryWeapon()&&Character->HasInfiniteReserveAmmo())
        {Spare->SetText(FText::FromString(TEXT("∞")));Spare->SetColorAndOpacity(ColdSteelUI::TextSecondary);}
        else if(Character&&Item&&Model&&Character->HasInventoryWeapon())
        {Spare->SetText(FText::FromString(FString::Printf(TEXT("%lld"),Model->PouchCount(Model->AmmoDefinitionFor(*Item)))));}
    }
    if(bPreview&&Model&&Model->IsAudit())Preview(Character,Model);
}
