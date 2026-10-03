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
// 正式规则 §4（2026-09-28 复核修复）：UI 文字一律走共享字体入口（Noto Sans SC / JetBrains Mono），
// 不再直载 C:/Windows 的 SimHei。本面板包在 SDPIScaler(1/ViewportScale) 里保持 CSS 像素版面，
// 字体点数只乘 0.75、不再除 PixelScale——子树内视口缩放已被中和，再除会双重缩小。
FSlateFontInfo UiText(float Pixels){return ColdSteelUI::TextFont(Pixels*.75f);}
FSlateFontInfo UiNumber(float Pixels,bool Medium=false){return ColdSteelUI::NumberFont(Pixels*.75f,Medium);}
// buff 图标是目录 emoji 字段（status_effects.json 的 icon，如 💫🛡️），Noto 无 emoji 字形；
// 工程尚无打包 emoji 字体，暂以系统 Segoe UI Emoji 作图标字形回退——待补充打包字体后仅改此处。
FSlateFontInfo EmojiIcon(float Pixels)
{static auto Font=MakeShared<FCompositeFont>(TEXT("Regular"),TEXT("C:/Windows/Fonts/seguiemj.ttf"),EFontHinting::Auto,EFontLoadingPolicy::LazyLoad);return FSlateFontInfo(Font,Pixels*.75f);}
UCanvasPanelSlot* At(UCanvasPanel* Canvas,UWidget* Widget,FVector2D Position,FVector2D Size)
{auto* Slot=Canvas->AddChildToCanvas(Widget);Slot->SetPosition(Position);Slot->SetSize(Size);return Slot;}
}
void UStatusEffectTile::NativeOnInitialized()
{
 Super::NativeOnInitialized();SetIsFocusable(false);SetVisibility(ESlateVisibility::Visible);
 Surface=WidgetTree->ConstructWidget<UBorder>();WidgetTree->RootWidget=Surface;Surface->SetPadding(FMargin(0));Surface->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
 auto* Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();Surface->SetContent(Canvas);
 Icon=WidgetTree->ConstructWidget<UTextBlock>();Icon->SetFont(EmojiIcon(22));Icon->SetJustification(ETextJustify::Center);Icon->SetColorAndOpacity(FLinearColor::White);At(Canvas,Icon,{0,2},{54,28});
 StackText=WidgetTree->ConstructWidget<UTextBlock>();StackText->SetFont(UiNumber(11,true));StackText->SetColorAndOpacity(ColdSteelUI::TextPrimary);At(Canvas,StackText,{4,30},{26,11});
 TimeText=WidgetTree->ConstructWidget<UTextBlock>();TimeText->SetFont(UiNumber(11));TimeText->SetColorAndOpacity(ColdSteelUI::TextSecondary);TimeText->SetJustification(ETextJustify::Right);At(Canvas,TimeText,{20,30},{30,11});
 Progress=WidgetTree->ConstructWidget<UImage>();At(Canvas,Progress,{2,40},{50,2});
 for(auto* W:{static_cast<UWidget*>(Icon),static_cast<UWidget*>(StackText),static_cast<UWidget*>(TimeText),static_cast<UWidget*>(Progress)})W->SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UStatusEffectTile::Update(const FStatusEffectView& V)
{
 View=V;Surface->SetBrush(ColdSteelUI::RoundedBrush(Hover?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,7,Hover?ColdSteelUI::Accent:V.Color,2));
 Icon->SetText(FText::FromString(V.Icon));StackText->SetText(FText::FromString(V.Stacks>=0?FString::Printf(TEXT("×%d"),V.Stacks):TEXT("")));TimeText->SetText(FText::FromString(V.TimeText()));
 // Five-character mm:ss uses the unused stack space on the non-stacking fountain blessing.
 auto* TimeSlot=CastChecked<UCanvasPanelSlot>(TimeText->Slot);const bool IsFountain=V.Type==TEXT("fountainBlessing");
 TimeSlot->SetPosition({IsFountain?6.:20.,30});TimeSlot->SetSize({IsFountain?44.:30.,11});
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
 // 状态详情浮窗走 §2 的深色 Tooltip 底（原浅色 F8F8F8 与 HUD 玻璃语言冲突），8px 圆角 1px 细边。
 Tooltip=WidgetTree->ConstructWidget<UBorder>();Tooltip->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Tooltip,8,ColdSteelUI::Border,1));Tooltip->SetPadding(FMargin(16,12));
 auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Tooltip->SetContent(Column);
 auto Text=[&](float Size,const FLinearColor& Color){auto* W=WidgetTree->ConstructWidget<UTextBlock>();W->SetFont(UiText(Size));W->SetColorAndOpacity(Color);W->SetAutoWrapText(true);Column->AddChildToVerticalBox(W)->SetPadding(FMargin(0,0,0,6));return W;};
 TipTitle=Text(16,ColdSteelUI::TextPrimary);TipDescription=Text(14,ColdSteelUI::TextSecondary);TipStacks=Text(14,ColdSteelUI::Accent);TipTime=Text(12,ColdSteelUI::TextTertiary);
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
 if(V.Type==TEXT("fountainBlessing"))TipTime->SetText(FText::FromString(TEXT("剩余 ")+V.TimeText()+TEXT(" · 总时长 12 分钟")));
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
