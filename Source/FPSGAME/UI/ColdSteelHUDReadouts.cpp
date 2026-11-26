#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuestJournal.h"
#include "StatusEffectsHUD.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../FPSGAMEPlayerController.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../Building/ColdSteelCampfire.h"
#include "ColdSteelSceneContainer.h"
#include "Framework/Application/SlateApplication.h"
#include "ColdSteelGunAssemblyWidget.h"
#include "ColdSteelIncineratorWidget.h"
#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelWorkbenchWidget.h"
#include "../Building/VoxelBuildWorld.h"
#include "Widgets/SWidget.h"
#include "ColdSteelSkillPage.h"
#include "ColdSteelCodexPage.h"
#include "ColdSteelProgressNotification.h"
#include "ColdSteelSkillTreeScreen.h"
#include "ColdSteelDungeonTracker.h"
#include "ColdSteelAcquisitionFeed.h"
#include "ColdSteelExperienceFeed.h"
#include "ColdSteelDamageNumbers.h"
#include "ColdSteelAmmoReadout.h"
#include "ColdSteelAmmoPouchWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelWorldClock.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "Dom/JsonValue.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/GameInstance.h"

#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelWorldInteraction.h"

#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScaleBox.h"
#include "Components/ScaleBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/Spacer.h"
#include "Components/TextBlock.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Input/Reply.h"
#include "InputCoreTypes.h"
#include "Misc/Paths.h"
#include "Styling/SlateTypes.h"
#include "UObject/UnrealType.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

#include "ColdSteelHUDPrivate.h"
using namespace ColdSteelHUDPrivate;

void UColdSteelHUDWidget::RefreshAmmo()
{
    RefreshQuickBar();

    const AFPSGAMECharacter* Character = GetOwningPlayerPawn<AFPSGAMECharacter>();
    if(AmmoReadout)
    {
        AmmoReadout->Refresh(Character,StatusModel,bInventoryOpen);
        // The bottom-right weapon readout and the drawer share the right edge; hide it during the slide too.
        if(bInventoryOpen||DrawerProgress>KINDA_SMALL_NUMBER||bExternalDrawerOpen)AmmoReadout->SetVisibility(ESlateVisibility::Collapsed);
        const float S=ColdSteelUI::PixelScale(this);
        FVector2D View=GetCachedGeometry().GetLocalSize();
        if(View.X<100)View=UWidgetLayoutLibrary::GetViewportSize(this)/S;
        if(View.X>0)
        {
            const float Width=FMath::Min(UColdSteelAmmoReadout::PreferredWidth,FMath::Max(1.f,float(View.X)*S-40.f));
            const FVector2D HotbarSize=HotbarCanvasSlot?HotbarCanvasSlot->GetSize():FVector2D::ZeroVector;
            const bool HintsVisible=BottomHintsSlot&&BottomHintsSlot->GetSize().Y>0;
            const float CentralWidth=FMath::Max(FMath::Max(float(HotbarSize.X),424/S),HintsVisible?float(BottomHintsSlot->GetSize().X):0.f);
            const float HotbarRight=View.X*.5f+CentralWidth*.5f;
            float Bottom=20/S;
            if(View.X-20/S-Width/S<HotbarRight+12/S)
            {
                const float HotbarBottom=HotbarCanvasSlot?-HotbarCanvasSlot->GetPosition().Y:12/S;
                const float HotbarTop=HotbarBottom+FMath::Max(float(HotbarSize.Y),66/S);
                const float StaminaTop=StaminaSlot?-StaminaSlot->GetPosition().Y+StaminaSlot->GetSize().Y:HotbarTop;
                const float HintTop=HintsVisible?-BottomHintsSlot->GetPosition().Y+BottomHintsSlot->GetSize().Y:StaminaTop;
                Bottom=FMath::Max(FMath::Max(HotbarTop,StaminaTop),HintTop)+12/S;
            }
            AmmoReadout->UpdateLayout(Width,Bottom*S);
        }
    }
}

