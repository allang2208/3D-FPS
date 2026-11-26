#include "ColdSteelItemTooltip.h"
#include "ColdSteelDisclosureIndicator.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelUIStyle.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/M249WeaponAssets.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ExpandableArea.h"
#include "Components/HorizontalBox.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "InputCoreTypes.h"
#include "Misc/Paths.h"
#include "UObject/ConstructorHelpers.h"

UColdSteelItemTooltip::UColdSteelItemTooltip(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
    static ConstructorHelpers::FObjectFinder<UTexture2D> Atlas(TEXT("/Game/UI/GunsmithWorkbench/EquipmentTooltip/T_EquipmentEffectPulse.T_EquipmentEffectPulse"));
    EffectArrowAtlas=Atlas.Object;
}

void UColdSteelItemTooltip::NativeOnInitialized()
{
    Super::NativeOnInitialized();Scale=ColdSteelUI::PixelScale(this);SetIsFocusable(true);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    WeaponIcons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    Frame=WidgetTree->ConstructWidget<USizeBox>();WidgetTree->RootWidget=Frame;
    auto* Layers=WidgetTree->ConstructWidget<UOverlay>();Frame->SetContent(Layers);
    Shadow=WidgetTree->ConstructWidget<UBorder>();Shadow->SetVisibility(ESlateVisibility::HitTestInvisible);auto* ShadowSlot=Layers->AddChildToOverlay(Shadow);ShadowSlot->SetHorizontalAlignment(HAlign_Fill);ShadowSlot->SetVerticalAlignment(VAlign_Fill);
    Surface=WidgetTree->ConstructWidget<UBorder>();auto* SurfaceSlot=Layers->AddChildToOverlay(Surface);SurfaceSlot->SetHorizontalAlignment(HAlign_Fill);SurfaceSlot->SetVerticalAlignment(VAlign_Fill);
    Surface->SetHorizontalAlignment(HAlign_Fill);Surface->SetVerticalAlignment(VAlign_Fill);
    RootColumn=WidgetTree->ConstructWidget<UVerticalBox>();Surface->SetContent(RootColumn);
    SetVisibility(ESlateVisibility::Collapsed);
}
void UColdSteelItemTooltip::NativeConstruct()
{
    Super::NativeConstruct();
    if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::ProfileChanged);
    if(WeaponIcons&&!IconHandle.IsValid())IconHandle=WeaponIcons->OnReady.AddUObject(this,&ThisClass::OnWeaponIconReady);
}
void UColdSteelItemTooltip::NativeDestruct()
{
    if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();
    if(WeaponIcons)WeaponIcons->OnReady.Remove(IconHandle);IconHandle.Reset();
    Super::NativeDestruct();
}
FString UColdSteelItemTooltip::StructureSignature()const
{
    FString Result=bPinned?TEXT("detail"):TEXT("summary");
    if(Presentation.bEquipment)Result+=TEXT("|equipment");
    if(Presentation.EnhancementLevel>0)Result+=TEXT("|enhanced");
    if(!Presentation.ValueScope.IsEmpty())Result+=TEXT("|scope");
    Result+=Presentation.bWideIcon?TEXT("|wide"):TEXT("|square");
    Result+=Presentation.HasLifetimeBar()?TEXT("|lifetime-bar"):TEXT("|no-lifetime-bar");
    auto Rows=[&](const TArray<FColdSteelTooltipRow>& Values)
    {for(const auto& R:Values)
        {
            Result+=FString::Printf(TEXT("|%d:%d:%d:%d:%d:%d:%s"),R.bSection,R.bContinuation,R.bStacked,R.bDashedAfter,R.bPreview,R.Tone,*R.Label);
            if(Presentation.bEquipment && R.ShowsEffectArrow())Result+=TEXT("|arrow");
            if(R.Label==TEXT("当前词缀"))Result+=R.Value;
        }
    };
    Rows(Presentation.Summary);
    // 套装块只在缩略与详情共用的摘要区出现；件数变化必须触发重建，
    // 否则穿上/脱下套装后浮窗还停在旧进度。
    if(Presentation.bHasSet)
        Result+=FString::Printf(TEXT("|set:%s:%d:%d:%d:%d"),*Presentation.Set.Name,
            Presentation.Set.Equipped,Presentation.Set.Total,Presentation.Set.bComplete,
            Presentation.Set.Bonuses.Num());
    if(!Presentation.Cards.IsEmpty())
    {
        const auto& Main=Presentation.Cards.Last();
        for(int32 Index=0;Index<Main.Rows.Num();++Index)
        {
            const auto& R=Main.Rows[Index];if(!R.bPreview)continue;
            Result+=FString::Printf(TEXT("|preview:%d:%d:%d:%d:%d:%d:%d:%s"),Presentation.Cards.Num()-1,Index,R.bSection,R.bContinuation,R.bStacked,R.bDashedAfter,R.Tone,*R.Label);
            if(Presentation.bEquipment && R.ShowsEffectArrow())Result+=TEXT("|arrow");
        }
    }
    if(bPinned)
    {
        Result+=Presentation.ComparisonTitle.IsEmpty()?TEXT("|no-compare"):TEXT("|compare");Rows(Presentation.Comparison);
        for(const auto& C:Presentation.Cards){Result+=TEXT("|")+C.Title;Rows(C.Rows);}
        Result+=TEXT("|")+Presentation.Description;
    }
    return Result;
}
void UColdSteelItemTooltip::ShowItem(const FString& Id,FVector2D Anchor,bool Pin,UWidget* Source,const FColdSteelItemTooltipPreview* Preview)
{
    if(IsPinned()&&!Pin)return;
    const bool Changed=InstanceId!=Id||ReturnFocus.Get()!=Source,ModeChanged=bPinned!=Pin;
    if(Preview)PreviewInstance=*Preview;else PreviewInstance.Reset();
    if(Changed||ModeChanged||!IsVisible()){bPlacementLocked=false;bStartDisclosureIntro=Pin;}
    InstanceId=Id;ReturnFocus=Source;bPinned=Pin;
    if(Changed||ModeChanged||!IsVisible())At=Anchor;
    if(Changed){Expanded.Reset();Signature.Empty();IconKey.Empty();}
    if(ModeChanged)Signature.Empty();
    const float NewScale=ColdSteelUI::PixelScale(this);
    const float Width=FMath::Min(Pin?520.f:400.f,FMath::Max(1.f,float(UWidgetLayoutLibrary::GetViewportSize(this).X)-24.f));
    if(!FMath::IsNearlyEqual(NewScale,Scale)||!FMath::IsNearlyEqual(Width,WidthPixels))Signature.Empty();
    Scale=NewScale;WidthPixels=Width;
    SetVisibility(Pin?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::HitTestInvisible);
    Refresh();
    if(Changed&&Vertical)Vertical->SetScrollOffset(0);
    FitAndPlace(Changed);
    if(Pin)SetKeyboardFocus();
}
const FColdSteelItem* UColdSteelItemTooltip::DisplayedItem() const
{
    if(PreviewInstance.IsSet())return &PreviewInstance->Item;
    return Model?Model->FindItem(InstanceId):nullptr;
}
void UColdSteelItemTooltip::ProfileChanged()
{
    // A preview's owner supplies the updated instance when it refreshes its list.
    if(!PreviewInstance.IsSet())Refresh();
}
void UColdSteelItemTooltip::Refresh()
{
    if(!IsVisible()||!Model)return;
    const auto* Item=DisplayedItem();
    if(!Item||Item->Place==2){Hide(true);return;}
    Presentation=BuildColdSteelItemTooltip(*Item,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>(),PreviewInstance.IsSet()?PreviewInstance->Location:FString());
    FoodRefreshSeconds=0;
    const FString Next=StructureSignature();
    if(Next!=Signature){Signature=Next;BuildCards();}
    UpdateRows();RefreshIcon();SettleSeconds=.15f;
}
void UColdSteelItemTooltip::OnWeaponIconReady(const FString& Recipe)
{
    if (!IsVisible() || !Model || !WeaponIcons) return;
    const auto* Item = DisplayedItem();
    if (Item && WeaponIcons->Supports(*Item) && WeaponIcons->Key(*Item) == Recipe) RefreshIcon();
}
void UColdSteelItemTooltip::RefreshIcon()
{
    if(!IsVisible()||!Icon||!Model)return;
    const auto* Item=DisplayedItem();if(!Item)return;
    const bool Live=WeaponIcons&&WeaponIcons->Supports(*Item);
    const FString Key=Live?WeaponIcons->Key(*Item):Presentation.Icon;
    if(IconKey!=Key){IconKey=Key;if(Live)WeaponIcons->Request(*Item);}
    if(Live)if(const auto* Brush=WeaponIcons->Find(*Item))
    {
        if(Icon->GetBrush().GetResourceObject()!=Brush->GetResourceObject())Icon->SetBrush(*Brush);
        Icon->SetVisibility(ESlateVisibility::HitTestInvisible);MissingIcon->SetVisibility(ESlateVisibility::Collapsed);return;
    }
    FString CatalogName=Item->Definition;
    if(Live&&Item->Definition==M249WeaponAssets::Definition)
    {
        const auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        const FString Variant=UColdSteelWeaponIcons::CatalogVariantIcon(Item->Definition,Guns->Installed(*Item));
        if(!Variant.IsEmpty())CatalogName=Variant;
    }
    const FString Path=Live?TEXT("Icons/")+CatalogName+TEXT(".png"):Presentation.Icon;
    if(!Path.IsEmpty()&&!TextureCache.Contains(Path))
        TextureCache.Add(Path,FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path));
    UTexture2D* Texture=TextureCache.FindRef(Path);
    if(Icon->GetBrush().GetResourceObject()!=Texture)Icon->SetBrushFromTexture(Texture,true);
    Icon->SetVisibility(Texture?ESlateVisibility::HitTestInvisible:ESlateVisibility::Hidden);
    // 缺正式图时按目录字形兜底（弹药 ▥、背包 包等）；连字形都没有才显示 ?。
    const FString Glyph=ColdSteelInventory::Text(*Item,TEXT("icon_fallback"));
    MissingIcon->SetText(FText::FromString(Glyph.IsEmpty()?TEXT("?"):Glyph));
    MissingIcon->SetVisibility(Texture?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
}
void UColdSteelItemTooltip::FitAndPlace(bool)
{
    if(!Cards||!Header)return;
    const FVector2D View=UWidgetLayoutLibrary::GetViewportSize(this)/Scale;LastViewport=View;
    Frame->SetWidthOverride(WidthPixels/Scale);RootColumn->ForceLayoutPrepass();
    const float Fixed=Header->GetDesiredSize().Y+FooterFrame->GetDesiredSize().Y+12/Scale;
    const bool Locked=bPinned&&bPlacementLocked;
    FVector2D Point=PlacedAt;
    if(Locked)
    {
        Point.X=FMath::Clamp(Point.X,12/Scale,FMath::Max(12.f/Scale,float(View.X-WidthPixels/Scale-12/Scale)));
        Point.Y=FMath::Clamp(Point.Y,12/Scale,FMath::Max(12.f/Scale,float(View.Y-Fixed-1-12/Scale)));
    }
    const float Available=FMath::Max(1.f,float(View.Y)-(Locked?float(Point.Y)+12/Scale:24/Scale));
    const float Natural=Cards->GetDesiredSize().Y;
    const float Body=FMath::Max(1.f,FMath::Min(Natural,Available-Fixed));
    BodyHeight->SetHeightOverride(Body);
    bHorizontalOverflow=false;bVerticalOverflow=Natural>Body+.5f;
    Vertical->SetScrollBarVisibility(bVerticalOverflow?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    Size=FVector2D(WidthPixels/Scale,FMath::Min(Available,Fixed+Body));Frame->SetHeightOverride(Size.Y);
    if(!Locked)
    {
        Point=FVector2D(At.X-Size.X-10/Scale,At.Y+10/Scale);
        if(Point.X<12/Scale)Point.X=At.X+10/Scale;
        if(Point.Y+Size.Y>View.Y-12/Scale)Point.Y=At.Y-Size.Y-10/Scale;
        Point.X=FMath::Clamp(Point.X,12/Scale,FMath::Max(12.f/Scale,float(View.X-Size.X-12/Scale)));
        Point.Y=FMath::Clamp(Point.Y,12/Scale,FMath::Max(12.f/Scale,float(View.Y-Size.Y-12/Scale)));
    }
    PlacedAt=Point;bPlacementLocked=bPinned;
    if(auto* CanvasSlot=Cast<UCanvasPanelSlot>(Slot)){CanvasSlot->SetPosition(Point);CanvasSlot->SetSize(Size);}
}
void UColdSteelItemTooltip::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);if(!IsVisible())return;
    if(Presentation.HasLifetimeBar())
    {
        FoodRefreshSeconds+=Delta;
        if(FoodRefreshSeconds>=1.f)
        {
            FoodRefreshSeconds=0;
            if(const auto* Item=DisplayedItem())
            {
                RefreshColdSteelFoodTooltip(*Item,Model,Presentation);
                UpdateRows();
            }
        }
    }
    const float NewScale=ColdSteelUI::PixelScale(this);
    const FVector2D Pixels=UWidgetLayoutLibrary::GetViewportSize(this);
    const float Width=FMath::Min(bPinned?520.f:400.f,FMath::Max(1.f,float(Pixels.X)-24.f));
    if(!FMath::IsNearlyEqual(NewScale,Scale)||!FMath::IsNearlyEqual(Width,WidthPixels))
    {
        At*=Scale/NewScale;PlacedAt*=Scale/NewScale;Scale=NewScale;WidthPixels=Width;BuildCards();UpdateRows();RefreshIcon();SettleSeconds=.15f;
    }
    if(SettleSeconds>0||!LastViewport.Equals(Pixels/Scale))
    {SettleSeconds=FMath::Max(0.f,SettleSeconds-Delta);FitAndPlace(false);}
}
void UColdSteelItemTooltip::Hide(bool Force)
{
    if(IsPinned()&&!Force)return;
    const bool Restore=HasKeyboardFocus()||HasFocusedDescendants();bPinned=false;
    PreviewInstance.Reset();
    SetVisibility(ESlateVisibility::Collapsed);
    if(Restore&&ReturnFocus.IsValid())ReturnFocus->SetKeyboardFocus();
}
void UColdSteelItemTooltip::CloseClicked(){Hide(true);if(ReturnFocus.IsValid())ReturnFocus->SetKeyboardFocus();}
void UColdSteelItemTooltip::ShowEnhancementDetails()
{
    if(UExpandableArea* Details=Sections.FindRef(TEXT("main:details")))
    {
        Details->SetIsExpanded(true);
        Vertical->ScrollWidgetIntoView(EnhancementTarget ? EnhancementTarget.Get() : Details,false,EDescendantScrollDestination::TopOrLeft);
        SettleSeconds=.3f;
    }
}
void UColdSteelItemTooltip::ExpansionChanged(UExpandableArea* Area,bool Open)
{
    for(const auto& Pair:Sections)if(Pair.Value==Area){Expanded.Add(Pair.Key,Open);if(auto Arrow=Disclosures.FindRef(Pair.Key))Arrow->SetExpanded(Open);break;}
    SettleSeconds=.3f;
}
void UColdSteelItemTooltip::ScrollToSideCards()
{
    UExpandableArea* First=nullptr;
    for(const auto& Pair:Sections)if(Pair.Key.StartsWith(TEXT("extra:")))
    {Pair.Value->SetIsExpanded(true);Expanded.Add(Pair.Key,true);if(!First)First=Pair.Value;}
    if(First)Vertical->ScrollWidgetIntoView(First,false);SettleSeconds=.15f;
}
FReply UColdSteelItemTooltip::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape){CloseClicked();return FReply::Handled();}
    if(E.GetKey()==EKeys::Up||E.GetKey()==EKeys::Down){Vertical->SetScrollOffset(FMath::Max(0.f,Vertical->GetScrollOffset()+(E.GetKey()==EKeys::Up?-80:80)/Scale));return FReply::Handled();}
    if(E.GetKey()==EKeys::PageUp||E.GetKey()==EKeys::PageDown){Vertical->SetScrollOffset(FMath::Max(0.f,Vertical->GetScrollOffset()+(E.GetKey()==EKeys::PageUp?-1:1)*BodyHeight->GetHeightOverride()));return FReply::Handled();}
    if(E.GetKey()==EKeys::Home){Vertical->ScrollToStart();return FReply::Handled();}
    if(E.GetKey()==EKeys::End){Vertical->ScrollToEnd();return FReply::Handled();}
    return Super::NativeOnKeyDown(G,E);
}
