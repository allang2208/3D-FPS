#include "StatusEffectsHUD.h"
#include "StatusEffectIconPainter.h"
#include "ColdSteelMeterPresentation.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDLayout.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/SizeBox.h"
#include "Components/ScrollBox.h"
#include "Components/WrapBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Rendering/DrawElementTypes.h"

namespace
{
constexpr float TileWidth=72.f,TileHeight=82.f,TileGap=8.f,ScrollGutter=6.f;
// This subtree cancels viewport DPI: use physical px and only convert font px to points.
FSlateFontInfo UiText(float Pixels){return ColdSteelUI::TextFont(Pixels*.75f);}
FSlateFontInfo UiNumber(float Pixels,bool Medium=false){return ColdSteelUI::NumberFont(Pixels*.75f,Medium);}
// Tribute icons retain their existing catalogue glyphs and existing font path.
FSlateFontInfo TributeIcon(float Pixels)
{static auto Font=MakeShared<FCompositeFont>(TEXT("Regular"),TEXT("C:/Windows/Fonts/seguiemj.ttf"),EFontHinting::Auto,EFontLoadingPolicy::LazyLoad);return FSlateFontInfo(Font,Pixels*.75f);}
UCanvasPanelSlot* At(UCanvasPanel* Canvas,UWidget* Widget,FVector2D Position,FVector2D Size)
{auto* Slot=Canvas->AddChildToCanvas(Widget);Slot->SetPosition(Position);Slot->SetSize(Size);return Slot;}
void SetText(UTextBlock* Label,const FString& Value)
{const auto Text=FText::FromString(Value);if(!Label->GetText().EqualTo(Text))Label->SetText(Text);}
FString CompactTime(const FStatusEffectView& V,float Remaining)
{
 if(V.Persistent)return V.DurationText==TEXT("本次地牢")?TEXT("本轮"):TEXT("持续");
 if(V.Battles>=0)return FString::Printf(TEXT("%d场"),V.Battles);
 const int32 Seconds=FMath::CeilToInt(FMath::Max(0.f,Remaining));
 return Seconds>=60?FString::Printf(TEXT("%d:%02d"),Seconds/60,Seconds%60):FString::Printf(TEXT("%ds"),Seconds);
}
}

void UStatusEffectTile::NativeOnInitialized()
{
 Super::NativeOnInitialized();SetIsFocusable(false);SetVisibility(ESlateVisibility::Visible);
 Surface=WidgetTree->ConstructWidget<UBorder>();WidgetTree->RootWidget=Surface;
 Surface->SetPadding(FMargin(0));Surface->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
 auto* Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();Surface->SetContent(Canvas);
 Icon=WidgetTree->ConstructWidget<UTextBlock>();Icon->SetFont(TributeIcon(30));
 Icon->SetJustification(ETextJustify::Center);Icon->SetColorAndOpacity(FLinearColor::White);At(Canvas,Icon,{8,5},{56,36});
 NameText=WidgetTree->ConstructWidget<UTextBlock>();NameText->SetFont(UiText(12));
 NameText->SetColorAndOpacity(ColdSteelUI::TextPrimary);NameText->SetJustification(ETextJustify::Center);
 NameText->SetAutoWrapText(false);NameText->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);At(Canvas,NameText,{5,43},{62,17});
 StackBadge=WidgetTree->ConstructWidget<UBorder>();StackBadge->SetPadding(FMargin(1,0));
 StackBadge->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,4,ColdSteelUI::Border,1));At(Canvas,StackBadge,{49,3},{21,17});
 StackText=WidgetTree->ConstructWidget<UTextBlock>();StackText->SetFont(UiNumber(11,true));
 StackText->SetColorAndOpacity(ColdSteelUI::TextPrimary);StackText->SetJustification(ETextJustify::Center);StackBadge->SetContent(StackText);
 TimeText=WidgetTree->ConstructWidget<UTextBlock>();TimeText->SetFont(UiNumber(12));
 TimeText->SetColorAndOpacity(ColdSteelUI::TextSecondary);TimeText->SetJustification(ETextJustify::Center);At(Canvas,TimeText,{4,60},{64,17});
 for(auto* W:{static_cast<UWidget*>(Icon),static_cast<UWidget*>(NameText),static_cast<UWidget*>(StackBadge),static_cast<UWidget*>(TimeText)})
  W->SetVisibility(ESlateVisibility::HitTestInvisible);
}

