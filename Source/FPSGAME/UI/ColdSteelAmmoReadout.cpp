#include "ColdSteelAmmoReadout.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/WoodenTorchComponent.h"
#include "../Weapons/PojunGrip.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/FullAutoTrigger.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
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
    if(!bOffhand)BuildStaffDetails(Content);
    else
    {
        FocusEffects=Text(12);FocusEffects->SetAutoWrapText(false);
        Content->AddChildToVerticalBox(FocusEffects);FocusEffects->SetVisibility(ESlateVisibility::Collapsed);
    }
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
    CooldownLabel->SetFont(ColdSteelUI::TextFont(12*.75f/S));
    RecoveryLabel->SetFont(ColdSteelUI::TextFont(12*.75f/S));
    CooldownValue->SetFont(ColdSteelUI::NumberFont(24*.75f/S,true));
    RecoveryValue->SetFont(bRecoveryStatusText?ColdSteelUI::TextFont(16*.75f/S):ColdSteelUI::NumberFont(24*.75f/S));
    Cast<UVerticalBoxSlot>(StaffDetails->Slot)->SetPadding(FMargin(0,10/S,0,0));
    Cast<UVerticalBoxSlot>(CooldownValue->Slot)->SetPadding(FMargin(0,2/S,0,0));
    Cast<UVerticalBoxSlot>(RecoveryValue->Slot)->SetPadding(FMargin(0,2/S,0,0));
    Cast<UHorizontalBoxSlot>(StaffDetails->GetChildAt(0)->Slot)->SetPadding(FMargin(0,0,8/S,0));
    Cast<UHorizontalBoxSlot>(StaffDetails->GetChildAt(1)->Slot)->SetPadding(FMargin(8/S,0,0,0));
    UpdateStaffMagicLayout(S);
    FocusEffects->SetFont(ColdSteelUI::TextFont(12*.75f/S));
    Cast<UVerticalBoxSlot>(FocusEffects->Slot)->SetPadding(FMargin(0,6/S,0,0));
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
        if(Hand.SelectableAutomatic)Detail+=TEXT("\n")+FullAutoTrigger::Hint(Hand.Automatic,Index);
        if(!Hand.PendingAmmoType.IsEmpty())if(const auto* Target=Model.AmmoType(Hand.PendingAmmoType))Detail+=TEXT(" → ")+Target->Name;
        if(Hand.Reloading)Detail+=TEXT(" · 换弹中");
        Details[Index]->SetText(FText::FromString(Detail));
        Details[Index]->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        RoundLabels[Index]->SetText(FText::FromString(TEXT("弹匣")));SpareLabels[Index]->SetText(FText::FromString(TEXT("备弹")));
        Rounds[Index]->SetText(FText::FromString(FString::Printf(TEXT("%02d / %d"),Count,Capacity)));
        Rounds[Index]->SetColorAndOpacity(Hand.Reloading?ColdSteelUI::Accent:Count==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
        Reserves[Index]->SetText(FText::FromString(Unlimited?TEXT("∞"):FString::Printf(TEXT("%lld"),Model.PouchCount(Model.AmmoDefinitionFor(Hand.Item)))));
        Reserves[Index]->SetColorAndOpacity(!Unlimited&&Reserve==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    }
}

void UColdSteelAmmoReadout::PresentStaffPistol(const FColdSteelItem& Staff,const UPistolDualWieldComponent& Dual,const UColdSteelStatusModel& Model)
{
    PresentStaff(Staff,Model,Model.RuntimePawn(),true);SetDualVisible(true);
    PresentOffhandPistol(Dual,Model);
}

