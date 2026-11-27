#include "ColdSteelMountGearPanel.h"
#include "ColdSteelTextToolTip.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelUIAudio.h"
#include "ColdSteelHorsePortrait.h"
#include "SHorseMarketPlate.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "../Movement/StableHorseGear.h"
#include "../Movement/StableHorseAffixes.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Images/SImage.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "GameFramework/Pawn.h"

void UColdSteelMountGearPanel::ReleaseSlateResources(bool ReleaseChildren)
{
    Super::ReleaseSlateResources(ReleaseChildren);
    Buttons.Reset();Captions.Reset();GearSubLabels.Reset();GearImages.Reset();GearAccentBars.Reset();GearArtFrames.Reset();
    Values.Reset();GrowthValues.Reset();TraitCards.Reset();TraitBars.Reset();TraitRanks.Reset();
    EmptyMarks.Reset();Performance.Reset();PerformanceDeltas.Reset();
    HeroPlate.Reset();StateBadge.Reset();NameText.Reset();LevelText.Reset();CoatText.Reset();HairText.Reset();
    StateText.Reset();CountText.Reset();TotalRatingText.Reset();
    ExperienceText.Reset();ExperienceBar.Reset();HealthBar.Reset();HealthText.Reset();StaminaBar.Reset();StaminaText.Reset();
    AffixWrap.Reset();AffixCountText.Reset();AffixBrushes.Reset();
    LastXP=-1;LastLevel=INDEX_NONE;LastState.Reset();LastVitals=FVector4(-1,-1,-1,-1);
}