bool UStatusEffectTile::IsTimed() const {return !View.Persistent&&View.Battles<0&&View.Duration>0.f;}
float UStatusEffectTile::RemainingAt(double Now) const
{return IsTimed()?FMath::Max(0.f,View.Remaining-float(FMath::Max(0.,Now-SampledAt))):View.Remaining;}
float UStatusEffectTile::ProgressAt(double Now) const
{
 if(!IsTimed())return 0.f;
 const float Exact=FMath::Clamp(RemainingAt(Now)/View.Duration,0.f,1.f);
 if(!bRefilling)return Exact;
 const float T=FMath::Clamp(float((Now-RefillStartedAt)/.18),0.f,1.f),R=1.f-T;
 return FMath::Lerp(RefillFrom,Exact,1.f-R*R*R);
}
void UStatusEffectTile::RefreshAppearance()
{
 Surface->SetBrush(ColdSteelUI::RoundedBrush(Hover?ColdSteelUI::ButtonHover:ColdSteelUI::GlassTint,
  ColdSteelUI::CardRadius,Hover?ColdSteelUI::Accent:ColdSteelUI::Border,1));
}
void UStatusEffectTile::Update(const FStatusEffectView& V)
{
 const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
 const bool SameType=bHasSnapshot&&View.Type==V.Type;
 const float Previous=ProgressAt(Now),PreviousRemaining=RemainingAt(Now);
 const bool Changed=!bHasSnapshot||View.Type!=V.Type||View.Icon!=V.Icon||View.Name!=V.Name||View.Kind!=V.Kind||
  View.Group!=V.Group||View.Color!=V.Color||View.Stacks!=V.Stacks||View.Persistent!=V.Persistent||View.Battles!=V.Battles||View.DurationText!=V.DurationText;
 const bool Refill=SameType&&!V.Persistent&&V.Battles<0&&V.Duration>0.f&&V.Remaining>PreviousRemaining+.15f;
 if(Refill){RefillFrom=Previous;RefillStartedAt=Now;bRefilling=true;}
 else if(!SameType||Now-RefillStartedAt>=.18)bRefilling=false;
 View=V;SampledAt=Now;bHasSnapshot=true;
 if(Changed)
 {
  RefreshAppearance();SetText(NameText,V.Name);
  const bool Tribute=V.Group==TEXT("tribute");
  Icon->SetVisibility(Tribute?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
  if(Tribute)
  {
   SetText(Icon,V.Icon);
   CastChecked<UCanvasPanelSlot>(Icon->Slot)->SetPosition({V.Stacks>=0?0.:8.,5});
  }
  SetText(StackText,V.Stacks>=100?TEXT("99+"):FString::FromInt(V.Stacks));
  StackBadge->SetVisibility(V.Stacks>=0?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
  DisplaySecond=INDEX_NONE;bExpiryWarning=false;TimeText->SetColorAndOpacity(ColdSteelUI::TextSecondary);
  if(!IsTimed())SetText(TimeText,CompactTime(View,View.Remaining));
  if(const auto Widget=GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Paint);
 }
 TickCountdown(Now);
}
void UStatusEffectTile::TickCountdown(double Now)
{
 if(!IsTimed())return;
 const float Remaining=RemainingAt(Now);
 const int32 Second=FMath::CeilToInt(Remaining);
 if(DisplaySecond!=Second){DisplaySecond=Second;SetText(TimeText,CompactTime(View,Remaining));}
 const bool Expiring=View.Kind!=TEXT("debuff")&&Remaining<=FMath::Min(3.f,View.Duration*.2f);
 if(Expiring!=bExpiryWarning){bExpiryWarning=Expiring;TimeText->SetColorAndOpacity(Expiring?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);}
 if(LastPaintTime!=Now)
 {
  LastPaintTime=Now;
  if(const auto Widget=GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Paint);
 }
}
int32 UStatusEffectTile::NativePaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Clip,
 FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
 int32 Result=Super::NativePaint(Args,G,Clip,Out,Layer,Style,Enabled);
 const auto Tint=Style.GetColorAndOpacityTint();
 if(View.Group!=TEXT("tribute"))Result=ColdSteelUI::PaintStatusEffectIcon(G,Out,Result+1,{View.Stacks>=0?10.:19.,6},34,View,Tint);
 if(IsTimed())
 {
  const double Now=GetWorld()?GetWorld()->GetTimeSeconds():SampledAt;
  const auto Fill=FMath::Lerp(View.Color,ColdSteelUI::TextPrimary,.25f);
  auto Deep=View.Color*.45f;Deep.A=1.f;
  Result=ColdSteelUI::PaintResourceMeter(G,Out,Result+1,{5,76},{62,4},ProgressAt(Now),Fill,Deep,ColdSteelUI::Border,Tint);
 }
 return Result;
}
void UStatusEffectTile::NativeOnMouseEnter(const FGeometry& G,const FPointerEvent& E)
{Super::NativeOnMouseEnter(G,E);Hover=true;RefreshAppearance();if(HUD.IsValid())HUD->ShowTip(this);}
void UStatusEffectTile::NativeOnMouseLeave(const FPointerEvent& E)
{Super::NativeOnMouseLeave(E);Hover=false;RefreshAppearance();}

void UStatusEffectsHUD::NativeOnInitialized()
{
 Super::NativeOnInitialized();SetIsFocusable(false);SetVisibility(ESlateVisibility::SelfHitTestInvisible);
 Root=WidgetTree->ConstructWidget<UCanvasPanel>();Root->SetVisibility(ESlateVisibility::SelfHitTestInvisible);WidgetTree->RootWidget=Root;
 Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetScrollbarThickness({4,4});Scroll->SetScrollbarPadding(FMargin(2,0,0,0));
 Scroll->SetAllowOverscroll(false);Scroll->SetClipping(EWidgetClipping::ClipToBounds);At(Root,Scroll,{12,12},{398,172});
 Wrap=WidgetTree->ConstructWidget<UWrapBox>();Wrap->SetExplicitWrapSize(true);Wrap->SetWrapSize(392);Wrap->SetInnerSlotPadding({TileGap,TileGap});Scroll->AddChild(Wrap);
 Tooltip=WidgetTree->ConstructWidget<UBorder>();Tooltip->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Tooltip,8,ColdSteelUI::Border,1));Tooltip->SetPadding(FMargin(14,12));
 TipSize=WidgetTree->ConstructWidget<USizeBox>();TipSize->SetWidthOverride(292);TipSize->SetMaxDesiredHeight(320);Tooltip->SetContent(TipSize);
 TipScroll=WidgetTree->ConstructWidget<UScrollBox>();TipScroll->SetAllowOverscroll(false);TipScroll->SetScrollbarThickness({4,4});TipScroll->SetClipping(EWidgetClipping::ClipToBounds);TipSize->SetContent(TipScroll);
 auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();TipScroll->AddChild(Column);
 auto Text=[&](float Size,const FLinearColor& Color){auto* W=WidgetTree->ConstructWidget<UTextBlock>();W->SetFont(UiText(Size));W->SetColorAndOpacity(Color);W->SetAutoWrapText(true);Column->AddChildToVerticalBox(W)->SetPadding(FMargin(0,0,0,6));return W;};
 TipTitle=Text(16,ColdSteelUI::TextPrimary);TipDescription=Text(14,ColdSteelUI::TextSecondary);TipStacks=Text(12,ColdSteelUI::TextSecondary);TipTime=Text(12,ColdSteelUI::HUDGoldLight);
 auto* TipSlot=At(Root,Tooltip,{12,102},{320,160});TipSlot->SetAutoSize(true);TipSlot->SetZOrder(2);
 Tooltip->SetVisibility(ESlateVisibility::Collapsed);Scroll->SetVisibility(ESlateVisibility::Collapsed);
}
TSharedRef<SWidget> UStatusEffectsHUD::RebuildWidget()
{
 return SNew(SDPIScaler).DPIScale_Lambda([this](){return 1.f/FMath::Max(.1f,UWidgetLayoutLibrary::GetViewportScale(this));})[Super::RebuildWidget()];
}
void UStatusEffectsHUD::BindPawn(APawn* Pawn)
{
 if(Source.IsValid())Source->OnChanged.Remove(Changed);
 Changed.Reset();HideTip();Source=UStatusEffectsComponent::GetOrCreate(Pawn);
 if(Source.IsValid())Changed=Source->OnChanged.AddUObject(this,&ThisClass::Refresh);
 Wrap->ClearChildren();Tiles.Reset();LayoutEffectCount=INDEX_NONE;Clock=0;Refresh();
}
void UStatusEffectsHUD::NativeDestruct()
{
 if(Source.IsValid())Source->OnChanged.Remove(Changed);
 Changed.Reset();Source.Reset();HideTip();Tiles.Reset();Super::NativeDestruct();
}
void UStatusEffectsHUD::Refresh()
{
 const auto Effects=Source.IsValid()?Source->Snapshot():TArray<FStatusEffectView>();
 bool Reflow=Effects.Num()!=Tiles.Num();
 if(!Reflow)for(int32 I=0;I<Effects.Num();++I)Reflow|=Effects[I].Type!=Tiles[I]->View.Type;
 if(Reflow)
 {
  const float OldOffset=Scroll->GetScrollOffset();
  TArray<TObjectPtr<UStatusEffectTile>> NextTiles;
  TArray<TObjectPtr<USizeBox>> Sizes;
  for(const auto& V:Effects)
  {
   auto* Tile=TileFor(V.Type);USizeBox* Size=Tile?Cast<USizeBox>(Tile->GetParent()):nullptr;
   if(!Tile){Tile=CreateWidget<UStatusEffectTile>(GetOwningPlayer());Tile->HUD=this;}
   if(!Size){Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetWidthOverride(TileWidth);Size->SetHeightOverride(TileHeight);Size->SetContent(Tile);}
   NextTiles.Add(Tile);Sizes.Add(Size);
  }
  if(HoverTile.IsValid()&&!NextTiles.Contains(HoverTile.Get()))HideTip();
  Wrap->ClearChildren();Tiles=MoveTemp(NextTiles);
  for(auto& Size:Sizes)Wrap->AddChildToWrapBox(Size);
  Scroll->SetScrollOffset(OldOffset);LayoutEffectCount=INDEX_NONE;
 }
 for(int32 I=0;I<Effects.Num();++I)Tiles[I]->Update(Effects[I]);
 Scroll->SetVisibility(Effects.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
 UpdateLayout();if(HoverTile.IsValid())ShowTip(HoverTile.Get());
}
void UStatusEffectsHUD::UpdateLayout()
{
 if(!Root||!Scroll)return;
 FVector2D Viewport=Root->GetCachedGeometry().GetLocalSize();
 if(Viewport.X<100||Viewport.Y<100)Viewport=UWidgetLayoutLibrary::GetViewportSize(this);
 if(Viewport.X<100||Viewport.Y<100)return;
 if(LayoutViewport.Equals(Viewport,.1)&&LayoutEffectCount==Tiles.Num())return;
 LayoutViewport=Viewport;LayoutEffectCount=Tiles.Num();
 const FColdSteelHUDLayout Main(Viewport.X);
 const float LeftLane=(Viewport.X-Main.CompassWidth)*.5f-24.f;
 const float TopLane=Main.EventLeft-24.f;
 float Available=FMath::Min(398.f,LeftLane),Top=12.f;
 int32 MaxRows=2;
 if(Available<TileWidth+ScrollGutter)
 {
  Available=FMath::Min(398.f,TopLane);MaxRows=1;
  if(Available<TileWidth+ScrollGutter)
  {
   // The clocks own the narrow top row. Put a slim strip below the compass instead.
   Top=Main.CompassTop+48.f;Available=TileWidth+ScrollGutter;
  }
 }
 const int32 Columns=FMath::Clamp(FMath::FloorToInt((Available-ScrollGutter+TileGap)/(TileWidth+TileGap)),1,5);
 const int32 UsedColumns=FMath::Min(Columns,FMath::Max(1,Tiles.Num()));
 const int32 Rows=FMath::DivideAndRoundUp(Tiles.Num(),Columns);
 MaxRows=FMath::Max(1,FMath::Min(MaxRows,FMath::FloorToInt((Viewport.Y-Top-24+TileGap)/(TileHeight+TileGap))));
 const int32 VisibleRows=FMath::Min(FMath::Max(1,Rows),MaxRows);
 const float Width=UsedColumns*TileWidth+(UsedColumns-1)*TileGap;
 Wrap->SetWrapSize(Width);
 auto* Slot=CastChecked<UCanvasPanelSlot>(Scroll->Slot);Slot->SetPosition({12,Top});Slot->SetSize({Width+ScrollGutter,VisibleRows*TileHeight+(VisibleRows-1)*TileGap});
 Scroll->SetScrollBarVisibility(Rows>MaxRows?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
}
void UStatusEffectsHUD::NativeTick(const FGeometry& G,float Dt)
{
 Super::NativeTick(G,Dt);UpdateLayout();Clock+=Dt;
 if(Clock>=.1f){Clock=0;if(!Tiles.IsEmpty())Refresh();}
 const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
 for(auto& Tile:Tiles)Tile->TickCountdown(Now);
 if(HoverTile.IsValid())
 {
  if(!GetOwningPlayer()||!GetOwningPlayer()->bShowMouseCursor){HideTip();return;}
  // Give the pointer time to cross the small gap into the scrollable details.
  if(HoverTile->IsHovered()||Tooltip->IsHovered())TipLeaveTime=0;else TipLeaveTime+=Dt;
  if(TipLeaveTime>.18f)HideTip();else PositionTip();
 }
}
void UStatusEffectsHUD::ShowTip(UStatusEffectTile* Tile)
{
 if(!Tile)return;
 if(HoverTile.Get()!=Tile){TipLeaveTime=0;TipScroll->SetScrollOffset(0);}
 HoverTile=Tile;const auto& V=Tile->View;
 SetText(TipTitle,V.Name);SetText(TipDescription,V.Description);
 SetText(TipStacks,V.Stacks>=0?FString::Printf(TEXT("层数／次数：×%d"),V.Stacks):TEXT(""));
 TipStacks->SetVisibility(V.Stacks>=0?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
 const FString Duration=V.Persistent?(V.DurationText.IsEmpty()?TEXT("持续至来源结束"):V.DurationText):
  V.Battles>=0?FString::Printf(TEXT("剩余 %d 场"),V.Battles):FString::Printf(TEXT("剩余 %s · 总时长 %.0f 秒"),*CompactTime(V,V.Remaining),V.Duration);
 SetText(TipTime,Duration);Tooltip->SetVisibility(ESlateVisibility::Visible);PositionTip();
}
void UStatusEffectsHUD::PositionTip()
{
 if(!HoverTile.IsValid()||!Root||!Tooltip)return;
 const auto& RootGeometry=Root->GetCachedGeometry();const FVector2D Viewport=RootGeometry.GetLocalSize();
 if(Viewport.X<1||Viewport.Y<1)return;
 const float Width=FMath::Max(32.f,FMath::Min(320.f,float(Viewport.X)-24.f));
 TipSize->SetWidthOverride(FMath::Max(4.f,Width-28));TipSize->SetMaxDesiredHeight(FMath::Max(24.f,FMath::Min(320.f,float(Viewport.Y)-48.f)));
 const auto& G=HoverTile->GetCachedGeometry();
 const FVector2D TileAt=RootGeometry.AbsoluteToLocal(G.LocalToAbsolute(FVector2D::ZeroVector));
 const float Height=FMath::Clamp(float(Tooltip->GetDesiredSize().Y),48.f,FMath::Max(48.f,float(Viewport.Y)-24.f));
 FVector2D P(TileAt.X,TileAt.Y+G.GetLocalSize().Y+8);
 if(P.Y+Height>Viewport.Y-12)P.Y=TileAt.Y-Height-8;
 P.X=FMath::Clamp(P.X,12.,FMath::Max(12.,Viewport.X-Width-12));P.Y=FMath::Clamp(P.Y,12.,FMath::Max(12.,Viewport.Y-Height-12));
 CastChecked<UCanvasPanelSlot>(Tooltip->Slot)->SetPosition(P);
}
void UStatusEffectsHUD::HideTip(){HoverTile.Reset();TipLeaveTime=0;if(Tooltip)Tooltip->SetVisibility(ESlateVisibility::Collapsed);}
bool UStatusEffectsHUD::IsTipVisible() const{return Tooltip&&Tooltip->GetVisibility()!=ESlateVisibility::Collapsed;}
FName UStatusEffectsHUD::TooltipType() const{return HoverTile.IsValid()?HoverTile->View.Type:NAME_None;}
FVector2D UStatusEffectsHUD::TooltipPosition() const{return Tooltip?CastChecked<UCanvasPanelSlot>(Tooltip->Slot)->GetPosition():FVector2D::ZeroVector;}
UStatusEffectTile* UStatusEffectsHUD::TileFor(FName Type) const{for(const auto& Tile:Tiles)if(Tile->View.Type==Type)return Tile;return nullptr;}
void UStatusEffectsHUDSubsystem::OnWorldBeginPlay(UWorld& W){Super::OnWorldBeginPlay(W);if(W.IsGameWorld()&&W.GetNetMode()!=NM_DedicatedServer)W.GetTimerManager().SetTimer(Timer,this,&ThisClass::EnsureHUD,.25f,true);}
void UStatusEffectsHUDSubsystem::EnsureHUD()
{
 auto* PC=UGameplayStatics::GetPlayerController(this,0);if(!PC||!PC->IsLocalController())return;
 if(!HUD){HUD=CreateWidget<UStatusEffectsHUD>(PC);HUD->AddToViewport(45);}
 if(BoundPawn.Get()!=PC->GetPawn()){BoundPawn=PC->GetPawn();HUD->BindPawn(BoundPawn.Get());}
}
void UStatusEffectsHUDSubsystem::Deinitialize(){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);if(HUD)HUD->RemoveFromParent();HUD=nullptr;BoundPawn.Reset();Super::Deinitialize();}