void UColdSteelHUDWidget::RefreshStatus()
{
    RefreshCharacterSheet();
    RefreshExpBar();
    const AFPSGAMECharacter* Character = GetOwningPlayerPawn<AFPSGAMECharacter>();
    if (!Character) return;
    const UFPSCombatHealthComponent* Health = Character->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Health && HealthBar && HealthValueText)
    {
        const float MaxHealth = FMath::Max(1.0f, Health->MaxHealth);
        SetAnimatedBarValue(HealthBar,FMath::Clamp(Health->Health / MaxHealth, 0.0f, 1.0f));
        HealthValueText->SetText(FText::FromString(FString::Printf(TEXT("%.0f/%.0f"), Health->Health, MaxHealth)));
    }
    if (AmmoStatusValueText)
    {
        const bool Sword=StatusModel&&StatusModel->Equipped()&&ColdSteelInventory::IsTwoHandedSword(*StatusModel->Equipped());
        AmmoStatusValueText->SetText(FText::FromString(Sword?TEXT("近战"):FString::Printf(TEXT("%d/%d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo())));
    }
    if (MoveSpeedValueText && Character->GetCharacterMovement())
    {
        MoveSpeedValueText->SetText(FText::FromString(FString::Printf(TEXT("%.1f m/s"), Character->GetCharacterMovement()->MaxWalkSpeed / 100.0f)));
    }
    if (EquipmentDamageValue && EquipmentCapacityValue && EquipmentIntervalValue && EquipmentReloadValue && EquipmentAmmoValue)
    {
        float Damage = 0.0f;
        float Interval = 0.0f;
        float Reload = 0.0f;
        int32 Capacity = Character->GetMagazineAmmo();
        if (const FFloatProperty* Property = FindFProperty<FFloatProperty>(Character->GetClass(), TEXT("DamagePerShot"))) Damage = Property->GetPropertyValue_InContainer(Character);
        if (const FFloatProperty* Property = FindFProperty<FFloatProperty>(Character->GetClass(), TEXT("FireInterval"))) Interval = Property->GetPropertyValue_InContainer(Character);
        if (const FFloatProperty* Property = FindFProperty<FFloatProperty>(Character->GetClass(), TEXT("ReloadDuration"))) Reload = Property->GetPropertyValue_InContainer(Character);
        if (const FIntProperty* Property = FindFProperty<FIntProperty>(Character->GetClass(), TEXT("MagazineCapacity"))) Capacity = Property->GetPropertyValue_InContainer(Character);
        const FColdSteelItem* Equipped=StatusModel?StatusModel->Equipped():nullptr;
        const bool Sword=Equipped&&ColdSteelInventory::IsTwoHandedSword(*Equipped);
        double MeleeInterval=0.;
        if(Sword)
        {
            const FMeleeWeaponStats Melee=ColdSteelMelee::Evaluate(*Equipped,StatusModel);
            Damage=Melee.Damage;
            MeleeInterval=Melee.AttackSeconds;
        }
        EquipmentDamageValue->SetText(FText::FromString(FString::Printf(TEXT("%.2f"), Damage)));
        EquipmentCapacityValue->SetText(FText::FromString(FString::Printf(TEXT("%d 发"), Capacity)));
        EquipmentIntervalValue->SetText(FText::FromString(FString::Printf(TEXT("%.0fms"), (Sword?MeleeInterval:Interval) * 1000.0)));
        EquipmentReloadValue->SetText(FText::FromString(FString::Printf(TEXT("%.0fms"), Reload * 1000.0f)));
        EquipmentAmmoValue->SetText(FText::FromString(FString::Printf(TEXT("%d / %d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo())));
        if(Sword)
        {EquipmentCapacityValue->SetText(FText::FromString(TEXT("—")));EquipmentReloadValue->SetText(FText::FromString(TEXT("—")));EquipmentAmmoValue->SetText(FText::FromString(TEXT("近战")));}
    }
    if (EquipmentTraitsBox)
    {
        const FString Def=StatusModel&&StatusModel->ActiveFirearm()?StatusModel->ActiveFirearm()->Definition:FString();
        if (Def!=EquipmentTraitsWeapon)
        {
            EquipmentTraitsWeapon=Def;
            EquipmentTraitsBox->ClearChildren();
            const UGunsmithSystem* Gunsmith=GetGameInstance()?GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
            const FGunsmithWeapon* Weapon=Gunsmith?Gunsmith->ModifiableWeapon(Def):nullptr;
            const TArray<TSharedPtr<FJsonValue>>* Traits=nullptr;
            if (Weapon&&Weapon->Source.IsValid()&&Weapon->Source->TryGetArrayField(TEXT("traits"),Traits)&&Traits)
            {
                int32 Shown=0;
                for (const TSharedPtr<FJsonValue>& Entry:*Traits)
                {
                    const TSharedPtr<FJsonObject> Trait=Entry.IsValid()?Entry->AsObject():nullptr;
                    if (!Trait.IsValid())continue;
                    FString Icon,Text;
                    Trait->TryGetStringField(TEXT("icon"),Icon);
                    Trait->TryGetStringField(TEXT("text"),Text);
                    if (Text.IsEmpty())continue;
                    if (!Shown++)AddTooltipSection(EquipmentTraitsBox,TEXT("特殊性质"));
                    const FLinearColor Color=Icon==TEXT("special")?ColdSteelUI::ItemTraitSpecial:Icon==TEXT("magic")?ColdSteelUI::ItemTraitMagic:Icon==TEXT("mechanic")?ColdSteelUI::ItemTraitMechanic:Icon==TEXT("drawback")?ColdSteelUI::ItemTraitDrawback:ColdSteelUI::ItemTraitNeutral;
                    UTextBlock* Line=MakeReferenceText(Text,13,Color);
                    Line->SetAutoWrapText(true);
                    EquipmentTraitsBox->AddChildToVerticalBox(Line)->SetPadding(FMargin(0,ReferenceUnits(2),0,ReferenceUnits(2)));
                }
            }
        }
    }
}



void UColdSteelHUDWidget::ShowEquipmentTooltip()
{
    if (!EquipmentTooltip || !bInventoryOpen || bStatusTabActive || bSkillsTabActive || bCodexTabActive || bQuestTabActive||bMountTabActive) return;
    RefreshStatus();
    EquipmentTooltip->SetVisibility(ESlateVisibility::Visible);
    EquipmentTooltipScroll->ScrollToEnd();
    if (!bEquipmentTooltipPinned) UpdateEquipmentTooltipPlacement();
}

void UColdSteelHUDWidget::HideEquipmentTooltip()
{
    if (EquipmentTooltip) EquipmentTooltip->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::UpdateEquipmentTooltipPlacement()
{
    if (!EquipmentTooltipCanvasSlot) return;
    APlayerController* PC = GetOwningPlayer();
    if (!PC) return;
    FVector2D ViewportPixels = UWidgetLayoutLibrary::GetViewportSize(this);
    const float Scale = ColdSteelUI::PixelScale(this);
    const FVector2D ViewportUnits = ViewportPixels / Scale;
    float MouseX = 0.0f;
    float MouseY = 0.0f;
    const bool bMouse = UWidgetLayoutLibrary::GetMousePositionScaledByDPI(PC, MouseX, MouseY);
    if ((!bMouse || (EquippedItemButton && EquippedItemButton->HasKeyboardFocus())) && EquippedItemButton)
    {
        const auto& Geometry = EquippedItemButton->GetCachedGeometry();
        const FVector2D Anchor = GetCachedGeometry().AbsoluteToLocal(Geometry.LocalToAbsolute(FVector2D::ZeroVector));
        MouseX = Anchor.X; MouseY = Anchor.Y;
    }
    const FVector2D Extent(FMath::Min(ReferenceUnits(510), (ViewportPixels.X - 20.0f) / Scale), ReferenceUnits(360.0f));
    const float Gap = ReferenceUnits(10.0f);
    FVector2D Position(MouseX - Extent.X - Gap, MouseY + Gap);
    if (Position.X < Gap) Position.X = MouseX + Gap;
    if (Position.Y + Extent.Y > ViewportUnits.Y - Gap) Position.Y = MouseY - Extent.Y - Gap;
    Position.X = FMath::Clamp(Position.X, Gap, FMath::Max(Gap, ViewportUnits.X - Extent.X - Gap));
    Position.Y = FMath::Clamp(Position.Y, Gap, FMath::Max(Gap, ViewportUnits.Y - Extent.Y - Gap));
    EquipmentTooltipCanvasSlot->SetAnchors(FAnchors(0.0f));
    EquipmentTooltipCanvasSlot->SetPosition(Position);
    EquipmentTooltipCanvasSlot->SetSize(Extent);
}

void UColdSteelHUDWidget::SetInventoryAuditState(int32 State)
{
    SetInventoryOpen(true);
    DrawerProgress = 1.0f;
    if (InventoryPanel) InventoryPanel->SetRenderTranslation(FVector2D::ZeroVector);
    if (State <= 0)
    {
        SetInventoryTab(true);
        ShowStatusTooltip(TEXT("str"));
    }
    else
    {
        SetInventoryTab(false);
        bEquipmentTooltipPinned = true;
        ShowEquipmentTooltip();
    }
}

void UColdSteelHUDWidget::PlayButtonClick()
{
    if (auto* Sound = LoadObject<USoundBase>(nullptr, TEXT("/Game/Audio/GamedevUI20261002/S_Button_Click.S_Button_Click")))
        UGameplayStatics::PlaySound2D(this, Sound, 1.f, 1.f);
}

void UColdSteelHUDWidget::HandleStatusTabClicked() { PlayButtonClick(); OpenStatus(); }
void UColdSteelHUDWidget::HandleEquipmentTabClicked() { PlayButtonClick(); SetInventoryTab(false); }
void UColdSteelHUDWidget::HandleStrengthHovered() { ShowStatusTooltip(TEXT("str")); }
void UColdSteelHUDWidget::HandleDexterityHovered() { ShowStatusTooltip(TEXT("dex")); }
void UColdSteelHUDWidget::HandleIntelligenceHovered() { ShowStatusTooltip(TEXT("intt")); }
void UColdSteelHUDWidget::HandleConstitutionHovered() { ShowStatusTooltip(TEXT("con")); }
void UColdSteelHUDWidget::HandleWisdomHovered() { ShowStatusTooltip(TEXT("wis")); }
void UColdSteelHUDWidget::HandleLuckHovered() { ShowStatusTooltip(TEXT("luck")); }
void UColdSteelHUDWidget::HandleAttributeUnhovered() { HideStatusTooltip(); }
void UColdSteelHUDWidget::HandleEquipmentHovered() { ShowEquipmentTooltip(); }
void UColdSteelHUDWidget::HandleEquipmentUnhovered() { if (!bEquipmentTooltipPinned && (!EquippedItemButton || !EquippedItemButton->HasKeyboardFocus())) HideEquipmentTooltip(); }
void UColdSteelHUDWidget::HandleEquipmentClicked()
{
    bEquipmentTooltipPinned = !bEquipmentTooltipPinned;
    if (bEquipmentTooltipPinned) ShowEquipmentTooltip(); else HideEquipmentTooltip();
}
void UColdSteelHUDWidget::HandleEquipmentTooltipCloseClicked()
{
    bEquipmentTooltipPinned = false;
    HideEquipmentTooltip();
}

UTextBlock* UColdSteelHUDWidget::MakeText(const FString& Text, int32 Size, const FLinearColor& Color, bool bNumeric, bool bBold)
{
    UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), *FString::Printf(TEXT("Text_%d"), WidgetSerial++));
    Label->SetText(FText::FromString(Text));
    Label->SetFont(bNumeric ? ColdSteelUI::NumberFont(Size, bBold) : ColdSteelUI::TextFont(Size, bBold));
    Label->SetColorAndOpacity(Color);
    Label->SetShadowOffset(FVector2D(0.0f, 1.0f));
    Label->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.55f));
    return Label;
}

float UColdSteelHUDWidget::ReferenceUnits(float PixelSize) const
{
    const float ViewportScale = ColdSteelUI::PixelScale(this);
    return PixelSize / ViewportScale;
}

UTextBlock* UColdSteelHUDWidget::MakeReferenceText(const FString& Text, float PixelSize, const FLinearColor& Color, bool bNumeric, bool bBold)
{
    auto* Label = MakeText(Text, 12, Color, bNumeric, bBold);
    // Slate uses points at 96 DPI; the reference contract specifies physical pixels.
    const float Points = ReferenceUnits(PixelSize) * .75f;
    Label->SetFont(bNumeric ? ColdSteelUI::NumberFont(Points, bBold) : ColdSteelUI::TextFont(Points, bBold));
    return Label;
}

UBorder* UColdSteelHUDWidget::MakeSurface(const FLinearColor& Fill, float Radius, const FLinearColor& Outline, float OutlineWidth)
{
    UBorder* Surface = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), *FString::Printf(TEXT("Surface_%d"), WidgetSerial++));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(Fill, Radius, Outline, OutlineWidth));
    return Surface;
}

UBorder* UColdSteelHUDWidget::MakeEquipmentSlot(const FString& Caption, bool bEquipped)
{
    UBorder* Surface = MakeSurface(bEquipped ? SlotEquipped : SlotDark, 7.0f, ColdSteelUI::Border);
    Surface->SetPadding(FMargin(4.0f));
    USizeBox* Height = WidgetTree->ConstructWidget<USizeBox>();
    Height->SetMinDesiredHeight(50.0f);
    Surface->SetContent(Height);
    UOverlay* Layer = WidgetTree->ConstructWidget<UOverlay>();
    Height->SetContent(Layer);
    if (bEquipped)
    {
        if (UTexture2D* Texture = LoadUiTexture(TEXT("ue_m4a1.png")))
        {
            UImage* Image = WidgetTree->ConstructWidget<UImage>();
            Image->SetBrushFromTexture(Texture, true);
            UOverlaySlot* ImageSlot = Layer->AddChildToOverlay(Image);
            ImageSlot->SetHorizontalAlignment(HAlign_Fill);
            ImageSlot->SetVerticalAlignment(VAlign_Fill);
            ImageSlot->SetPadding(FMargin(24.0f, 4.0f, 20.0f, 4.0f));
        }
        UBorder* Rail = MakeSurface(FLinearColor(0.72f, 0.76f, 0.84f, 0.9f), 3.0f, FLinearColor::Transparent, 0.0f);
        UOverlaySlot* RailSlot = Layer->AddChildToOverlay(Rail);
        RailSlot->SetHorizontalAlignment(HAlign_Left);
        RailSlot->SetVerticalAlignment(VAlign_Fill);
        RailSlot->SetPadding(FMargin(2.0f));
        USizeBox* RailWidth = WidgetTree->ConstructWidget<USizeBox>();
        RailWidth->SetWidthOverride(8.0f);
        Rail->SetContent(RailWidth);
    }
    else
    {
        UTextBlock* Label = MakeReferenceText(Caption, 16, Caption == TEXT("双手占用") ? FLinearColor(0.35f, 0.38f, 0.40f, 1.0f) : ColdSteelUI::TextSecondary);
        Label->SetJustification(ETextJustify::Center);
        UOverlaySlot* LabelSlot = Layer->AddChildToOverlay(Label);
        LabelSlot->SetHorizontalAlignment(HAlign_Fill);
        LabelSlot->SetVerticalAlignment(VAlign_Center);
    }
    return Surface;
}

UBorder* UColdSteelHUDWidget::MakeTab(const FString& Caption, bool bActive)
{
    UBorder* Surface = MakeSurface(bActive?GunsmithUI::Gray(75,110):GunsmithUI::Gray(18,32),ReferenceUnits(7),FLinearColor::Transparent,0);
    USizeBox* Height = WidgetTree->ConstructWidget<USizeBox>();
    Height->SetHeightOverride(ReferenceUnits(40));
    InventoryTabSizes.Add(Height);
    Surface->SetContent(Height);
    UOverlay* Layer = WidgetTree->ConstructWidget<UOverlay>();
    Height->SetContent(Layer);
    UTextBlock* Label = MakeInventoryText(Caption,14,bActive?GunsmithUI::Text:GunsmithUI::Muted,false,bActive);
    Label->SetJustification(ETextJustify::Center);
    UOverlaySlot* LabelSlot = Layer->AddChildToOverlay(Label);
    LabelSlot->SetHorizontalAlignment(HAlign_Fill);
    LabelSlot->SetVerticalAlignment(VAlign_Center);
    UBorder* Underline = MakeSurface(GunsmithUI::Silver,0,FLinearColor::Transparent,0);
    Underline->SetVisibility(bActive ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    UOverlaySlot* UnderlineSlot = Layer->AddChildToOverlay(Underline);
    UnderlineSlot->SetHorizontalAlignment(HAlign_Fill);
    UnderlineSlot->SetVerticalAlignment(VAlign_Bottom);
    USizeBox* UnderlineHeight = WidgetTree->ConstructWidget<USizeBox>();
    UnderlineHeight->SetHeightOverride(ReferenceUnits(2));
    Underline->SetContent(UnderlineHeight);
    return Surface;
}

UTexture2D* UColdSteelHUDWidget::LoadUiTexture(const FString& Filename)
{
    if (const TObjectPtr<UTexture2D>* Existing = LoadedTextureCache.Find(Filename))
    {
        return Existing->Get();
    }
    const FString Path = FPaths::ProjectContentDir() / TEXT("ColdSteelUI/Icons") / Filename;
    UTexture2D* Texture = FImageUtils::ImportFileAsTexture2D(Path);
    if (Texture)
    {
        LoadedTextures.Add(Texture);
        LoadedTextureCache.Add(Filename, Texture);
    }
    return Texture;
}

void UColdSteelHUDWidget::HandleCloseClicked()
{
    if (bQuestTabActive && QuestPage && QuestPage->GoBack()) return;
    SetInventoryOpen(false);
}