void UColdSteelMountGearPanel::ShowHorse(UColdSteelStatusModel* InModel,const FStableMountRecord& Horse,bool bCanEquip,const FString& DisplayName)
{
    using namespace ColdSteelUI;
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
    if(HeroPlate)
    {
        HeroPlate->SetSelected(true);
        HeroPlate->Invalidate(EInvalidateWidgetReason::Paint);
    }
    NameText->SetText(FText::FromString(Horse.DisplayName()));
    ColdSteelToolTip::Set(*NameText,FText::FromString(DisplayName));
    const FString Identifier=DisplayName==Horse.DisplayName()?FString():TEXT(" · ")+Horse.HorseId.ToString(EGuidFormats::Digits).Left(8);
    CoatText->SetText(FText::FromString(Look.CoatDescription()+Identifier));
    HairText->SetText(FText::FromString(Look.HairDescription()));
    const auto TB=StableHorseGear::Bonuses(Horse);
    CountText->SetText(FText::FromString(TB.bFullSet
        ? FString::Printf(TEXT("已装配 %d / %d · 东门骑兵套已激活"),Horse.Equipment.Num(),StableHorseGear::Count)
        : FString::Printf(TEXT("已装配 %d / %d"),Horse.Equipment.Num(),StableHorseGear::Count)));

    const auto T=Horse.Traits(), G=FStableHorseTraits::EffectiveGrowth(HorseId);
    const auto Affix=StableHorseAffixes::Bonuses(HorseId);
    const auto AffixList=StableHorseAffixes::Roll(HorseId);
    const float Ratings[]={T.Strength,T.Agility,T.Intelligence,T.Constitution,T.Spirit,T.Luck};
    const float Gains[]={G.Strength,G.Agility,G.Intelligence,G.Constitution,G.Spirit,G.Luck};
    const float TotalScore=T.Strength+T.Agility+T.Intelligence+T.Constitution+T.Spirit+T.Luck;
    if(TotalRatingText)
        TotalRatingText->SetText(FText::FromString(FString::Printf(TEXT("综合总评 %.0f"),TotalScore)));

    static const FSlateBrush TraitNormalBrush=RoundedBrush(Gray(255,9),5,Gray(222,24),1);
    static const FSlateBrush TraitHighBrush=RoundedBrush(FLinearColor(HUDGold.R,HUDGold.G,HUDGold.B,.10f),5,
        FLinearColor(HUDGold.R,HUDGold.G,HUDGold.B,.44f),1);
    const float HighThreshold=12.f+FMath::Max(0,Horse.Level-1)*.75f;
    const float ScaleCap=FMath::Max(14.f,14.f+FMath::Max(0,Horse.Level-1)*1.0f);

    for(int32 I=0;I<Values.Num();++I)
    {
        const bool High=Ratings[I]>=HighThreshold;
        Values[I]->SetText(FText::FromString(FString::SanitizeFloat(FMath::RoundToFloat(Ratings[I]*10.f)/10.f,0)));
        Values[I]->SetColorAndOpacity(High?HUDGoldLight:TextPrimary);
        GrowthValues[I]->SetText(FText::FromString(TEXT("+")+FString::SanitizeFloat(FMath::RoundToFloat(Gains[I]*100.f)/100.f,1)));
        GrowthValues[I]->SetColorAndOpacity(High?HUDGoldLight:Success);
        if(TraitCards.IsValidIndex(I) && TraitCards[I])
            TraitCards[I]->SetBorderImage(High?&TraitHighBrush:&TraitNormalBrush);
        if(TraitRanks.IsValidIndex(I) && TraitRanks[I])
        {
            TraitRanks[I]->SetText(FText::FromString(High?TEXT("◆ 强势"):TEXT("常规")));
            TraitRanks[I]->SetColorAndOpacity(High?HUDGold:TextTertiary);
        }
        if(TraitBars.IsValidIndex(I) && TraitBars[I])
        {
            TraitBars[I]->SetPercent(FMath::Clamp(Ratings[I]/ScaleCap,0.f,1.f));
            TraitBars[I]->SetFillColorAndOpacity(High?HUDGold:FLinearColor(.78f,.80f,.84f,.72f));
        }
    }

    const float SpeedVal=T.CanterSpeed()*Affix.BaseMoveMultiplier*Affix.CanterSpeedMultiplier*(1.f+TB.SpeedBonus)/100.f;
    const float JumpVal=T.JumpRise()*(1.f+TB.JumpBonus)/100.f;
    const float TurnVal=88.f*T.TurnScale()*Affix.TurnMultiplier*(1.f+TB.TurnBonus);
    const float RecVal=100.f*T.RecoveryScale()*Affix.StaminaRecoveryMultiplier*(1.f+TB.StaminaRecoveryBonus);
    const float EffMaxHP=T.HealthLimit()*Affix.HealthMultiplier+TB.MaxHealthAdd;
    const float HealVal=EffMaxHP*(.025f*T.HealingScale()*(1.f+TB.HealRateBonus)+Affix.NaturalRegenPerSecondPct);
    const float DrVal=TB.MountedDamageReduction*100.f;
    const FString Data[]={
        FString::Printf(TEXT("%.1f"),SpeedVal),
        FString::Printf(TEXT("%.2f"),JumpVal),
        FString::Printf(TEXT("%.0f"),TurnVal),
        FString::Printf(TEXT("%.0f"),RecVal),
        FString::Printf(TEXT("%.1f"),HealVal),
        FString::Printf(TEXT("%.0f"),DrVal)};
    const float Deltas[]={
        (SpeedVal/11.6f-1.f)*100.f,
        (JumpVal/2.20f-1.f)*100.f,
        (T.TurnScale()*Affix.TurnMultiplier*(1.f+TB.TurnBonus)-1.f)*100.f,
        (T.RecoveryScale()*Affix.StaminaRecoveryMultiplier*(1.f+TB.StaminaRecoveryBonus)-1.f)*100.f,
        (HealVal/7.5f-1.f)*100.f,
        DrVal};
    for(int32 I=0;I<Performance.Num();++I)
    {
        Performance[I]->SetText(FText::FromString(Data[I]));
        if(PerformanceDeltas.IsValidIndex(I) && PerformanceDeltas[I])
        {
            if(I==5)
            {
                if(TB.bFullSet){PerformanceDeltas[I]->SetText(FText::FromString(TEXT("4件套")));PerformanceDeltas[I]->SetColorAndOpacity(HUDGoldLight);}
                else if(DrVal>0.f){PerformanceDeltas[I]->SetText(FText::FromString(TEXT("面甲")));PerformanceDeltas[I]->SetColorAndOpacity(Success);}
                else {PerformanceDeltas[I]->SetText(FText::FromString(TEXT("无")));PerformanceDeltas[I]->SetColorAndOpacity(TextTertiary);}
                continue;
            }
            const int32 PctDelta=FMath::RoundToInt(Deltas[I]);
            if(PctDelta>0)
            {
                PerformanceDeltas[I]->SetText(FText::FromString(FString::Printf(TEXT("+%d%%"),PctDelta)));
                PerformanceDeltas[I]->SetColorAndOpacity(Success);
            }
            else if(PctDelta<0)
            {
                PerformanceDeltas[I]->SetText(FText::FromString(FString::Printf(TEXT("%d%%"),PctDelta)));
                PerformanceDeltas[I]->SetColorAndOpacity(Warning);
            }
            else
            {
                PerformanceDeltas[I]->SetText(FText::FromString(TEXT("基准")));
                PerformanceDeltas[I]->SetColorAndOpacity(TextTertiary);
            }
        }
    }

    // Populate Horse Affixes Section
    if(AffixCountText)
    {
        const int32 SpecialCount=AffixList.FilterByPredicate([](EStableHorseAffix A){
            return StableHorseAffixes::Definition(A).Tier==EStableHorseAffixTier::Special;}).Num();
        AffixCountText->SetText(FText::FromString(SpecialCount>0
            ? FString::Printf(TEXT("%d 条词条 · 含稀有特殊词条"),AffixList.Num())
            : FString::Printf(TEXT("%d 条词条"),AffixList.Num())));
    }
    if(AffixWrap)
    {
        AffixWrap->ClearChildren();
        static const FSlateBrush SpecialBrush=RoundedBrush(FLinearColor::FromSRGBColor(FColor(42,33,19,232)),6,HUDGold,1.25f);
        static const FSlateBrush PosMajorBrush=RoundedBrush(FLinearColor::FromSRGBColor(FColor(18,40,32,226)),6,FLinearColor(.42f,.88f,.64f,.85f),1.15f);
        static const FSlateBrush PosBrush=RoundedBrush(FLinearColor::FromSRGBColor(FColor(18,34,29,220)),6,FLinearColor(.36f,.78f,.56f,.65f),1.f);
        static const FSlateBrush NegBrush=RoundedBrush(FLinearColor::FromSRGBColor(FColor(40,20,24,222)),6,FLinearColor(.84f,.38f,.44f,.68f),1.f);
        static const FSlateBrush NegMajorBrush=RoundedBrush(FLinearColor::FromSRGBColor(FColor(52,18,22,232)),6,FLinearColor(.94f,.34f,.40f,.88f),1.15f);

        for(EStableHorseAffix A:AffixList)
        {
            const auto& Def=StableHorseAffixes::Definition(A);
            const FString Key(Def.Id);
            TSharedPtr<FSlateBrush>* FoundBrush=AffixBrushes.Find(Key);
            if(!FoundBrush)
            {
                UTexture2D* Tex=AffixTextures.FindRef(Key);
                if(!Tex)
                {
                    Tex=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData/Icons/HorseAffixes")/(Key+TEXT(".png")));
                    if(Tex)AffixTextures.Add(Key,Tex);
                }
                TSharedPtr<FSlateBrush> NewBrush=MakeShared<FSlateBrush>();
                NewBrush->SetResourceObject(Tex);
                NewBrush->DrawAs=ESlateBrushDrawType::Image;
                NewBrush->SetImageSize(FVector2D(34,34));
                FoundBrush=&AffixBrushes.Add(Key,NewBrush);
            }

            const FSlateBrush* CardBrush=&PosBrush;
            FLinearColor TitleCol=TextPrimary;
            FLinearColor SubCol=Success;
            switch(Def.Tier)
            {
                case EStableHorseAffixTier::Special:       CardBrush=&SpecialBrush; TitleCol=HUDGoldLight; SubCol=HUDGold; break;
                case EStableHorseAffixTier::PositiveMajor: CardBrush=&PosMajorBrush; TitleCol=FLinearColor(.82f,.98f,.88f,1.f); SubCol=Success; break;
                case EStableHorseAffixTier::Positive:      CardBrush=&PosBrush; TitleCol=TextPrimary; SubCol=Success; break;
                case EStableHorseAffixTier::Negative:      CardBrush=&NegBrush; TitleCol=FLinearColor(.96f,.82f,.84f,1.f); SubCol=Warning; break;
                case EStableHorseAffixTier::NegativeMajor: CardBrush=&NegMajorBrush; TitleCol=FLinearColor(1.f,.84f,.82f,1.f); SubCol=Danger; break;
            }

            const FString DisplayTitle=(Def.Tier==EStableHorseAffixTier::Special)?(FString(TEXT("★ "))+Def.Name):FString(Def.Name);
            const FString TipText=FString::Printf(TEXT("%s\n%s"),*DisplayTitle,Def.Description);
            auto Chip=SNew(SBorder).BorderImage(CardBrush).Padding(FMargin(8,6,10,6))
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,8,0)
                [
                    SNew(SBox).WidthOverride(34).HeightOverride(34)
                    [SNew(SImage).Image(FoundBrush->Get())]
                ]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                [
                    SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()
                    [SNew(STextBlock).Text(FText::FromString(DisplayTitle)).Font(TextFont(12.f,true)).ColorAndOpacity(TitleCol)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,1,0,0)
                    [SNew(STextBlock).Text(FText::FromString(Def.ShortEffect)).Font(TextFont(10.f)).ColorAndOpacity(SubCol)]
                ]
            ];
            ColdSteelToolTip::Set(*Chip,FText::FromString(TipText));
            AffixWrap->AddSlot()[Chip];
        }
    }

    for(int32 I=0;I<Buttons.Num();++I)
    {
        const auto* Item=StableHorseGear::At(Horse,I);
        const FString Name=Item?ColdSteelInventory::Text(*Item,TEXT("name")):TEXT("未装备");
        Captions[I]->SetText(FText::FromString(Name));
        Captions[I]->SetColorAndOpacity(Item?TextPrimary:TextTertiary);
        if(GearSubLabels.IsValidIndex(I) && GearSubLabels[I])
        {
            GearSubLabels[I]->SetText(Item?FText::FromString(StableHorseGear::ShortSlotEffect(I)):FText::GetEmpty());
            GearSubLabels[I]->SetColorAndOpacity(Success);
            GearSubLabels[I]->SetVisibility(Item?EVisibility::HitTestInvisible:EVisibility::Collapsed);
        }

        Brushes[I].SetResourceObject(Textures[I]);
        Brushes[I].DrawAs=ESlateBrushDrawType::Image;
        Brushes[I].SetImageSize(FVector2D(256,256));
        GearImages[I]->SetImage(&Brushes[I]);
        // Keep real tack silhouette always visible: subtle monochrome watermark when empty, full color when equipped!
        GearImages[I]->SetVisibility(Textures[I]?EVisibility::HitTestInvisible:EVisibility::Collapsed);
        GearImages[I]->SetColorAndOpacity(Item?FLinearColor::White:FLinearColor(.74f,.78f,.84f,.18f));
        EmptyMarks[I]->SetText(FText::FromString(Editable?TEXT("+"):TEXT("—")));
        EmptyMarks[I]->SetVisibility(Item?EVisibility::Collapsed:EVisibility::HitTestInvisible);

        FLinearColor Fill=Gray(14,220),Stroke=Gray(220,34),AccentCol=FLinearColor::Transparent,ArtEdge=Gray(222,30);
        if(Item)
        {
            const FLinearColor Rarity=RarityColor(ColdSteelInventory::Text(*Item,TEXT("rarity")));
            Fill=FMath::Lerp(Gray(22,235),Rarity,.14f);Fill.A=.92f;
            Stroke=Rarity;Stroke.A=.54f;
            AccentCol=Rarity;AccentCol.A=.92f;
            ArtEdge=Rarity;ArtEdge.A=.62f;
            Captions[I]->SetColorAndOpacity(FMath::Lerp(TextPrimary,Rarity,.30f));
        }
        CellBrushes[I]=RoundedBrush(Fill,6,Stroke,1.f);
        GearAccentBrushes[I]=RoundedBrush(AccentCol,1.25f,FLinearColor::Transparent,0);
        GearArtFrameBrushes[I]=RoundedBrush(Gray(10,235),5,ArtEdge,1.f);
        if(GearAccentBars.IsValidIndex(I) && GearAccentBars[I])
        {
            GearAccentBars[I]->SetBorderImage(&GearAccentBrushes[I]);
            GearAccentBars[I]->SetVisibility(Item?EVisibility::HitTestInvisible:EVisibility::Collapsed);
        }
        if(GearArtFrames.IsValidIndex(I) && GearArtFrames[I])GearArtFrames[I]->SetBorderImage(&GearArtFrameBrushes[I]);

        FString Hint=FString(StableHorseGear::Labels[I])+TEXT(" · ")+Name;
        if(Item)
        {
            Hint+=TEXT("\n")+FString(StableHorseGear::ShortSlotEffect(I));
            Hint+=FString::Printf(TEXT("\n套装 · %s (%d/%d)%s"),
                StableHorseGear::SetName,TB.EquippedCount,StableHorseGear::Count,
                TB.bFullSet?TEXT("：疾驰+5% · 骑乘减伤+5% · 耗耐-10%（已激活）"):TEXT("：齐套激活疾驰+5% · 减伤+5% · 耗耐-10%"));
        }
        ColdSteelToolTip::Set(*Buttons[I],FText::FromString(Hint));
        Buttons[I]->SetVisibility(Editable?EVisibility::Visible:EVisibility::HitTestInvisible);
        Buttons[I]->Invalidate(EInvalidateWidgetReason::Paint);
    }
}

