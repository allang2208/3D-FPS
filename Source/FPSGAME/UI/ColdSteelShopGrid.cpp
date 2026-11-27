#include "ColdSteelShopWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelUIAudio.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelStaffIcon.h"
#include "../Weapons/GunsmithSystem.h"
#include "ColdSteelItemReadCache.h"
#include "ColdSteelTooltipFormatPrivate.h"
#include "ColdSteelWeaponText.h"
#include "../Building/ForgingQuality.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/Border.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/SlateRenderer.h"
#include "Rendering/DrawElements.h"
#include "Widgets/SWidget.h"

namespace { constexpr int32 ShopColumns = 18; }

void UColdSteelShopGrid::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);SetClipping(EWidgetClipping::ClipToBounds);
    WeaponIcons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    auto* Surface=WidgetTree->ConstructWidget<UBorder>();Surface->SetBrushColor(FLinearColor::Transparent);
    Surface->SetPadding(FMargin(0));WidgetTree->RootWidget=Surface;
}
void UColdSteelShopGrid::NativeConstruct()
{
    Super::NativeConstruct();
    if(WeaponIcons&&!IconHandle.IsValid())
        IconHandle=WeaponIcons->OnReady.AddUObject(this,&ThisClass::OnIconReady);
}
void UColdSteelShopGrid::NativeDestruct()
{
    if(Shop&&Shop->TooltipHUD())Shop->TooltipHUD()->HideItemTooltip(true,this);
    ClearHover();
    if(WeaponIcons)WeaponIcons->OnReady.Remove(IconHandle);
    IconHandle.Reset();
    Super::NativeDestruct();
}
void UColdSteelShopGrid::Configure(UColdSteelShopWidget* Owner,bool Sale){Shop=Owner;bSale=Sale;}
void UColdSteelShopGrid::InvalidateGridPaint(){if(auto Widget=GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Paint);}
void UColdSteelShopGrid::ResetPage(){Page=0;Selected.Empty();ClearHover();InvalidateGridPaint();}
void UColdSteelShopGrid::SetItems(const TArray<FColdSteelShopSaleLine>& Items)
{
    // Rebuild presentation only on model changes, never in Paint / Tick.
    const FString Previous=Selected;Entries.Reset(Items.Num());
    for(const auto& Line:Items)
    {
        auto& Entry=Entries.AddDefaulted_GetRef();Entry.Line=Line;
        Entry.Key=Line.Item.InstanceId;
        Entry.Name=bSale?FString():ColdSteelInventory::Text(Line.Item,TEXT("shop_name"));
        if(Entry.Name.IsEmpty())Entry.Name=ColdSteelInventory::Text(Line.Item,TEXT("name"));
        Entry.Description=Entry.Name;
        if(!bSale)
        {
            const auto Data=ColdSteelItemData::Read(Line.Item.Data);
            if(Data&&Data->HasTypedField<EJson::Object>(TEXT("_forgeQuality")))
            {
                const double Bonus=(ColdSteelForgeQuality::Multiplier(Line.Item)-1.)*100.;
                Entry.Quality=ColdSteelTooltipPrivate::Signed(Bonus,TEXT("%"));
                Entry.Description+=FString::Printf(TEXT(" · %s %s"),ColdSteelWeaponText::ForgeQuality,*Entry.Quality);
            }
        }
        Entry.Description+=FString::Printf(TEXT(" · %lld 灵魂/件"),Line.UnitPrice);
    }
    if(!Entries.ContainsByPredicate([&](const auto& E){return E.Key==Selected;}))Selected.Empty();
    Pack();Shop->GridChanged(bSale,Previous!=Selected);
    if(auto* HUD=Shop->TooltipHUD();HUD&&HUD->IsItemTooltipPinnedFrom(this))
    {
        if(const auto* Line=SelectedLine())ShowItemDetails(*Line,TooltipAnchor,true);
        else HUD->HideItemTooltip(true,this);
    }
}
void UColdSteelShopGrid::NativeTick(const FGeometry& G,float Delta)
{
    Super::NativeTick(G,Delta);
    if(!Size.Equals(G.GetLocalSize(),.5f))
    {Size=G.GetLocalSize();Pack();if(Shop)Shop->GridChanged(bSale);}
    if(Hovered==INDEX_NONE)return;
    if(!IsHovered()||!CanShowHover()){ClearHover();return;}
    if(!bTooltipShown)
    {
        HoverSeconds+=Delta;
        if(HoverSeconds>=.2f&&!Shop->TooltipHUD()->HasPinnedItemTooltip())ShowHoveredItem();
    }
}
void UColdSteelShopGrid::Pack()
{
    const float Cell=FMath::Max(1.f,float(Size.X-24)/ShopColumns);
    Rows=FMath::Max(1,FMath::FloorToInt(FMath::Max(1.f,float(Size.Y)-2)/Cell));
    PageRows.Reset();PageRows.Add(Rows);
    TArray<TBitArray<>> Occupancy;Occupancy.Emplace(false,ShopColumns*Rows);
    for(auto& Entry:Entries)
    {
        const int32 W=FMath::Clamp(Entry.Line.Item.Width,1,ShopColumns),H=FMath::Max(1,Entry.Line.Item.Height);
        bool Placed=false;
        // Tall items receive a fitted page of their own, retaining their real footprint.
        // Ordinary pages still use exactly the backpack cell width and fill all available rows.
        for(int32 P=0;P<Occupancy.Num()&&!Placed;++P)
        {
            if(PageRows[P]!=Rows||H>Rows)continue;
            for(int32 Y=0;Y<=Rows-H&&!Placed;++Y)for(int32 X=0;X<=ShopColumns-W&&!Placed;++X)
            {
                bool Free=true;
                for(int32 DY=0;DY<H&&Free;++DY)for(int32 DX=0;DX<W;++DX)
                    if(Occupancy[P][(Y+DY)*ShopColumns+X+DX]){Free=false;break;}
                if(!Free)continue;
                Entry.Page=P;Entry.Cell=Y*ShopColumns+X;
                for(int32 DY=0;DY<H;++DY)for(int32 DX=0;DX<W;++DX)Occupancy[P][(Y+DY)*ShopColumns+X+DX]=true;
                Placed=true;
            }
        }
        if(!Placed)
        {
            // Reuse the initial empty page when the very first item is tall.
            const bool EmptyFirst=Occupancy.Num()==1&&Occupancy[0].CountSetBits()==0;
            const int32 P=EmptyFirst?0:PageRows.Add(FMath::Max(Rows,H));
            if(EmptyFirst){PageRows[0]=FMath::Max(Rows,H);Occupancy[0].Init(false,ShopColumns*PageRows[0]);}
            else Occupancy.Emplace(false,ShopColumns*PageRows[P]);
            Entry.Page=P;Entry.Cell=0;
            for(int32 Y=0;Y<H;++Y)for(int32 X=0;X<W;++X)Occupancy[P][Y*ShopColumns+X]=true;
        }
    }
    Page=FMath::Clamp(Page,0,PageRows.Num()-1);
    if(IsHovered())UpdateHover(GetCachedGeometry(),FSlateApplication::Get().GetCursorPos(),true);
    else ClearHover();
    PreparePageIcons();
    InvalidateGridPaint();
}
void UColdSteelShopGrid::PreparePageIcons()
{
    if(Size.X<25||Size.Y<3)return;
    TMap<FString,FSlateBrush> VisibleBrushes;
    const auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const auto LoadCatalog=[&](const FString& Path,const FColdSteelItem& Item)
    {
        if(Path.IsEmpty())return false;
        if(const auto* Existing=VisibleBrushes.Find(Path))return Existing->GetResourceObject()!=nullptr;
        auto& Brush=VisibleBrushes.Add(Path);
        if(const auto* Existing=CatalogBrushes.Find(Path))
            Brush=*Existing;
        else if(auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path))
        {
            Brush.SetResourceObject(Texture);
            Brush.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
            Brush.DrawAs=ESlateBrushDrawType::Image;
            if(ColdSteelInventory::IsStaff(Item)||ColdSteelInventory::IsOneHandedMelee(Item)||Item.Definition==TEXT("ue_m870"))
                ColdSteelStaffIcon::FrameImportedTexture(Brush,Texture);
        }
        return Brush.GetResourceObject()!=nullptr;
    };
    for(auto& Entry:Entries)
    {
        if(Entry.Page!=Page)continue;
        const auto& Item=Entry.Line.Item;
        Entry.IconRecipe=WeaponIcons?WeaponIcons->Request(Item):FString();
        if(!Entry.IconRecipe.IsEmpty())
        {
            const FString Variant=Guns?UColdSteelWeaponIcons::CatalogVariantIcon(Item.Definition,Guns->Installed(Item)):FString();
            if(!Variant.IsEmpty())
            {
                Entry.CatalogIcon=TEXT("Icons/")+Variant+TEXT(".png");
                if(LoadCatalog(Entry.CatalogIcon,Item))continue;
            }
            Entry.CatalogIcon=TEXT("Icons/")+Item.Definition+TEXT(".png");
            if(LoadCatalog(Entry.CatalogIcon,Item))continue;
        }
        Entry.CatalogIcon=ColdSteelInventory::Text(Item,TEXT("ue_icon"));
        LoadCatalog(Entry.CatalogIcon,Item);
    }
    CatalogBrushes=MoveTemp(VisibleBrushes);
}
void UColdSteelShopGrid::OnIconReady(const FString& Recipe)
{
    if(Shop&&Shop->ShopModel()->IsOpen()&&Entries.ContainsByPredicate([&](const FEntry& E)
        {return E.Page==Page&&E.IconRecipe==Recipe;}))
        InvalidateGridPaint();
}
void UColdSteelShopGrid::GridGeometry(FVector2D& Origin,float& Cell)const
{
    const int32 Height=PageRows.IsValidIndex(Page)?PageRows[Page]:Rows;
    Cell=FMath::Max(.1f,FMath::Min(float(Size.X-24)/ShopColumns,float(Size.Y-2)/Height));
    Origin=FVector2D((Size.X-ShopColumns*Cell)*.5,1);
}
int32 UColdSteelShopGrid::Hit(const FGeometry& G,FVector2D Screen)const
{
    FVector2D Origin;float Cell;GridGeometry(Origin,Cell);const FVector2D P=G.AbsoluteToLocal(Screen)-Origin;
    if(P.X<0||P.Y<0||P.X>=ShopColumns*Cell||P.Y>=PageRows[Page]*Cell)return INDEX_NONE;
    const int32 X=FMath::FloorToInt(P.X/Cell),Y=FMath::FloorToInt(P.Y/Cell);
    return Entries.IndexOfByPredicate([&](const auto& E){return E.Page==Page&&X>=E.Cell%ShopColumns&&X<E.Cell%ShopColumns+E.Line.Item.Width&&Y>=E.Cell/ShopColumns&&Y<E.Cell/ShopColumns+E.Line.Item.Height;});
}
const FColdSteelShopSaleLine* UColdSteelShopGrid::SelectedLine(FString* Description)const
{
    const auto* Entry=Entries.FindByPredicate([&](const auto& E){return E.Key==Selected&&E.Page==Page;});
    if(Entry&&Description)*Description=Entry->Description;
    return Entry?&Entry->Line:nullptr;
}
void UColdSteelShopGrid::SelectKey(const FString& Key,bool Reveal)
{
    if(const auto* Entry=Entries.FindByPredicate([&](const auto& E){return E.Key==Key;}))
    {
        if(Selected!=Key&&Shop&&Shop->TooltipHUD())Shop->TooltipHUD()->HideItemTooltip(true,this);
        Selected=Key;
        if(Reveal&&Page!=Entry->Page){Page=Entry->Page;ClearHover();PreparePageIcons();}
        InvalidateGridPaint();
        if(Shop)Shop->GridChanged(bSale,true);
    }
}
void UColdSteelShopGrid::TurnPage(int32 Direction,bool Wrap)
{
    if(!Shop||Shop->IsConfirming()||PageRows.Num()<2||Direction==0)return;
    UWidgetBlueprintLibrary::CancelDragDrop();
    const int32 Target=Wrap?(Page+Direction+PageRows.Num())%PageRows.Num():FMath::Clamp(Page+Direction,0,PageRows.Num()-1);
    if(Target==Page)return;
    if(auto* HUD=Shop->TooltipHUD())HUD->HideItemTooltip(true,this);
    Page=Target;PreparePageIcons();Selected.Empty();ClearHover();InvalidateGridPaint();Shop->GridChanged(bSale,true);
    if(IsHovered())UpdateHover(GetCachedGeometry(),FSlateApplication::Get().GetCursorPos());
}
FReply UColdSteelShopGrid::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    if(!Shop||Shop->IsConfirming())return FReply::Handled();
    if(E.GetEffectingButton()!=EKeys::LeftMouseButton&&E.GetEffectingButton()!=EKeys::RightMouseButton)return Super::NativeOnMouseButtonDown(G,E);
    SetKeyboardFocus(); // Commit the previous quantity before changing the selected item.
    if(auto* HUD=Shop->TooltipHUD())HUD->HideItemTooltip(true);
    const int32 Index=Hit(G,E.GetScreenSpacePosition());
    Selected=Entries.IsValidIndex(Index)?Entries[Index].Key:FString();InvalidateGridPaint();Shop->GridChanged(bSale,true);
    if(Index!=INDEX_NONE&&E.GetEffectingButton()==EKeys::RightMouseButton){ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::Button);Shop->ActivateGridItem(bSale);}
    else if(Index!=INDEX_NONE){ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::Slot);ShowItemDetails(Entries[Index].Line,E.GetScreenSpacePosition(),true);}
    return FReply::Handled();
}
FReply UColdSteelShopGrid::NativeOnMouseButtonDoubleClick(const FGeometry& G,const FPointerEvent& E)
{
    if(Shop&&!Shop->IsConfirming()&&E.GetEffectingButton()==EKeys::LeftMouseButton)
    {
        if(auto* HUD=Shop->TooltipHUD())HUD->HideItemTooltip(true);
        const int32 Index=Hit(G,E.GetScreenSpacePosition());
        if(Index!=INDEX_NONE){ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::Button);SelectKey(Entries[Index].Key,false);Shop->ActivateGridItem(bSale);}
        return FReply::Handled();
    }
    return Super::NativeOnMouseButtonDoubleClick(G,E);
}
FReply UColdSteelShopGrid::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::F1&&CanShowHover())
    {
        if(const auto* Line=SelectedLine())
        {
            ShowItemDetails(*Line,G.LocalToAbsolute(G.GetLocalSize()*.5f),true);
            Shop->TooltipHUD()->FocusItemTooltip();
        }
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(G,E);
}
bool UColdSteelShopGrid::CanShowHover() const
{
    return Shop&&Shop->TooltipHUD()&&Shop->TooltipHUD()->IsShopOpen()&&Shop->GetVisibility()==ESlateVisibility::Visible
        &&!Shop->IsConfirming()&&!FSlateApplication::Get().IsDragDropping();
}
void UColdSteelShopGrid::ClearHover()
{
    if(Hovered==INDEX_NONE)return;
    if(Shop&&Shop->TooltipHUD())Shop->TooltipHUD()->HideItemTooltip(false,this);
    Hovered=INDEX_NONE;HoveredKey.Reset();HoverSeconds=0.f;bTooltipShown=false;
    InvalidateGridPaint();
}
void UColdSteelShopGrid::UpdateHover(const FGeometry& G,FVector2D ScreenPosition,bool RefreshItem)
{
    if(!CanShowHover()){ClearHover();return;}
    const int32 Index=Hit(G,ScreenPosition);
    if(!Entries.IsValidIndex(Index)){ClearHover();return;}
    const FEntry& Entry=Entries[Index];
    if(Entry.Key!=HoveredKey||Hovered==INDEX_NONE)
    {
        ClearHover();
        Hovered=Index;HoveredKey=Entry.Key;TooltipAnchor=ScreenPosition;
        InvalidateGridPaint();
    }
    else
    {
        Hovered=Index;
        if(RefreshItem&&bTooltipShown)ShowHoveredItem();
    }
}
void UColdSteelShopGrid::ShowHoveredItem()
{
    ShowItemDetails(Entries[Hovered].Line,TooltipAnchor,false);
    bTooltipShown=true;
}
void UColdSteelShopGrid::ShowItemDetails(const FColdSteelShopSaleLine& Line,FVector2D Anchor,bool Pinned)
{
    const FString Location=bSale?FString(TEXT("待售栏")):Shop->ShopModel()->MerchantName()+TEXT("货架");
    const FString Hint=FString::Printf(TEXT("%lld 灵魂/件 · %s"),Line.UnitPrice,bSale?TEXT("右键或双击移出待售栏"):TEXT("右键或双击购买"));
    const FColdSteelItemTooltipPreview Preview{Line.Item,Location,Hint};
    Shop->TooltipHUD()->ShowItemTooltip(Line.Item.InstanceId,Anchor,Pinned,this,&Preview);
}
FReply UColdSteelShopGrid::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E)
{
    UpdateHover(G,E.GetScreenSpacePosition());
    return FReply::Handled();
}
void UColdSteelShopGrid::NativeOnMouseLeave(const FPointerEvent& E){ClearHover();Super::NativeOnMouseLeave(E);}
FReply UColdSteelShopGrid::NativeOnMouseWheel(const FGeometry&,const FPointerEvent& E){TurnPage(E.GetWheelDelta()>0?-1:E.GetWheelDelta()<0?1:0,true);return FReply::Handled();}

