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

void UColdSteelAmmoReadout::SetTextIfChanged(UTextBlock* Block,const FString& Value)
{
    if(Block&&Block->GetText().ToString()!=Value)Block->SetText(FText::FromString(Value));
}

void UColdSteelAmmoReadout::SetColorIfChanged(UTextBlock* Block,const FLinearColor& Color)
{
    if(!Block)return;
    if(const FLinearColor* Prev=CachedTextColors.Find(Block);Prev&&Prev->Equals(Color,1e-4f))return;
    CachedTextColors.Add(Block,Color);
    Block->SetColorAndOpacity(Color);
}

void UColdSteelAmmoReadout::SetDualVisible(bool Visible)
{
    if(LastDualVisible.IsSet()&&LastDualVisible.GetValue()==Visible)return;
    LastDualVisible=Visible;
    const auto SectionVisibility=Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
    OffhandSection->SetVisibility(SectionVisibility);HandSeparator->SetVisibility(SectionVisibility);
}

void UColdSteelAmmoReadout::UpdateLayout(float WidthPixels,float BottomPixels)
{
    const float S=ColdSteelUI::PixelScale(this);
    if(auto* CanvasSlot=Cast<UCanvasPanelSlot>(Slot))
    {
        if(!bSlotAutoSizeSet){CanvasSlot->SetAutoSize(true);bSlotAutoSizeSet=true;}
        const FVector2D TargetPos(-20.f/S,-BottomPixels/S);
        if(!LastSlotPosition.Equals(TargetPos,0.05f)){CanvasSlot->SetPosition(TargetPos);LastSlotPosition=TargetPos;}
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
    SetReserveStatusText(false);SetTextIfChanged(ReserveLabel,TEXT("备弹"));
    const int32 M=FMath::Max(0,Magazine),R=FMath::Max(0,Reserve),C=FMath::Max(1,Capacity);
    const bool Low=M>0&&M<=FMath::Max(1,FMath::CeilToInt(C*.2f));
    const FLinearColor Color=!Equipped?ColdSteelUI::TextTertiary:Reloading?ColdSteelUI::Accent:M==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary;
    SetTextIfChanged(Weapon,Equipped?Name:TEXT("未装备武器"));SetTextIfChanged(Calibre,Equipped?Ammo:TEXT(""));
    // Never abbreviate reserves: displayed values remain exact, including large stacks.
    SetTextIfChanged(Current,Equipped?FString::Printf(TEXT("%02d"),M):TEXT("--"));SetColorIfChanged(Current,Color);
    SetTextIfChanged(Spare,Equipped?FString::FromInt(R):TEXT("--"));SetColorIfChanged(Spare,Equipped&&R==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
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
        SetTextIfChanged(Names[Index],FString(Index==0?TEXT("主手 · "):TEXT("副手 · "))+ColdSteelInventory::Text(Hand.Item,TEXT("name")));
        FString Detail=FString(Index==0?TEXT("左键 · "):TEXT("右键 · "))+Model.AmmoLabel(Model.AmmoDefinitionFor(Hand.Item));
        if(Hand.SelectableAutomatic)Detail+=TEXT("\n")+FullAutoTrigger::Hint(Hand.Automatic,Index);
        if(!Hand.PendingAmmoType.IsEmpty())if(const auto* Target=Model.AmmoType(Hand.PendingAmmoType))Detail+=TEXT(" → ")+Target->Name;
        if(Hand.Reloading)Detail+=TEXT(" · 换弹中");
        SetTextIfChanged(Details[Index],Detail);
        SetColorIfChanged(Details[Index],ColdSteelUI::TextSecondary);
        SetTextIfChanged(RoundLabels[Index],TEXT("弹匣"));SetTextIfChanged(SpareLabels[Index],TEXT("备弹"));
        SetTextIfChanged(Rounds[Index],FString::Printf(TEXT("%02d / %d"),Count,Capacity));
        SetColorIfChanged(Rounds[Index],Hand.Reloading?ColdSteelUI::Accent:Count==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
        SetTextIfChanged(Reserves[Index],Unlimited?TEXT("∞"):FString::Printf(TEXT("%lld"),Model.PouchCount(Model.AmmoDefinitionFor(Hand.Item))));
        SetColorIfChanged(Reserves[Index],!Unlimited&&Reserve==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
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
    SetTextIfChanged(OffhandName,FString(TEXT("副手 · "))+ColdSteelInventory::Text(Hand.Item,TEXT("name")));
    FString Detail=TEXT("右键 · ")+Model.AmmoLabel(Model.AmmoDefinitionFor(Hand.Item));
    if(Hand.SelectableAutomatic)Detail+=TEXT("\n")+FullAutoTrigger::Hint(Hand.Automatic,1);
    if(!Hand.PendingAmmoType.IsEmpty())if(const auto* Target=Model.AmmoType(Hand.PendingAmmoType))Detail+=TEXT(" → ")+Target->Name;
    if(Hand.Reloading)Detail+=TEXT(" · 换弹中");
    else if(Dual.IsMeleePairBlocked())Detail+=Hand.ReloadQueued?TEXT(" · 避让中，待换弹"):TEXT(" · 避让中");
    SetTextIfChanged(OffhandCalibre,Detail);
    SetColorIfChanged(OffhandCalibre,ColdSteelUI::TextSecondary);
    SetTextIfChanged(OffhandMagazineLabel,TEXT("弹匣"));
    SetTextIfChanged(OffhandReserveLabel,TEXT("备弹"));
    const bool Unlimited=Dual.InfiniteReserve(1);
    const int32 Count=FMath::Max(0,Hand.Rounds),Capacity=FMath::Max(1,Hand.Stats.Capacity),Reserve=FMath::Max(0,Dual.Reserve(1));
    const bool Low=Count>0&&Count<=FMath::Max(1,FMath::CeilToInt(Capacity*.2f));
    SetTextIfChanged(OffhandAmmo,FString::Printf(TEXT("%02d / %d"),Count,Capacity));
    SetColorIfChanged(OffhandAmmo,Hand.Reloading?ColdSteelUI::Accent:Count==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    SetTextIfChanged(OffhandSpare,Unlimited?TEXT("∞"):FString::FromInt(Reserve));
    SetColorIfChanged(OffhandSpare,!Unlimited&&Reserve==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

void UColdSteelAmmoReadout::PresentMelee(const FColdSteelItem& Item,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character)
{
    const auto Readout=Model.MeleeStaminaReadout(Character);
    SetTextIfChanged(Weapon,ColdSteelInventory::Text(Item,TEXT("name")));
    SetTextIfChanged(Calibre,PojunGrip::Installed(Item)?TEXT("破军长柄 · 双手锤式挥击"):ColdSteelInventory::IsTwoHandedBlunt(Item)?TEXT("双手钝器 · 左键挥击"):
        ColdSteelInventory::IsOneHandedMelee(Item)?TEXT("单手近战 · 左键挥砍"):TEXT("双手近战 · 左键挥砍"));
    SetTextIfChanged(MagazineLabel,TEXT("可普通攻击次数"));SetTextIfChanged(ReserveLabel,TEXT("体力回满时间"));
    SetTextIfChanged(Current,Readout.bUnlimitedAttacks?TEXT("∞"):FString::FromInt(Readout.AvailableAttacks));
    SetColorIfChanged(Current,Readout.bUnlimitedAttacks?ColdSteelUI::TextPrimary:Readout.AvailableAttacks==0?ColdSteelUI::Danger:Readout.AvailableAttacks==1?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    SetReserveStatusText(Readout.bRecoveryPaused||Readout.bRecoveryDisabled);
    if(Readout.bRecoveryDisabled)SetTextIfChanged(Spare,TEXT("不恢复"));
    else if(Readout.bRecoveryPaused)SetTextIfChanged(Spare,TEXT("暂停恢复"));
    else SetTextIfChanged(Spare,FString::Printf(TEXT("%.1f s"),FMath::CeilToDouble(double(Readout.FullRecoverySeconds)*10.)/10.));
    SetColorIfChanged(Spare,Readout.bRecoveryDisabled?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    SetDualVisible(false);
}

void UColdSteelAmmoReadout::Refresh(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model,bool MenuOpen)
{
    if(!Current)return;
    const ESlateVisibility RootVis=MenuOpen?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible;
    if(GetVisibility()!=RootVis)SetVisibility(RootVis);
    const auto* Item=Model?Model->ActiveFirearm():nullptr;
    const auto* ActiveTool=Model?Model->ActiveProductionTool():nullptr;
    const bool StaffEquipped=Item&&Model&&!ActiveTool&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff");
    SetStaffVisible(StaffEquipped);
    const auto* Book=StaffEquipped?Model->ActiveSpellbook():nullptr;
    const ESlateVisibility FocusVis=Book?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
    if(FocusEffects&&FocusEffects->GetVisibility()!=FocusVis)FocusEffects->SetVisibility(FocusVis);
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
    if(Character)
    {
        const int32 CompCount=Character->GetComponents().Num();
        if(CachedPawn.Get()!=Character||CachedPawnComponents!=CompCount)
        {
            CachedPawn=Character;
            CachedPawnComponents=CompCount;
            CachedBow=Character->FindComponentByClass<UBowWeaponComponent>();
            CachedTorch=Character->FindComponentByClass<UWoodenTorchComponent>();
        }
    }
    const auto* Bow=Character?CachedBow.Get():nullptr;
    if(Item&&Model&&Bow&&Bow->IsEquipped()&&!ActiveTool&&ColdSteelInventory::IsBow(*Item))
    {
        SetReserveStatusText(false);SetDualVisible(false);
        SetTextIfChanged(Weapon,ColdSteelInventory::Text(*Item,TEXT("name")));
        SetTextIfChanged(Calibre,Model->AmmoLabel(Bow->ArrowDefinition())+(Bow->HasArrowNocked()?TEXT(" · 已搭箭"):TEXT(" · 未搭箭")));
        SetTextIfChanged(MagazineLabel,TEXT("拉距"));SetTextIfChanged(ReserveLabel,TEXT("箭袋"));
        // Do not round a sub-threshold draw up to the 50% firing gate.
        SetTextIfChanged(Current,FString::Printf(TEXT("%d%%"),FMath::FloorToInt(Bow->DrawFraction()*100.f)));
        const bool Infinite=Character->HasInfiniteReserveAmmoFor(Bow->ArrowDefinition());
        SetTextIfChanged(Spare,Infinite?TEXT("∞"):FString::Printf(TEXT("%lld"),Model->PouchCount(Bow->ArrowDefinition())));
        SetColorIfChanged(Current,Bow->IsDrawing()?ColdSteelUI::Accent:ColdSteelUI::TextPrimary);
        SetColorIfChanged(Spare,!Infinite&&Bow->ArrowsInPouch()==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
        return;
    }
    if(Model&&!ActiveTool)
    {
        const auto* LeftOnly=!Item&&Character?CachedTorch.Get():nullptr;
        if((Item&&ColdSteelInventory::IsWoodenTorch(*Item))||(LeftOnly&&LeftOnly->HoldsLeft()))
        {
            SetTextIfChanged(Weapon,TEXT("火把"));SetTextIfChanged(Calibre,TEXT("照明"));
            for(auto* Block:{MagazineLabel.Get(),ReserveLabel.Get(),Current.Get(),Spare.Get()})SetTextIfChanged(Block,FString());
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
        SetTextIfChanged(MagazineLabel,TEXT("弹匣"));
        if(Character&&Item&&Character->HasInventoryWeapon()&&Character->HasInfiniteReserveAmmo())
        {
            SetTextIfChanged(Spare,TEXT("∞"));
            SetColorIfChanged(Spare,ColdSteelUI::TextSecondary);
        }
        else if(Character&&Item&&Model&&Character->HasInventoryWeapon())
        {
            SetTextIfChanged(Spare,FString::Printf(TEXT("%lld"),Model->PouchCount(Model->AmmoDefinitionFor(*Item))));
        }
    }
    if(bPreview&&Model&&Model->IsAudit())Preview(Character,Model);
}