void UColdSteelMountGearPanel::UpdateCondition(const FStableMountRecord& Horse,const FString& State,float Health,float Stamina)
{
    if(!StateText || HorseId!=Horse.HorseId)return;
    if(LastState!=State)
    {
        LastState=State;
        StateText->SetText(FText::FromString(State));
    }
    if(LastLevel!=Horse.Level || LastXP!=Horse.Experience)
    {
        LastLevel=Horse.Level;LastXP=Horse.Experience;
        LevelText->SetText(FText::FromString(FString::Printf(TEXT("Lv.%d"),Horse.Level)));
        const int64 Required=Horse.ExperienceNeeded(Horse.Level);
        const bool Max=Horse.Level>=FStableHorseTraits::MaxLevel;
        ExperienceText->SetFont(Max?ColdSteelUI::TextFont(10.5f,true):ColdSteelUI::NumberFont(10.5f));
        ExperienceText->SetText(FText::FromString(Max?TEXT("已满级"):FString::Printf(TEXT("%lld / %lld XP"),Horse.Experience,Required)));
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

bool UColdSteelMountGearPanel::TryQuickEquip(const FString& ItemId)
{
    auto* M=Model.Get();
    if(!Editable || !HorseId.IsValid() || !M)return false;
    const auto* Item=M->FindItem(ItemId);
    const bool bInHorseBag=Item && Item->Place==ColdSteelWarehouse::Place && Item->Container==StableHorseAffixes::BagContainerKey(HorseId);
    if(!Item || (Item->Place!=0 && Item->Place!=ColdSteelInventory::ColdSteelCompartment::Place && !bInHorseBag))return false;
    const int32 SlotIndex=StableHorseGear::SlotOf(Item->Definition);
    if(SlotIndex==INDEX_NONE)return false;
    Change(HorseId,SlotIndex,ItemId,true);
    return true;
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
    const FString HorseBagKey=Horse->BagContainerKey();
    for(const auto& Item:M->Items())
        if((Item.Place==0 || Item.Place==ColdSteelInventory::ColdSteelCompartment::Place || (Item.Place==ColdSteelWarehouse::Place && Item.Container==HorseBagKey)) && StableHorseGear::SlotOf(Item.Definition)==GearIndex)
            Add(TEXT("装备  ")+ColdSteelInventory::Text(Item,TEXT("name")),Item.InstanceId,true);
    if(!List->NumSlots())List->AddSlot().Padding(8)[SNew(STextBlock).Font(ColdSteelUI::TextFont(12))
        .Text(FText::FromString(TEXT("背包中没有适用马具")))];
    return SNew(SBox).MinDesiredWidth(180).MaxDesiredHeight(236)
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
    {
        const FString HorseBagKey=StableHorseAffixes::BagContainerKey(HorseId);
        const bool bValidSource=Drag->SourcePlace==0 || Drag->SourcePlace==ColdSteelInventory::ColdSteelCompartment::Place ||
            (Drag->SourcePlace==ColdSteelWarehouse::Place && Drag->SourceSnapshot.Container==HorseBagKey);
        for(int32 I=0;I<Buttons.Num();++I)
            if(Buttons[I]->GetCachedGeometry().IsUnderLocation(Position))
            {
                if(Drag->bHasSourceSnapshot && bValidSource && StableHorseGear::SlotOf(Drag->SourceSnapshot.Definition)==I)
                    ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::SlotDrop);
                Change(HorseId,I,Drag->ItemId,true);return true;
            }
    }
    return false;
}

bool UColdSteelMountGearPanel::NativeOnDragOver(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Op)
{
    const auto* Drag=Cast<UColdSteelItemDrag>(Op);
    DropIndex=INDEX_NONE;bDropAllowed=false;
    if(!Drag)return false;
    const FVector2D PointerPosition=E.GetScreenSpacePosition();
    const FString HorseBagKey=StableHorseAffixes::BagContainerKey(HorseId);
    for(int32 I=0;Editable && I<Buttons.Num();++I)
        if(Buttons[I]->GetCachedGeometry().IsUnderLocation(PointerPosition))
        {
            DropIndex=I;
            const bool bValidSource=Drag->SourcePlace==0 || Drag->SourcePlace==ColdSteelInventory::ColdSteelCompartment::Place ||
                (Drag->SourcePlace==ColdSteelWarehouse::Place && Drag->SourceSnapshot.Container==HorseBagKey);
            bDropAllowed=Drag->bHasSourceSnapshot && bValidSource && StableHorseGear::SlotOf(Drag->SourceSnapshot.Definition)==I;
            break;
        }
    return true;
}

void UColdSteelMountGearPanel::NativeOnDragLeave(const FDragDropEvent& E,UDragDropOperation* Op)
{
    DropIndex=INDEX_NONE;bDropAllowed=false;Super::NativeOnDragLeave(E,Op);
}

bool UColdSteelMountGearPanel::NativeOnDrop(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Op)
{
    return HandleItemDrop(Cast<UColdSteelItemDrag>(Op),E.GetScreenSpacePosition());
}
