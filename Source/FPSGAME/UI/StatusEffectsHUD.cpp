#include "StatusEffectsHUD.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
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
#include "Blueprint/WidgetLayoutLibrary.h"

namespace
{
FLinearColor Hex(const TCHAR* Color){return FLinearColor::FromSRGBColor(FColor::FromHex(Color));}
FSlateFontInfo Chinese(float Pixels)
{static auto Font=MakeShared<FCompositeFont>(TEXT("Regular"),TEXT("C:/Windows/Fonts/simhei.ttf"),EFontHinting::Auto,EFontLoadingPolicy::LazyLoad);return FSlateFontInfo(Font,Pixels*.75f);}
FSlateFontInfo Emoji(float Pixels)
{static auto Font=MakeShared<FCompositeFont>(TEXT("Regular"),TEXT("C:/Windows/Fonts/seguiemj.ttf"),EFontHinting::Auto,EFontLoadingPolicy::LazyLoad);return FSlateFontInfo(Font,Pixels*.75f);}
UCanvasPanelSlot* At(UCanvasPanel* Canvas,UWidget* Widget,FVector2D Position,FVector2D Size)
{auto* Slot=Canvas->AddChildToCanvas(Widget);Slot->SetPosition(Position);Slot->SetSize(Size);return Slot;}
}
void UStatusEffectTile::NativeOnInitialized()
{
 Super::NativeOnInitialized();SetIsFocusable(false);SetVisibility(ESlateVisibility::Visible);
 Surface=WidgetTree->ConstructWidget<UBorder>();WidgetTree->RootWidget=Surface;Surface->SetPadding(FMargin(0));Surface->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
 auto* Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();Surface->SetContent(Canvas);
 Icon=WidgetTree->ConstructWidget<UTextBlock>();Icon->SetFont(Emoji(22));Icon->SetJustification(ETextJustify::Center);Icon->SetColorAndOpacity(FLinearColor::White);At(Canvas,Icon,{0,2},{54,28});
 StackText=WidgetTree->ConstructWidget<UTextBlock>();StackText->SetFont(ColdSteelUI::NumberFont(6.75,true));StackText->SetColorAndOpacity(Hex(TEXT("F0F4F6FF")));At(Canvas,StackText,{4,30},{26,11});
 TimeText=WidgetTree->ConstructWidget<UTextBlock>();TimeText->SetFont(ColdSteelUI::NumberFont(6.75));TimeText->SetColorAndOpacity(Hex(TEXT("C3CDD2FF")));TimeText->SetJustification(ETextJustify::Right);At(Canvas,TimeText,{20,30},{30,11});
 Progress=WidgetTree->ConstructWidget<UImage>();At(Canvas,Progress,{2,40},{50,2});
 for(auto* W:{static_cast<UWidget*>(Icon),static_cast<UWidget*>(StackText),static_cast<UWidget*>(TimeText),static_cast<UWidget*>(Progress)})W->SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UStatusEffectTile::Update(const FStatusEffectView& V)
{
 View=V;Surface->SetBrush(ColdSteelUI::RoundedBrush(Hover?Hex(TEXT("232A30F5")):Hex(TEXT("2A2520D9")),7,Hover?Hex(TEXT("C4D3DAFF")):V.Color,2));
 Icon->SetText(FText::FromString(V.Icon));StackText->SetText(FText::FromString(V.Stacks>=0?FString::Printf(TEXT("×%d"),V.Stacks):TEXT("")));TimeText->SetText(FText::FromString(V.TimeText()));
 const float Ratio=V.Persistent?1.f:V.Battles>=0?0.f:V.Duration>0?FMath::Clamp(V.Remaining/V.Duration,0.f,1.f):0.f;
 CastChecked<UCanvasPanelSlot>(Progress->Slot)->SetSize({50*Ratio,2});Progress->SetColorAndOpacity(V.Color.CopyWithNewOpacity(.7f));
}
void UStatusEffectTile::NativeOnMouseEnter(const FGeometry& G,const FPointerEvent& E){Super::NativeOnMouseEnter(G,E);Hover=true;Update(View);if(HUD.IsValid())HUD->ShowTip(this);}
void UStatusEffectTile::NativeOnMouseLeave(const FPointerEvent& E){Super::NativeOnMouseLeave(E);Hover=false;Update(View);if(HUD.IsValid())HUD->HideTip();}
void UStatusEffectsHUD::NativeOnInitialized()
{
 Super::NativeOnInitialized();SetIsFocusable(false);SetVisibility(ESlateVisibility::SelfHitTestInvisible);
 Root=WidgetTree->ConstructWidget<UCanvasPanel>();Root->SetVisibility(ESlateVisibility::SelfHitTestInvisible);WidgetTree->RootWidget=Root;
 Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetScrollbarThickness({3,3});Scroll->SetScrollbarPadding(FMargin(0));Scroll->SetAllowOverscroll(false);At(Root,Scroll,{104,12},{252,44});
 Wrap=WidgetTree->ConstructWidget<UWrapBox>();Wrap->SetExplicitWrapSize(true);Wrap->SetWrapSize(252);Wrap->SetInnerSlotPadding({12,6});Scroll->AddChild(Wrap);
 Tooltip=WidgetTree->ConstructWidget<UBorder>();Tooltip->SetBrush(ColdSteelUI::RoundedBrush(Hex(TEXT("F8F8F8F2")),8,Hex(TEXT("00000033")),2));Tooltip->SetPadding(FMargin(16,12));
 auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Tooltip->SetContent(Column);
 auto Text=[&](float Size,FLinearColor Color){auto* W=WidgetTree->ConstructWidget<UTextBlock>();W->SetFont(Chinese(Size));W->SetColorAndOpacity(Color);W->SetAutoWrapText(true);Column->AddChildToVerticalBox(W)->SetPadding(FMargin(0,0,0,6));return W;};
 TipTitle=Text(15,Hex(TEXT("2A2520FF")));TipDescription=Text(13,Hex(TEXT("2A2520FF")));TipStacks=Text(13,Hex(TEXT("8A6A3AFF")));TipTime=Text(12,Hex(TEXT("6A5A4AFF")));
 auto* TipSlot=At(Root,Tooltip,{168,12},{260,160});TipSlot->SetZOrder(2);Tooltip->SetVisibility(ESlateVisibility::Collapsed);Scroll->SetVisibility(ESlateVisibility::Collapsed);
}
TSharedRef<SWidget> UStatusEffectsHUD::RebuildWidget()
{
 // The source HTML uses CSS pixels. Preserve its readable card dimensions at
 // 720p as well as 1080p instead of shrinking it through the game's DPI curve.
 return SNew(SDPIScaler).DPIScale_Lambda([this](){return 1.f/FMath::Max(.1f,UWidgetLayoutLibrary::GetViewportScale(this));})[Super::RebuildWidget()];
}
void UStatusEffectsHUD::BindPawn(APawn* Pawn)
{
 if(Source.IsValid())Source->OnChanged.Remove(Changed);Source=UStatusEffectsComponent::GetOrCreate(Pawn);if(Source.IsValid())Changed=Source->OnChanged.AddUObject(this,&ThisClass::Refresh);Refresh();
}
void UStatusEffectsHUD::NativeDestruct(){if(Source.IsValid())Source->OnChanged.Remove(Changed);Source.Reset();HideTip();Super::NativeDestruct();}
void UStatusEffectsHUD::Refresh()
{
 const auto Effects=Source.IsValid()?Source->Snapshot():TArray<FStatusEffectView>();bool Rebuild=Effects.Num()!=Tiles.Num();
 if(!Rebuild)for(int32 I=0;I<Effects.Num();++I)Rebuild|=Effects[I].Type!=Tiles[I]->View.Type;
 if(Rebuild){HideTip();Wrap->ClearChildren();Tiles.Empty();for(const auto& V:Effects){auto* Tile=CreateWidget<UStatusEffectTile>(GetOwningPlayer());Tile->HUD=this;auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetWidthOverride(54);Size->SetHeightOverride(44);Size->SetContent(Tile);Wrap->AddChildToWrapBox(Size);Tiles.Add(Tile);}}
 for(int32 I=0;I<Effects.Num();++I)Tiles[I]->Update(Effects[I]);Scroll->SetScrollBarVisibility(Effects.Num()>4?ESlateVisibility::Visible:ESlateVisibility::Collapsed);Scroll->SetVisibility(Effects.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
 if(HoverTile.IsValid())ShowTip(HoverTile.Get());
}
void UStatusEffectsHUD::NativeTick(const FGeometry& G,float Dt)
{
 Super::NativeTick(G,Dt);Clock+=Dt;if(Clock>=.1f){Clock=0;if(!Tiles.IsEmpty())Refresh();}
 if(HoverTile.IsValid()&&(!GetOwningPlayer()||!GetOwningPlayer()->bShowMouseCursor))HideTip();
}
void UStatusEffectsHUD::ShowTip(UStatusEffectTile* Tile)
{
 if(!Tile)return;HoverTile=Tile;const auto& V=Tile->View;
 TipTitle->SetText(FText::FromString(V.Name));TipDescription->SetText(FText::FromString(V.Description));TipStacks->SetText(FText::FromString(V.Stacks>=0?FString::Printf(TEXT("层数：x%d"),V.Stacks):TEXT("")));TipStacks->SetVisibility(V.Stacks>=0?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
 TipTime->SetText(FText::FromString(V.Persistent?(V.DurationText.IsEmpty()?TEXT("持续至来源结束"):V.DurationText):V.Battles>=0?FString::Printf(TEXT("剩余 %d 场"),V.Battles):FString::Printf(TEXT("剩余 %d 秒"),FMath::CeilToInt(V.Remaining))));
 const float Height=V.Stacks>=0?160:142;const FVector2D Viewport=Root->GetCachedGeometry().GetLocalSize();const auto& G=Tile->GetCachedGeometry();FVector2D P=Root->GetCachedGeometry().AbsoluteToLocal(G.LocalToAbsolute({G.GetLocalSize().X+10,0}));
 if(P.X+260>Viewport.X-8)P.X-=G.GetLocalSize().X+280;P.X=FMath::Clamp(P.X,8.,FMath::Max(8.,Viewport.X-268));P.Y=FMath::Clamp(P.Y,8.,FMath::Max(8.,Viewport.Y-Height-8));auto* TipSlot=CastChecked<UCanvasPanelSlot>(Tooltip->Slot);TipSlot->SetPosition(P);TipSlot->SetSize({260,Height});Tooltip->SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UStatusEffectsHUD::HideTip(){HoverTile.Reset();if(Tooltip)Tooltip->SetVisibility(ESlateVisibility::Collapsed);}
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