int32 UColdSteelShopGrid::NativePaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& C,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled)const
{
    Layer=Super::NativePaint(Args,G,C,Out,Layer,Style,Enabled);if(Size.X<25||Size.Y<3)return Layer;
    FVector2D Origin;float Cell;GridGeometry(Origin,Cell);
    const auto Tint=Style.GetColorAndOpacityTint();
    auto Box=[&](FVector2D P,FVector2D Extent,FLinearColor Fill,FLinearColor Edge=FLinearColor::Transparent,float Radius=0,int32 Z=1)
    {
        if(Extent.X<=0||Extent.Y<=0)return;
        auto Brush=ColdSteelUI::RoundedBrush(Fill,Radius,Edge,Edge.A>0?1:0);
        FSlateDrawElement::MakeBox(Out,Layer+Z,G.ToPaintGeometry(Extent,FSlateLayoutTransform(P)),&Brush,ESlateDrawEffect::None,Fill*Tint);
    };
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    auto Label=[&](FString Caption,FVector2D P,float MaxWidth,bool Numeric,FLinearColor Color)
    {
        if(MaxWidth<=0)return;
        const auto Font=Numeric?ColdSteelUI::NumberFont(9):ColdSteelUI::TextFont(9);
        if(Measure->Measure(Caption,Font).X>MaxWidth)
        {while(!Caption.IsEmpty()&&Measure->Measure(Caption+TEXT("…"),Font).X>MaxWidth)Caption.LeftChopInline(1);Caption+=TEXT("…");}
        FSlateDrawElement::MakeText(Out,Layer+5,G.ToPaintGeometry(FVector2D(MaxWidth,16),FSlateLayoutTransform(P)),Caption,Font,ESlateDrawEffect::None,Color*Tint);
    };
    const FVector2D Extent(ShopColumns*Cell,PageRows[Page]*Cell);
    Box(Origin,Extent,ColdSteelUI::Gray(15,95),ColdSteelUI::Border);
    for(int32 X=1;X<ShopColumns;++X)Box(Origin+FVector2D(X*Cell,0),FVector2D(1,Extent.Y),ColdSteelUI::Gray(220,22));
    for(int32 Y=1;Y<PageRows[Page];++Y)Box(Origin+FVector2D(0,Y*Cell),FVector2D(Extent.X,1),ColdSteelUI::Gray(220,22));
    for(int32 N=0;N<Entries.Num();++N)
    {
        const auto& E=Entries[N];if(E.Page!=Page)continue;
        const auto& Item=E.Line.Item;
        const FVector2D P=Origin+FVector2D(E.Cell%ShopColumns*Cell,E.Cell/ShopColumns*Cell);
        const FVector2D Bounds(Item.Width*Cell,Item.Height*Cell);
        const bool Active=E.Key==Selected,Hover=N==Hovered;
        Box(P+FVector2D(1,1),Bounds-FVector2D(2,2),ColdSteelUI::Gray(Hover?80:55,Hover?175:128),Active?ColdSteelUI::HUDGold:ColdSteelUI::Border,ColdSteelUI::InventoryItemRadius,2);
        for(int32 X=1;X<Item.Width;++X)Box(P+FVector2D(X*Cell,2),FVector2D(1,Bounds.Y-4),ColdSteelUI::Gray(220,10),FLinearColor::Transparent,0,2);
        for(int32 Y=1;Y<Item.Height;++Y)Box(P+FVector2D(2,Y*Cell),FVector2D(Bounds.X-4,1),ColdSteelUI::Gray(220,10),FLinearColor::Transparent,0,2);
        const bool ShowName=Bounds.Y>=48;
        const FSlateBrush* Icon=WeaponIcons&&!E.IconRecipe.IsEmpty()?WeaponIcons->FindRecipe(E.IconRecipe):nullptr;
        if(!Icon)Icon=CatalogBrushes.Find(E.CatalogIcon);
        if(Icon&&Icon->GetResourceObject())
        {
            FVector2D Image=Icon->ImageSize;
            const float AvailableW=FMath::Max(1.,Bounds.X-8),AvailableH=FMath::Max(1.,Bounds.Y-(ShowName?22:8));
            const float Fit=Item.bRotated?FMath::Min(AvailableW/Image.Y,AvailableH/Image.X):FMath::Min(AvailableW/Image.X,AvailableH/Image.Y);
            Image*=Fit;
            const FVector2D Center=P+FVector2D(Bounds.X*.5,ShowName?16+AvailableH*.5:Bounds.Y*.5);
            const auto Paint=G.ToPaintGeometry(Image,FSlateLayoutTransform(Center-Image*.5));
            if(Item.bRotated)FSlateDrawElement::MakeRotatedBox(Out,Layer+3,Paint,Icon,ESlateDrawEffect::None,PI*.5f,TOptional<FVector2f>(),FSlateDrawElement::RelativeToElement,Tint);
            else FSlateDrawElement::MakeBox(Out,Layer+3,Paint,Icon,ESlateDrawEffect::None,Tint);
        }
        if(ShowName)Label(E.Name,P+FVector2D(4,2),Bounds.X-8,false,ColdSteelUI::TextPrimary);
        else if(!Icon||!Icon->GetResourceObject())Label(E.Name,P+FVector2D(4,FMath::Max(2.,Bounds.Y*.5-8)),Bounds.X-8,false,ColdSteelUI::TextPrimary);
        if(!bSale||E.Line.Count>1)
        {
            const FString Count=FString::Printf(TEXT("%lld"),bSale?E.Line.Count:E.Line.UnitPrice);
            const float Width=FMath::Min(float(Bounds.X-4),float(Measure->Measure(Count,ColdSteelUI::NumberFont(9)).X)+6);
            const FVector2D At=P+FVector2D(Bounds.X-Width-2,Bounds.Y-17);
            Box(At,FVector2D(Width,15),ColdSteelUI::Gray(10,220),FLinearColor::Transparent,2,4);
            Label(Count,At+FVector2D(3,0),Width-4,true,bSale?ColdSteelUI::TextPrimary:ColdSteelUI::HUDGoldLight);
            if(!E.Quality.IsEmpty())
            {
                const float QualityWidth=Measure->Measure(E.Quality,ColdSteelUI::NumberFont(9)).X+6;
                if(Bounds.X>=Width+QualityWidth+6)
                {
                    const FVector2D QualityAt(P.X+2,At.Y);
                    Box(QualityAt,FVector2D(QualityWidth,15),ColdSteelUI::Gray(10,220),FLinearColor::Transparent,2,4);
                    Label(E.Quality,QualityAt+FVector2D(3,0),QualityWidth-3,true,ColdSteelUI::TextPrimary);
                }
            }
        }
    }
    if(Entries.IsEmpty())
    {
        const FString Hint=bSale?TEXT("拖入物品，或右键背包物品加入待售栏"):TEXT("暂无可购买的物品");
        const float HintWidth=FMath::Min(float(Extent.X-24),float(Measure->Measure(Hint,ColdSteelUI::TextFont(9)).X));
        const FVector2D At=Origin+FVector2D((Extent.X-HintWidth)*.5,FMath::Max(2.,Extent.Y*.5-8));
        Box(At-FVector2D(8,4),FVector2D(HintWidth+16,24),ColdSteelUI::Content,FLinearColor::Transparent,4,4);
        Label(Hint,At,HintWidth,false,ColdSteelUI::TextSecondary);
    }
    return Layer+6;
}