void UColdSteelAmmoReadout::PresentOffhandPistol(const UPistolDualWieldComponent& Dual,const UColdSteelStatusModel& Model)
{
    const auto& Hand=Dual.Hand(1);
    OffhandName->SetText(FText::FromString(TEXT("副手 · ")+ColdSteelInventory::Text(Hand.Item,TEXT("name"))));
    FString Detail=TEXT("右键 · ")+Model.AmmoLabel(Model.AmmoDefinitionFor(Hand.Item));
    if(Hand.SelectableAutomatic)Detail+=TEXT("\n")+FullAutoTrigger::Hint(Hand.Automatic,1);
    if(!Hand.PendingAmmoType.IsEmpty())if(const auto* Target=Model.AmmoType(Hand.PendingAmmoType))Detail+=TEXT(" → ")+Target->Name;
    if(Hand.Reloading)Detail+=TEXT(" · 换弹中");
    else if(Dual.IsMeleePairBlocked())Detail+=Hand.ReloadQueued?TEXT(" · 避让中，待换弹"):TEXT(" · 避让中");
    OffhandCalibre->SetText(FText::FromString(Detail));
    OffhandCalibre->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    OffhandMagazineLabel->SetText(FText::FromString(TEXT("弹匣")));
    OffhandReserveLabel->SetText(FText::FromString(TEXT("备弹")));
    const bool Unlimited=Dual.InfiniteReserve(1);
    const int32 Count=FMath::Max(0,Hand.Rounds),Capacity=FMath::Max(1,Hand.Stats.Capacity),Reserve=FMath::Max(0,Dual.Reserve(1));
    const bool Low=Count>0&&Count<=FMath::Max(1,FMath::CeilToInt(Capacity*.2f));
    OffhandAmmo->SetText(FText::FromString(FString::Printf(TEXT("%02d / %d"),Count,Capacity)));
    OffhandAmmo->SetColorAndOpacity(Hand.Reloading?ColdSteelUI::Accent:Count==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    OffhandSpare->SetText(FText::FromString(Unlimited?TEXT("∞"):FString::FromInt(Reserve)));
    OffhandSpare->SetColorAndOpacity(!Unlimited&&Reserve==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

void UColdSteelAmmoReadout::PresentMelee(const FColdSteelItem& Item,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character)
{
    const auto Readout=Model.MeleeStaminaReadout(Character);
    auto Set=[](UTextBlock* Block,const FString& Value){if(Block->GetText().ToString()!=Value)Block->SetText(FText::FromString(Value));};
    Set(Weapon,ColdSteelInventory::Text(Item,TEXT("name")));
    Set(Calibre,PojunGrip::Installed(Item)?TEXT("破军长柄 · 双手锤式挥击"):ColdSteelInventory::IsTwoHandedBlunt(Item)?TEXT("双手钝器 · 左键挥击"):
        ColdSteelInventory::IsOneHandedMelee(Item)?TEXT("单手近战 · 左键挥砍"):TEXT("双手近战 · 左键挥砍"));
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
    const auto* Item=Model?Model->ActiveFirearm():nullptr;
    const auto* ActiveTool=Model?Model->ActiveProductionTool():nullptr;
    const bool StaffEquipped=Item&&Model&&!ActiveTool&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff");
    SetStaffVisible(StaffEquipped);
    const auto* Book=StaffEquipped?Model->ActiveSpellbook():nullptr;
    FocusEffects->SetVisibility(Book?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    if(StaffEquipped)
    {
        const auto* StaffOffhand=Character?Character->DualPistols.Get():nullptr;
        if(StaffOffhand&&StaffOffhand->IsOffhandOnly())PresentStaffPistol(*Item,*StaffOffhand,*Model);
        else
        {
            PresentStaff(*Item,*Model,Character,Book!=nullptr);SetDualVisible(Book!=nullptr);
            if(Book)PresentSpellbook(*Book,*Model,Character);
        }
        return;
    }
    const auto* Bow=Character?Character->FindComponentByClass<UBowWeaponComponent>():nullptr;
    if(Item&&Model&&Bow&&Bow->IsEquipped()&&!ActiveTool&&ColdSteelInventory::IsBow(*Item))
    {
        auto Set=[](UTextBlock* Block,const FString& Value){if(Block->GetText().ToString()!=Value)Block->SetText(FText::FromString(Value));};
        SetReserveStatusText(false);SetDualVisible(false);
        Set(Weapon,ColdSteelInventory::Text(*Item,TEXT("name")));
        Set(Calibre,Model->AmmoLabel(Bow->ArrowDefinition())+(Bow->HasArrowNocked()?TEXT(" · 已搭箭"):TEXT(" · 未搭箭")));
        Set(MagazineLabel,TEXT("拉距"));Set(ReserveLabel,TEXT("箭袋"));
        // Do not round a sub-threshold draw up to the 50% firing gate.
        Set(Current,FString::Printf(TEXT("%d%%"),FMath::FloorToInt(Bow->DrawFraction()*100.f)));
        const bool Infinite=Character->HasInfiniteReserveAmmoFor(Bow->ArrowDefinition());
        Set(Spare,Infinite?TEXT("∞"):FString::Printf(TEXT("%lld"),Model->PouchCount(Bow->ArrowDefinition())));
        Current->SetColorAndOpacity(Bow->IsDrawing()?ColdSteelUI::Accent:ColdSteelUI::TextPrimary);
        Spare->SetColorAndOpacity(!Infinite&&Bow->ArrowsInPouch()==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
        return;
    }
    if(Model&&!ActiveTool)
    {
        const auto* LeftOnly=!Item&&Character?Character->FindComponentByClass<UWoodenTorchComponent>():nullptr;
        if((Item&&ColdSteelInventory::IsWoodenTorch(*Item))||(LeftOnly&&LeftOnly->HoldsLeft()))
        {
            auto Set=[](UTextBlock* Block,const FString& Value){if(Block->GetText().ToString()!=Value)Block->SetText(FText::FromString(Value));};
            Set(Weapon,TEXT("火把"));Set(Calibre,TEXT("照明"));
            for(auto* Block:{MagazineLabel.Get(),ReserveLabel.Get(),Current.Get(),Spare.Get()})Set(Block,FString());
            const auto* Dual=Character?Character->DualPistols.Get():nullptr;
            SetDualVisible(Dual&&Dual->IsMeleePair());
            if(Dual&&Dual->IsMeleePair())PresentOffhandPistol(*Dual,*Model);
            return;
        }
    }
    // Blunt weapons share the tool motion executor but still use melee stamina.
    // A backpack tool override must not expose the stowed main-hand readout.
    if(Item&&Model&&(!ActiveTool||ActiveTool==Item)&&
        (ColdSteelInventory::IsTwoHandedSword(*Item)||ColdSteelInventory::IsTwoHandedBlunt(*Item)||
            ColdSteelInventory::IsOneHandedMelee(*Item)))
    {
        PresentMelee(*Item,*Model,Character);
        if(const auto* Offhand=Character?Character->DualPistols.Get():nullptr;Offhand&&Offhand->IsMeleePair())
        {
            SetDualVisible(true);PresentOffhandPistol(*Offhand,*Model);
        }
        return;
    }
    const auto* Dual=Character?Character->DualPistols.Get():nullptr;
    const bool Akimbo=Dual&&Dual->IsPair()&&Model;
    SetDualVisible(Akimbo);
    if(Akimbo)PresentDual(*Dual,*Model,Character->HasInfiniteReserveAmmo());
    else
    {
        FString AmmoName=Model?Model->AmmoLabel(Model->AmmoDefinition()):FString();
        if(Character)
        {
            const FString BipodHint=Character->GetBipodDeploymentHint();
            const FString FireModeHint=Character->GetFireModeHint();
            if(!FireModeHint.IsEmpty())AmmoName+=TEXT("\n")+FireModeHint;
            if(!BipodHint.IsEmpty())AmmoName+=TEXT("\n")+BipodHint;
        }
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
