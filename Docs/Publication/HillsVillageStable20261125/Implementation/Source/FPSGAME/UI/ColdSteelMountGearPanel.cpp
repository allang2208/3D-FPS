#include "ColdSteelMountGearPanel.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHorsePortrait.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "../Movement/StableHorseGear.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Images/SImage.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "GameFramework/Pawn.h"

void UColdSteelMountGearPanel::ReleaseSlateResources(bool ReleaseChildren)
{
    Super::ReleaseSlateResources(ReleaseChildren);
    Buttons.Reset();Captions.Reset();GearImages.Reset();Values.Reset();GrowthValues.Reset();EmptyMarks.Reset();Performance.Reset();
    Portrait.Reset();NameText.Reset();LevelText.Reset();CoatText.Reset();HairText.Reset();StateText.Reset();CountText.Reset();
    ExperienceText.Reset();ExperienceBar.Reset();HealthBar.Reset();HealthText.Reset();StaminaBar.Reset();StaminaText.Reset();
    LastXP=-1;LastLevel=INDEX_NONE;LastState.Reset();LastVitals=FVector4(-1,-1,-1,-1);
}
void UColdSteelMountGearPanel::ShowHorse(UColdSteelStatusModel* InModel,const FStableMountRecord& Horse,bool bCanEquip,const FString& DisplayName)
{
    if(HorseId!=Horse.HorseId)ClearHorse();
    Model=InModel;HorseId=Horse.HorseId;Editable=bCanEquip;
    if(Buttons.IsEmpty())TakeWidget();
    if(Textures.IsEmpty())
    {
        for(int32 I=0;I<StableHorseGear::Count;++I)
            Textures.Add(FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData/Icons/HorseTack")/(FString(StableHorseGear::Definitions[I])+TEXT(".png"))));
    }
    if(!PortraitAtlas)PortraitAtlas=ColdSteelHorsePortrait::LoadAtlas();
    const auto Look=FStableHorseAppearance::FromId(HorseId);
    ColdSteelHorsePortrait::SetImage(PortraitBrush,PortraitAtlas,Look);
    Portrait->SetImage(&PortraitBrush);Portrait->Invalidate(EInvalidateWidgetReason::Paint);
    NameText->SetText(FText::FromString(Horse.DisplayName()));NameText->SetToolTipText(FText::FromString(DisplayName));
    const FString Identifier=DisplayName==Horse.DisplayName()?FString():TEXT(" · ")+Horse.HorseId.ToString(EGuidFormats::Digits).Left(8);
    CoatText->SetText(FText::FromString(Look.CoatDescription()+Identifier));HairText->SetText(FText::FromString(Look.HairDescription()));
    CountText->SetText(FText::FromString(FString::Printf(TEXT("%d / %d"),Horse.Equipment.Num(),StableHorseGear::Count)));
    const auto T=Horse.Traits(), G=FStableHorseTraits::Growth(HorseId);
    const float Ratings[]={T.Strength,T.Agility,T.Intelligence,T.Constitution,T.Spirit,T.Luck};
    const float Gains[]={G.Strength,G.Agility,G.Intelligence,G.Constitution,G.Spirit,G.Luck};
    for(int32 I=0;I<Values.Num();++I)
    {
        Values[I]->SetText(FText::FromString(FString::SanitizeFloat(Ratings[I],0)));
        GrowthValues[I]->SetText(FText::FromString(FString::Printf(TEXT("+%.1f"),Gains[I])));
    }
    const FString Data[]={
        FString::Printf(TEXT("%.1f"),T.CanterSpeed()/100.f),
        FString::Printf(TEXT("%.2f"),T.JumpRise()/100.f),
        FString::Printf(TEXT("%.0f"),88.f*T.TurnScale()),
        FString::Printf(TEXT("%.0f"),100.f*T.RecoveryScale()),
        FString::Printf(TEXT("%.1f"),T.HealthLimit()*.025f*T.HealingScale())};
    for(int32 I=0;I<Performance.Num();++I)Performance[I]->SetText(FText::FromString(Data[I]));
    for(int32 I=0;I<Buttons.Num();++I)
    {
        const auto* Item=StableHorseGear::At(Horse,I);
        const FString Name=Item?ColdSteelInventory::Text(*Item,TEXT("name")):TEXT("未装备");
        Captions[I]->SetText(FText::FromString(Name));
        Captions[I]->SetColorAndOpacity(Item?ColdSteelUI::TextPrimary:ColdSteelUI::TextTertiary);
        Brushes[I].SetResourceObject(Textures[I]);Brushes[I].DrawAs=ESlateBrushDrawType::Image;
        Brushes[I].SetImageSize(FVector2D(256,256));
        GearImages[I]->SetImage(&Brushes[I]);
        GearImages[I]->SetVisibility(Item?EVisibility::HitTestInvisible:EVisibility::Collapsed);
        EmptyMarks[I]->SetText(FText::FromString(Editable?TEXT("+"):TEXT("—")));
        EmptyMarks[I]->SetVisibility(Item?EVisibility::Collapsed:EVisibility::HitTestInvisible);
        FLinearColor Fill=ColdSteelUI::Gray(18,90),Stroke=ColdSteelUI::Gray(220,28);
        if(Item)
        {
            Fill=ColdSteelUI::RarityColor(ColdSteelInventory::Text(*Item,TEXT("rarity")));
            Stroke=Fill;Fill.A=.42f;Stroke.A=.62f;
        }
        CellBrushes[I]=ColdSteelUI::RoundedBrush(Fill,ColdSteelUI::InventoryItemRadius,Stroke,1);
        const FString Hint=FString(StableHorseGear::Labels[I])+TEXT(" · ")+Name;
        Buttons[I]->SetToolTipText(FText::FromString(Hint));
        Buttons[I]->SetVisibility(Editable?EVisibility::Visible:EVisibility::HitTestInvisible);
        Buttons[I]->Invalidate(EInvalidateWidgetReason::Paint);
    }
}
void UColdSteelMountGearPanel::UpdateCondition(const FStableMountRecord& Horse,const FString& State,float Health,float Stamina)
{
    if(!StateText || HorseId!=Horse.HorseId)return;
    if(LastState!=State){LastState=State;StateText->SetText(FText::FromString(State));}
    if(LastLevel!=Horse.Level || LastXP!=Horse.Experience)
    {
        LastLevel=Horse.Level;LastXP=Horse.Experience;
        LevelText->SetText(FText::FromString(FString::Printf(TEXT("%d 级"),Horse.Level)));
        const int64 Required=Horse.ExperienceNeeded(Horse.Level);
        const bool Max=Horse.Level>=FStableHorseTraits::MaxLevel;
        ExperienceText->SetFont(Max?ColdSteelUI::TextFont(11,true):ColdSteelUI::NumberFont(11));
        ExperienceText->SetText(FText::FromString(Max?TEXT("已满级"):FString::Printf(TEXT("%lld / %lld"),Horse.Experience,Required)));
        ExperienceBar->SetPercent(Max?1.f:FMath::Clamp(float(Horse.Experience)/float(Required),0.f,1.f));
    }
    const FVector4 Snapshot(Health,Horse.MaxHealth,Stamina,Horse.MaxStamina);
    if(LastVitals==Snapshot)return;
    LastVitals=Snapshot;
    HealthText->SetText(FText::FromString(FString::Printf(TEXT("%.0f / %.0f"),Health,Horse.MaxHealth)));
    StaminaText->SetText(FText::FromString(FString::Printf(TEXT("%.0f / %.0f"),Stamina,Horse.MaxStamina)));
    HealthBar->SetPercent(FMath::Clamp(Health/FMath::Max(1.f,Horse.MaxHealth),0.f,1.f));
    StaminaBar->SetPercent(FMath::Clamp(Stamina/FMath::Max(1.f,Horse.MaxStamina),0.f,1.f));
}
void UColdSteelMountGearPanel::ClearHorse()
{
    Editable=false;HorseId.Invalidate();DropIndex=INDEX_NONE;bDropAllowed=false;
    LastState.Reset();LastXP=-1;LastLevel=INDEX_NONE;LastVitals=FVector4(-1,-1,-1,-1);
    for(const auto& Button:Buttons)if(Button && Button->IsOpen())Button->SetIsOpen(false);
}
TSharedRef<SWidget> UColdSteelMountGearPanel::Choices(int32 GearIndex)
{
    auto List=SNew(SVerticalBox);
    auto* M=Model.Get();
    const auto* Horse=M?M->ProfileView().MountRoster.Find(HorseId):nullptr;
    if(!Editable || !Horse)return List;
    static const FButtonStyle Style=ColdSteelUI::ButtonStyle();
    const auto Add=[&](const FString& Text,const FString& Item,bool Equip)
    {
        List->AddSlot().AutoHeight()[SNew(SButton).ButtonStyle(&Style).ContentPadding(FMargin(10,5))
          .OnClicked_UObject(this,&ThisClass::Change,HorseId,GearIndex,Item,Equip)
          [SNew(STextBlock).Font(ColdSteelUI::TextFont(12)).Text(FText::FromString(Text))]];
    };
    if(const auto* Old=StableHorseGear::At(*Horse,GearIndex))Add(TEXT("卸下并放回背包"),Old->InstanceId,false);
    for(const auto& Item:M->Items())
        if((Item.Place==0 || Item.Place==ColdSteelInventory::ColdSteelCompartment::Place) && StableHorseGear::SlotOf(Item.Definition)==GearIndex)
            Add(TEXT("装备  ")+ColdSteelInventory::Text(Item,TEXT("name")),Item.InstanceId,true);
    if(!List->NumSlots())List->AddSlot().Padding(8)[SNew(STextBlock).Font(ColdSteelUI::TextFont(12))
        .Text(FText::FromString(TEXT("随身背包没有适用马具")))];
    return SNew(SBox).MinDesiredWidth(160).MaxDesiredHeight(236)
        [SNew(SScrollBox).AllowOverscroll(EAllowOverscroll::No)+SScrollBox::Slot()[List]];
}
FReply UColdSteelMountGearPanel::Change(FGuid Id,int32 GearIndex,FString Item,bool Equip)
{
    FSlateApplication::Get().DismissAllMenus();
    auto* Pawn=GetOwningPlayerPawn();auto* M=Model.Get();
    if(!Editable || Id!=HorseId || !Pawn || !M || !M->ProfileView().MountRoster.Find(Id))return FReply::Handled();
    if(Pawn->GetNetMode()==NM_Standalone)
    {
        M->SyncRuntime();FString Why;M->ChangeMountGear(Id,GearIndex,Item,Equip,Why);M->PostNotice(TEXT("马具"),Why);
    }
    else if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())
    {
        FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::MountGear;
        R.MountId=Id;R.Cell=GearIndex;R.Item=Item;R.Mode=Equip?TEXT("equip"):TEXT("remove");
        if(!PS->RequestInventoryAction(R))M->PostNotice(TEXT("马具"),TEXT("背包正在同步，请稍候再试"));
    }
    return FReply::Handled();
}
bool UColdSteelMountGearPanel::HandleItemDrop(UColdSteelItemDrag* Drag,FVector2D Position)
{
    DropIndex=INDEX_NONE;bDropAllowed=false;
    if(!Drag || !GetCachedGeometry().IsUnderLocation(Position))return false;
    if(Editable && Model.IsValid() && Drag->IsCurrent(Model.Get()))
        for(int32 I=0;I<Buttons.Num();++I)
            if(Buttons[I]->GetCachedGeometry().IsUnderLocation(Position))
            {Change(HorseId,I,Drag->ItemId,true);break;}
    return true;
}
bool UColdSteelMountGearPanel::NativeOnDragOver(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Op)
{
    const auto* Drag=Cast<UColdSteelItemDrag>(Op);
    DropIndex=INDEX_NONE;bDropAllowed=false;
    if(!Drag)return false;
    const FVector2D PointerPosition=E.GetScreenSpacePosition();
    for(int32 I=0;Editable && I<Buttons.Num();++I)
        if(Buttons[I]->GetCachedGeometry().IsUnderLocation(PointerPosition))
        {
            DropIndex=I;
            bDropAllowed=Drag->bHasSourceSnapshot && (Drag->SourcePlace==0 || Drag->SourcePlace==ColdSteelInventory::ColdSteelCompartment::Place)
                && StableHorseGear::SlotOf(Drag->SourceSnapshot.Definition)==I;
            break;
        }
    return true;
}
void UColdSteelMountGearPanel::NativeOnDragLeave(const FDragDropEvent& E,UDragDropOperation* Op)
{
    DropIndex=INDEX_NONE;bDropAllowed=false;Super::NativeOnDragLeave(E,Op);
}
bool UColdSteelMountGearPanel::NativeOnDrop(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Op){return HandleItemDrop(Cast<UColdSteelItemDrag>(Op),E.GetScreenSpacePosition());}
