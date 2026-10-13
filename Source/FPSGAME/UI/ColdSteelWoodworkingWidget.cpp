#include "ColdSteelWoodworkingWidget.h"
#include "ColdSteelWoodworkingManagementWidget.h"
#include "ColdSteelHUDWidget.h"
#include "../Building/WoodworkingSawVisualComponent.h"
#include "../Building/WoodworkingWorldView.h"
#include "Engine/World.h"
#include "Widgets/SOverlay.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "Sound/SoundWaveProcedural.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "GunsmithUIStyle.h"
#include "WoodworkingPresentation.h"
#include "../Building/WoodworkingSystem.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "../FPSGAMEPlayerController.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/SlateBlueprintLibrary.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Pawn.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"

class SWoodworkingCanvas : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SWoodworkingCanvas){} SLATE_ARGUMENT(UColdSteelWoodworkingWidget*,Owner) SLATE_END_ARGS()
    void Construct(const FArguments& Args){Owner=Args._Owner;SetClipping(EWidgetClipping::ClipToBounds);Chips.Reserve(WoodworkingPresentation::MaximumChips);}
    virtual FVector2D ComputeDesiredSize(float) const override {return FVector2D(640,420);}
    virtual bool SupportsKeyboardFocus() const override {return true;}
    struct FView {double Fit=1,Scale=1;FVector2D Origin=FVector2D::ZeroVector;};
    FView View(const FGeometry& G) const
    {
        FView V;const auto* S=Owner.IsValid()?Owner->System():nullptr;if(!S)return V;
        const FVector2D WorkSize(S->Settings().Width*1.55,S->Settings().Height*2.9);
        V.Fit=FMath::Max(.01,FMath::Min((G.GetLocalSize().X-24)/WorkSize.X,(G.GetLocalSize().Y-24)/WorkSize.Y));
        V.Scale=V.Fit*Zoom;V.Origin=G.GetLocalSize()*.5+Pan*V.Fit;return V;
    }
    bool WorkPoint(const FGeometry& G,FVector2D Screen,FVector2D& Out) const
    {if(Owner.IsValid()&&Owner->IsWorldMode())return Owner->CursorToWorldWork(Screen,Out);const auto V=View(G);Out=(FVector2D(G.AbsoluteToLocal(Screen))-V.Origin)/V.Scale;return true;}
    bool CanGrab(FVector2D Work) const
    {
        const auto* S=Owner.IsValid()?Owner->System():nullptr;if(!S)return false;
        const auto P=S->WorkToBoard(Work);const int32 W=S->Settings().Width,H=S->Settings().Height;
        const int32 X=FMath::FloorToInt(P.X),Y=FMath::FloorToInt(P.Y);
        return X>=0&&Y>=0&&X<W&&Y<H&&S->Mask().Wood().IsValidIndex(Y*W+X)&&S->Mask().Wood()[Y*W+X];
    }
    void Cancel()
    {
        bDragging=bPanning=false;if(Owner.IsValid()&&Owner->System())Owner->System()->EndStroke();
        if(HasMouseCapture()&&FSlateApplication::IsInitialized())FSlateApplication::Get().ReleaseAllPointerCapture();
    }
    void SetBlocked(bool Blocked){if(Blocked)Cancel();bBlocked=Blocked;}
    void ResetView(){Cancel();Zoom=1;Pan=FVector2D::ZeroVector;if(Owner.IsValid())Owner->ResetWorldCamera();}
    void ClearFeedback(){Chips.Reset();DamageUntil=0;}
    void Rotate(int32 Direction,bool Fine)
    {
        if(bBlocked||!Owner.IsValid()||!Owner->PresentationReady())return;
        auto* S=Owner->System();const uint64 Before=S->Mask().CutSerial();
        S->RotateBoard(Direction,Fine);Contact(Before);
        if(bDragging)GrabLocal=S->WorkToBoard(LastWork);
        Invalidate(EInvalidateWidgetReason::Paint);
    }
    virtual void Tick(const FGeometry& G,double,float Delta) override
    {
        if(!LastSize.IsZero()&&!LastSize.Equals(FVector2D(G.GetLocalSize()),.1))Cancel();LastSize=G.GetLocalSize();
        if(!Owner.IsValid()||!Owner->System())return;
        const double Now=FPlatformTime::Seconds();
        Chips.RemoveAll([Now](const FChip& C){return Now-C.Born>WoodworkingPresentation::ChipLifetime;});
        if(Owner->System()->MotorRunning())SawMotion=FMath::Fmod(SawMotion+FMath::Min(Delta,.1f)*72,8.0);
        if(bDragging&&Owner->System()->State()!=EWoodworkingPhase::Running&&Owner->System()->State()!=EWoodworkingPhase::Preview)Cancel();
        if(Owner->IsWorldMode()||Owner->System()->MotorRunning()||!Chips.IsEmpty()||Now<DamageUntil)Invalidate(EInvalidateWidgetReason::Paint);
    }
    void Contact(uint64 Before)
    {
        auto* O=Owner.Get();if(!O||!O->System()||O->System()->Mask().CutSerial()==Before)return;
        const auto& Event=O->System()->Mask().LastCut();if(Event.Removed<=0)return;
        const double Now=FPlatformTime::Seconds();
        if(Event.Damaged>0){DamageAt=Event.DamagePoint;DamageUntil=Now+.85;}
        if(Now>=NextChips)
        {
            const int32 Count=FMath::Min3(WoodworkingPresentation::ChipsPerContact,Event.Samples.Num(),WoodworkingPresentation::MaximumChips-Chips.Num());
            for(int32 I=0;I<Count;++I)
            {
                FVector2D Point=O->System()->BoardToWork(Event.Samples[I]);
                Point.X=FMath::Clamp(Point.X,-O->System()->SawSettings().Kerf*.5,O->System()->SawSettings().Kerf*.5);
                Point.Y=FMath::Clamp(Point.Y,-O->System()->SawSettings().ContactLength*.5,O->System()->SawSettings().ContactLength*.5);
                const double Side=((ChipSerial++)&1)?1:-1;
                Chips.Add({Point,FVector2D(Side*(28+I*9),-18-I*6),Now});
            }
            NextChips=Now+WoodworkingPresentation::ChipInterval;
        }
        O->NotifyCutContact();O->PlayCutSound();Invalidate(EInvalidateWidgetReason::Paint);
    }
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle&,bool) const override
    {
        const auto* O=Owner.Get();if(!O||!O->System())return Layer;
        // The saw guide is rendered on the blade socket in the world view.
        if(O->IsWorldMode())return Layer;
        const auto* S=O->System();
        const auto V=View(G);const auto* White=FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));
        const double Dpi=FMath::Max(.1f,G.GetAccumulatedLayoutTransform().GetScale()),Px=1/Dpi;
        auto Line=[&](const TArray<FVector2D>& Points,FLinearColor Color,double Width,int32 Z)
        {if(Points.Num()<2)return;FSlateDrawElement::MakeLines(Out,Layer+Z,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Color,true,Width*Px);};
        const FLinearColor EdgeRed(.95f,.008f,.004f,1);
        auto PreviewLine=[&](FVector2D A,FVector2D B,int32 Z)
        {
            for(int32 I=0;I<12;++I)
            {
                const FVector2D Start=A+(B-A)*(double(I)/12),End=A+(B-A)*((I+.55)/12);
                Line({Start,End},FLinearColor(0,0,0,.95f),6,Z);
                Line({Start,End},EdgeRed,3,Z+1);
            }
        };
        auto WP=[&](FVector2D P){return V.Origin+P*V.Scale;};
        auto Box=[&](FVector2D P,FVector2D Size,FLinearColor Color,int32 Z)
        {FSlateDrawElement::MakeBox(Out,Layer+Z,G.ToPaintGeometry(Size,FSlateLayoutTransform(P)),White,ESlateDrawEffect::None,Color);};
        Box(FVector2D::ZeroVector,G.GetLocalSize(),ColdSteelUI::Content,0);
        // Quiet metal tabletop; all equipment geometry uses the same work coordinates as the blade.
        Box(WP(FVector2D(-300,-340)),FVector2D(600,680)*V.Scale,FLinearColor(.075f,.080f,.085f,1.f),1);
        for(int32 I=-5;I<=5;++I)Line({WP(FVector2D(-290,I*60)),WP(FVector2D(290,I*60))},FLinearColor(.16f,.17f,.18f,.3f),.6,2);
        const double Half=S->SawSettings().ContactLength*.5,Kerf=S->SawSettings().Kerf;
        Box(WP(FVector2D(-12,-Half-16)),FVector2D(24,Half*2+32)*V.Scale,FLinearColor(.03f,.035f,.04f,1.f),3);
        Line({WP(FVector2D(0,-Half-48)),WP(FVector2D(0,-Half-20))},ColdSteelUI::TextSecondary,.8,3);
        Line({WP(FVector2D(0,Half+20)),WP(FVector2D(0,Half+48))},ColdSteelUI::TextSecondary,.8,3);
        const FVector2D BoardSize(S->Settings().Width,S->Settings().Height);
        const FVector2D BoardOrigin=WP(S->Pose().Offset)-BoardSize*V.Scale*.5;
        auto BoardGeometry=[&](FVector2D Offset)
        {return G.ToPaintGeometry(BoardSize,FSlateLayoutTransform(float(V.Scale),BoardOrigin+Offset),FSlateRenderTransform(FQuat2D(float(S->Pose().Angle))),FVector2D(.5,.5));};
        for(int32 I=4;I>=1;--I)
            FSlateDrawElement::MakeBox(Out,Layer+4,BoardGeometry(FVector2D(I*1.1,I*1.8)*Px),&O->BoardBrush(),ESlateDrawEffect::None,FLinearColor(0.f,0.f,0.f,.08f));
        FSlateDrawElement::MakeBox(Out,Layer+5,BoardGeometry(FVector2D(0,3)*Px),&O->BoardBrush(),ESlateDrawEffect::None,FLinearColor(.30f,.24f,.18f,1.f));
        FSlateDrawElement::MakeBox(Out,Layer+6,BoardGeometry(FVector2D::ZeroVector),&O->BoardBrush(),ESlateDrawEffect::None,FLinearColor::White);
        FSlateDrawElement::MakeBox(Out,Layer+7,BoardGeometry(FVector2D::ZeroVector),&O->DamageBrush(),ESlateDrawEffect::None,FLinearColor::White);
        for(const auto& Path:O->Contours())
        {
            TArray<FVector2D> Points;Points.Reserve(Path.Num());for(const auto& P:Path)Points.Add(WP(S->BoardToWork(P)));
            Line(Points,ColdSteelUI::Accent,.95,8);
        }
        if(S->IsAdjusting())PreviewLine(WP(FVector2D(0,-Half)),WP(FVector2D(0,Half)),9);
        else
        {
            // Thin fixed knife footprint. Teeth travel only while the motor is actually running.
            Line({WP(FVector2D(0,-Half)),WP(FVector2D(0,Half))},FLinearColor(0,0,0,.95f),FMath::Max(6.,Kerf*V.Scale*Dpi+3),9);
            Line({WP(FVector2D(0,-Half)),WP(FVector2D(0,Half))},EdgeRed,FMath::Max(3.,Kerf*V.Scale*Dpi),10);
            TArray<FVector2D> KnifeBoundary;KnifeBoundary.Reserve(35);
            for(int32 I=0;I<=16;++I){const double A=PI+PI*I/16;KnifeBoundary.Add(WP(FVector2D(FMath::Cos(A)*Kerf*.5,-Half+FMath::Sin(A)*Kerf*.5)));}
            for(int32 I=0;I<=16;++I){const double A=PI*I/16;KnifeBoundary.Add(WP(FVector2D(FMath::Cos(A)*Kerf*.5,Half+FMath::Sin(A)*Kerf*.5)));}
            WoodworkingPresentation::ClosePolyline(KnifeBoundary);Line(KnifeBoundary,EdgeRed,1,10);
            for(double Y=-Half+SawMotion;Y<=Half;Y+=8)
                Line({WP(FVector2D(-Kerf*.5,Y)),WP(FVector2D(Kerf*.5,Y+1))},ColdSteelUI::Content,.7,10);
        }
        const double Now=FPlatformTime::Seconds();
        for(const auto& Chip:Chips)
        {
            const double Age=Now-Chip.Born,Alpha=FMath::Clamp(1-Age/WoodworkingPresentation::ChipLifetime,0.0,1.0);
            const FVector2D P=WP(Chip.At+Chip.Velocity*Age+FVector2D(0,95*Age*Age));
            Line({P,P+FVector2D(3,1)*Px},FLinearColor(.74f,.54f,.30f,float(Alpha)),1.5,13);
        }
        if(Now<DamageUntil)
        {
            const FVector2D At=WP(S->BoardToWork(DamageAt));const double R=(10+10*(1-(DamageUntil-Now)/.85))*Px;
            TArray<FVector2D> Ring;Ring.Reserve(33);for(int32 I=0;I<=32;++I){const double A=2*PI*I/32;Ring.Add(At+FVector2D(FMath::Cos(A),FMath::Sin(A))*R);}
            auto Color=ColdSteelUI::Danger;Color.A=float((DamageUntil-Now)/.85);Line(Ring,Color,1.5,14);
        }
        return Layer+14;
    }
    virtual FReply OnMouseButtonDown(const FGeometry& G,const FPointerEvent& E) override
    {
        if(bBlocked||!Owner.IsValid()||!Owner->System())return FReply::Handled();
        FVector2D Work;if(!WorkPoint(G,E.GetScreenSpacePosition(),Work))return FReply::Handled();
        if(E.GetEffectingButton()==EKeys::MiddleMouseButton&&!Owner->IsWorldMode())
        {Cancel();bPanning=true;LastPointer=G.AbsoluteToLocal(E.GetScreenSpacePosition());return FReply::Handled().CaptureMouse(SharedThis(this)).SetUserFocus(SharedThis(this));}
        if(E.GetEffectingButton()==EKeys::LeftMouseButton&&CanGrab(Work)&&Owner->System()->BeginFeed())
        {bDragging=true;GrabLocal=Owner->System()->WorkToBoard(Work);LastWork=Work;return FReply::Handled().CaptureMouse(SharedThis(this)).SetUserFocus(SharedThis(this));}
        return FReply::Handled();
    }
    virtual FReply OnMouseMove(const FGeometry& G,const FPointerEvent& E) override
    {
        const FVector2D Local=G.AbsoluteToLocal(E.GetScreenSpacePosition());
        const bool Inside=Local.X>=0&&Local.Y>=0&&Local.X<G.GetLocalSize().X&&Local.Y<G.GetLocalSize().Y;
        if((bDragging||bPanning)&&(!Inside||bBlocked||(bDragging&&!E.IsMouseButtonDown(EKeys::LeftMouseButton))||(bPanning&&!E.IsMouseButtonDown(EKeys::MiddleMouseButton))))
        {Cancel();return FReply::Handled().ReleaseMouseCapture();}
        if(bPanning)
        {
            const auto V=View(G);Pan+=(Local-LastPointer)/V.Fit;LastPointer=Local;
            Pan.X=FMath::Clamp(Pan.X,-1200.0,1200.0);Pan.Y=FMath::Clamp(Pan.Y,-1200.0,1200.0);
        }
        else if(bDragging&&Owner.IsValid())
        {
            auto* S=Owner->System();FVector2D Work;if(!WorkPoint(G,E.GetScreenSpacePosition(),Work)){Cancel();return FReply::Handled().ReleaseMouseCapture();}const uint64 Before=S->Mask().CutSerial();
            const FVector2D Requested=Work-S->BoardToWork(GrabLocal);
            S->MoveBoard(Requested);LastWork=Work;
            if(!S->BoardToWork(GrabLocal).Equals(Work,.01))GrabLocal=S->WorkToBoard(Work); // Re-anchor blocked directions; no later sideways snap.
            Contact(Before);
            if(S->State()!=EWoodworkingPhase::Running&&S->State()!=EWoodworkingPhase::Preview){Cancel();return FReply::Handled().ReleaseMouseCapture();}
        }
        Invalidate(EInvalidateWidgetReason::Paint);return FReply::Handled();
    }
    virtual FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent& E) override
    {if(E.GetEffectingButton()==EKeys::LeftMouseButton||E.GetEffectingButton()==EKeys::MiddleMouseButton){Cancel();return FReply::Handled().ReleaseMouseCapture();}return FReply::Handled();}
    virtual void OnMouseCaptureLost(const FCaptureLostEvent&) override {bDragging=bPanning=false;if(Owner.IsValid()&&Owner->System())Owner->System()->EndStroke();}
    virtual void OnFocusLost(const FFocusEvent&) override {Cancel();}
    virtual void OnMouseLeave(const FPointerEvent& E) override {SLeafWidget::OnMouseLeave(E);if(!HasMouseCapture())Cancel();}
    virtual FReply OnMouseWheel(const FGeometry& G,const FPointerEvent& E) override
    {
        if(bBlocked)return FReply::Handled();Cancel();
        if(Owner.IsValid()&&Owner->IsWorldMode()){Owner->ZoomWorld(E.GetWheelDelta());return FReply::Handled();}
        const auto Before=View(G);
        const FVector2D Local=G.AbsoluteToLocal(E.GetScreenSpacePosition()),At=(Local-Before.Origin)/Before.Scale;
        Zoom=FMath::Clamp(Zoom*FMath::Pow(1.15,double(E.GetWheelDelta())),.5,4.0);
        Pan=(Local-G.GetLocalSize()*.5-At*Before.Fit*Zoom)/Before.Fit;
        Invalidate(EInvalidateWidgetReason::Paint);return FReply::Handled();
    }
private:
    struct FChip{FVector2D At,Velocity;double Born=0;};
    TWeakObjectPtr<UColdSteelWoodworkingWidget> Owner;
    TArray<FChip> Chips;
    FVector2D Pan=FVector2D::ZeroVector,LastPointer=FVector2D::ZeroVector,LastWork=FVector2D::ZeroVector,LastSize=FVector2D::ZeroVector,GrabLocal=FVector2D::ZeroVector,DamageAt=FVector2D::ZeroVector;
    double Zoom=1,NextChips=0,DamageUntil=0,SawMotion=0;uint32 ChipSerial=0;
    bool bDragging=false,bPanning=false,bBlocked=false;
};

#include "WoodworkingPanel.inl"

void UColdSteelWoodworkingWidget::NativeOnInitialized()
{Super::NativeOnInitialized();SetIsFocusable(true);Woodworking=GetGameInstance()->GetSubsystem<UWoodworkingSystem>();}
bool UColdSteelWoodworkingWidget::Configure(AActor* Station,bool PracticeOnly)
{
    if(PracticeOnly||!Station)return false;
    Workbench=Station;EntryPawn=GetOwningPlayerPawn();
    SawVisual=Station->FindComponentByClass<UWoodworkingSawVisualComponent>();
    if(!EntryFlow.Open()||!Woodworking||!Woodworking->Open(false)){EndSession();return false;}
    LastRevision=-1;EntryNotice.Reset();return true;
}
TSharedRef<SWidget> UColdSteelWoodworkingWidget::RebuildWidget()
{return SAssignNew(Panel,SWoodworkingPanel).Owner(this);}
TSharedRef<SWidget> UColdSteelWoodworkingWidget::ManagementContent()
{
    if(!ManagementWidget)ManagementWidget=CreateWidget<UColdSteelWoodworkingManagementWidget>(this);
    if(!ManagementWidget)return SNullWidget::NullWidget;
    ManagementWidget->Configure(this);return ManagementWidget->TakeWidget();
}
void UColdSteelWoodworkingWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if(FSlateApplication::IsInitialized()&&!ActivationHandle.IsValid())ActivationHandle=FSlateApplication::Get().OnApplicationActivationStateChanged().AddUObject(this,&ThisClass::ApplicationActive);
    if(!CuttingSound.IsNull())SoundLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(CuttingSound.ToSoftObjectPath());
    UpdateImages(true); // Selection preview only; confirming the project owns world creation.
}
void UColdSteelWoodworkingWidget::NativeDestruct()
{
    EndSession();SawVisual.Reset();StopMotorAudio();
    if(FSlateApplication::IsInitialized()&&ActivationHandle.IsValid())FSlateApplication::Get().OnApplicationActivationStateChanged().Remove(ActivationHandle);
    ActivationHandle.Reset();
    if(CutAudio){CutAudio->Stop();CutAudio->DestroyComponent();CutAudio=nullptr;}
    if(SoundLoad){SoundLoad->CancelHandle();SoundLoad.Reset();}
    Super::NativeDestruct();
}
void UColdSteelWoodworkingWidget::ReleaseSlateResources(bool Children)
{Super::ReleaseSlateResources(Children);Panel.Reset();if(Children&&ManagementWidget)ManagementWidget->ReleaseSlateResources(Children);}
void UColdSteelWoodworkingWidget::ApplicationActive(bool Active){if(!Active)CancelInput();}
void UColdSteelWoodworkingWidget::CancelInput(){if(Panel)Panel->CancelInput();else if(Woodworking)Woodworking->EndStroke();}
void UColdSteelWoodworkingWidget::RequestClose()
{
    if(EntryFlow.Closed())return;
    if(EntryFlow.InWorkshop()){if(Woodworking&&!Woodworking->Suspend())return;ReturnToSelection();return;}
    CloseConfirmed();
}
void UColdSteelWoodworkingWidget::CloseConfirmed()
{if(EntryFlow.Closed())return;if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->CloseWoodworking();else EndSession();}
bool UColdSteelWoodworkingWidget::EnsureStation()
{
    if(EntryFlow.Closed())return false;
    if(!EntryPawn.IsValid()||EntryPawn.Get()!=GetOwningPlayerPawn()){CloseConfirmed();return false;}
    if(IsWorldMode()&&(!IsValid(WorldView)||!WorldView->Healthy())){CloseConfirmed();return false;}
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Workbench.Get());const auto* Pawn=GetOwningPlayerPawn();
    const auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    if(!Piece||Piece->PrefabId()!=VoxelWoodworkingBenchId||Piece->IsFalling()||!World||!World->HasPrefabAt(Piece->AnchorCell())||!Pawn||!Piece->Body()
        ||Piece->Body()->Bounds.GetBox().ComputeSquaredDistanceToPoint(Pawn->GetActorLocation())>240.f*240.f)
    {CloseConfirmed();return false;}
    return true;
}
FReply UColdSteelWoodworkingWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry,const FKeyEvent& E)
{
    if(IsProjectMenu())
    {
        if(!ManagementInputReady())return FReply::Handled();
        // Let the combo own arrows, Enter, Space and Escape while its menu is open.
        if(ManagementWidget&&ManagementWidget->IsRecipeMenuOpen())return Super::NativeOnPreviewKeyDown(Geometry,E);
        if(E.GetKey()==EKeys::Escape){RequestClose();return FReply::Handled();}
        return Super::NativeOnPreviewKeyDown(Geometry,E);
    }
    if(E.IsRepeat()&&E.GetKey()!=EKeys::Q&&E.GetKey()!=EKeys::E)return FReply::Handled();
    if(E.GetKey()==EKeys::Escape||E.GetKey()==EKeys::Tab){RequestClose();return FReply::Handled();}
    if(EntryFlow.InWorkshop()&&Woodworking&&Panel&&!Panel->Confirming()&&PresentationReady())
    {
        if(E.IsControlDown()&&E.GetKey()==EKeys::Z)Panel->Undo();
        else if(E.GetKey()==EKeys::Q)Panel->Rotate(-1,E.IsShiftDown());
        else if(E.GetKey()==EKeys::E)Panel->Rotate(1,E.IsShiftDown());
        else if(E.GetKey()==EKeys::SpaceBar)Panel->ToggleCutting();
    }
    return FReply::Handled();
}
void UColdSteelWoodworkingWidget::PlayCutSound()
{
    const double Now=FPlatformTime::Seconds();if(Now<NextCutSound||!CuttingSound.IsValid()||!Woodworking||!Woodworking->MotorRunning())return;
    NextCutSound=Now+WoodworkingPresentation::SoundInterval;
    // At most one voice, with no synchronous asset load in this input path.
    if(CutAudio&&CutAudio->IsPlaying())return;
    if(!CutAudio)CutAudio=UGameplayStatics::SpawnSound2D(this,CuttingSound.Get(),.35f,1.f,0.f,nullptr,false,false);
    else CutAudio->Play();
}
void UColdSteelWoodworkingWidget::NativeTick(const FGeometry& G,float Delta)
{
    Super::NativeTick(G,Delta);if(!Woodworking||EntryFlow.Closed())return;
    const float Drawer=DrawerProgress();
    const float Target=IsProjectMenu()&&!bDrawerClosing&&Drawer>1.f-KINDA_SMALL_NUMBER?1.f:0.f;
    ManagementMotion=FMath::FInterpConstantTo(ManagementMotion,Target,Delta,4.f);
    if(bCloseRequested)
    {if(Drawer<=KINDA_SMALL_NUMBER){bCloseAnimationDone=true;CloseConfirmed();}return;}
    if(IsValid(WorldView)&&WorldView->MeshBudgetFailure())UseCanvasFallback();
    UpdateMotorAudio();
    if(auto* Saw=SawVisual.Get())Saw->SetPowered(EntryFlow.InWorkshop()&&Woodworking->MotorRunning(),EntryFlow.InWorkshop()&&Woodworking->IsAdjusting());
    const float Scale=ColdSteelUI::PixelScale(this);const auto Size=UWidgetLayoutLibrary::GetViewportSize(this);
    if(Panel&&(!FMath::IsNearlyEqual(Scale,LastScale,.001f)||!FMath::IsNearlyEqual(float(Size.X),LastWidth,1.f)||!FMath::IsNearlyEqual(float(Size.Y),LastHeight,1.f)))
    {LastScale=Scale;LastWidth=Size.X;LastHeight=Size.Y;Panel->Build();}
    if(CutAudio&&CutAudio->IsPlaying()&&(!Woodworking->MotorRunning()||FPlatformTime::Seconds()>NextCutSound+.05))CutAudio->Stop();
    const double Now=FPlatformTime::Seconds();
    if(Now>=NextStationCheck)
    {
        NextStationCheck=Now+.2;if(!EnsureStation())return;
    }
    if(EntryFlow.InWorkshop()&&(Woodworking->State()==EWoodworkingPhase::Complete||Woodworking->State()==EWoodworkingPhase::Failed))
    {UpdateImages(true);ReturnToSelection();return;}
    if(EntryFlow.Selecting()&&!Woodworking->HasPendingJob()&&Woodworking->State()==EWoodworkingPhase::Delivered)
    {EntryNotice=Woodworking->Message();Woodworking->Restart();UpdateImages(true);if(Panel)Panel->Build();}
    if(EntryFlow.Preparing())
    {
        if(!bCanvasFallback&&(!IsValid(WorldView)||WorldView->Failed()))
        {
            const FString Why=IsValid(WorldView)?WorldView->Status():TEXT("实景资源失效，请重新选择项目。");
            ReturnToSelection();EntryNotice=Why;return;
        }
        if((bCanvasFallback||(WorldView&&WorldView->Prepared()))&&EnsureStation())
        {
            if(!bStartRequested)
            {
                bStartRequested=true;
                if(!(Woodworking->HasPendingJob()?Woodworking->Resume():Woodworking->StartMode(EWoodworkingMode::Craft)))
                {const FString Why=Woodworking->Message();ReturnToSelection();EntryNotice=Why;return;}
            }
            if(Woodworking->TransactionPending())return;
            if(!Woodworking->HasPendingJob()||Woodworking->State()!=EWoodworkingPhase::Running)
            {const FString Why=Woodworking->Message();ReturnToSelection();EntryNotice=Why;return;}
            if(!bDrawerClosing)
            {
                // A resume receipt can replace the preview mask while keeping its revision number.
                // Rebuild that exact authoritative stock before switching the player's view.
                bDrawerClosing=true;if(WorldView)WorldView->InvalidateBoard();ShowManagementInventory(false);return;
            }
            if(DrawerProgress()>KINDA_SMALL_NUMBER)return;
            if(WorldView)WorldView->Enter();EntryFlow.Prepared();
            if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))if(auto* HUD=PC->GetColdSteelHUD())HUD->SetWoodworkingManagement(false);
            bDrawerClosing=false;
            if(Panel){Panel->ResetConfirm();Panel->Build();}SetKeyboardFocus();
        }
    }
    if((bCanvasFallback||IsProjectMenu()||Woodworking->State()==EWoodworkingPhase::Complete||Woodworking->State()==EWoodworkingPhase::Failed||Woodworking->State()==EWoodworkingPhase::Delivered)&&Now>=NextUpload){UpdateImages();NextUpload=Now+1.0/30.0;}
}
void UColdSteelWoodworkingWidget::UpdateImages(bool Force)
{
    if(!Woodworking||Woodworking->Mask().Wood().IsEmpty())return;
    const auto& M=Woodworking->Mask();const auto* Pattern=Woodworking->Pattern();if(!Pattern)return;
    const bool NewPattern=ImagePattern!=Pattern->Id;
    if(!Force&&!NewPattern&&LastRevision==M.Revision())return;
    const int32 Width=Woodworking->Settings().Width,Height=Woodworking->Settings().Height,Count=Width*Height;
    if(!WoodTexture)
    {
        auto MakeTexture=[&]()
        {auto* T=UTexture2D::CreateTransient(Width,Height,PF_B8G8R8A8);T->NeverStream=true;T->SRGB=true;T->Filter=TF_Bilinear;T->AddressX=TA_Clamp;T->AddressY=TA_Clamp;T->UpdateResource();return T;};
        WoodTexture=MakeTexture();OutlineTexture=MakeTexture();DamageTexture=MakeTexture();
        auto Brush=[&](FSlateBrush& B,UTexture2D* T){B.SetResourceObject(T);B.ImageSize=FVector2D(Width,Height);B.DrawAs=ESlateBrushDrawType::Image;};
        Brush(WoodBrush,WoodTexture);Brush(OutlineBrush,OutlineTexture);Brush(DamageOverlayBrush,DamageTexture);
        WoodColors.SetNum(Count);
        for(int32 Y=0;Y<Height;++Y)for(int32 X=0;X<Width;++X)
        {
            const double Grain=.5+.5*FMath::Sin(Y*.43+FMath::Sin(X*.014)*2.4+FMath::Sin(X*.034+Y*.06));
            const double Fine=.5+.5*FMath::Sin(Y*2.4+X*.017);
            const double Shade=.79+.16*Grain+.05*Fine;
            WoodColors[Y*Width+X]=FColor(uint8(180*Shade),uint8(136*Shade),uint8(88*Shade),255);
        }
    }
    if(!WoodTexture->GetResource()||!OutlineTexture->GetResource()||!DamageTexture->GetResource())return;
    auto Upload=[&](UTexture2D* Texture,const TArray<FColor>& Colors)
    {
        auto* Pixels=new uint8[Count*sizeof(FColor)];FMemory::Memcpy(Pixels,Colors.GetData(),Count*sizeof(FColor));
        auto* Region=new FUpdateTextureRegion2D(0,0,0,0,Width,Height);
        Texture->UpdateTextureRegions(0,1,Region,Width*sizeof(FColor),sizeof(FColor),Pixels,[](uint8* Data,const FUpdateTextureRegion2D* Areas){delete[] Data;delete Areas;});
    };
    TArray<FColor> Pixels;Pixels.SetNumUninitialized(Count);
    for(int32 Y=0;Y<Height;++Y)for(int32 X=0;X<Width;++X)
    {
        const int32 I=Y*Width+X;
        if(!M.Wood()[I]){Pixels[I]=FColor(0,0,0,0);continue;}
        const bool Left=X==0||!M.Wood()[I-1],Right=X+1==Width||!M.Wood()[I+1];
        const bool Top=Y==0||!M.Wood()[I-Width],Bottom=Y+1==Height||!M.Wood()[I+Width];
        FColor Color=WoodColors[I];
        if(Left||Right||Top||Bottom)
        {
            const double EndGrain=.86+.14*FMath::Sin(Y*.8+X*.25),Light=(Top||Left)?1.18:.85;
            Color=FColor(uint8(FMath::Clamp(204*EndGrain*Light,0.0,255.0)),uint8(158*EndGrain*Light),uint8(101*EndGrain*Light),255);
        }
        Pixels[I]=Color;
    }
    Upload(WoodTexture,Pixels);
    FColor Damage=ColdSteelUI::Danger.ToFColorSRGB();
    for(int32 I=0;I<Count;++I){Damage.A=((I%Width+I/Width)%8<3)?100:35;Pixels[I]=M.Damage()[I]?Damage:FColor(0,0,0,0);}
    Upload(DamageTexture,Pixels);
    if(NewPattern||Force)
    {
        const FColor Edge=ColdSteelUI::Accent.ToFColorSRGB();for(int32 I=0;I<Count;++I)Pixels[I]=M.Target()[I]?Edge:FColor(0,0,0,0);
        Upload(OutlineTexture,Pixels);WoodworkingPresentation::TargetContours(M.Target(),Width,Height,CachedContours);
    }
    ImagePattern=Pattern->Id;LastRevision=M.Revision();if(Panel)Panel->Invalidate(EInvalidateWidgetReason::Paint);
}

bool UColdSteelWoodworkingWidget::PresentationReady() const {return EntryFlow.InWorkshop()&&(bCanvasFallback||(IsValid(WorldView)&&WorldView->Ready()));}
bool UColdSteelWoodworkingWidget::CursorToWorldWork(FVector2D Screen,FVector2D& Work) const
{if(!WorldView)return false;FVector2D Pixel,Viewport;USlateBlueprintLibrary::AbsoluteToViewport(this,Screen,Pixel,Viewport);return WorldView->CursorToWork(Pixel,Work);}
void UColdSteelWoodworkingWidget::ZoomWorld(float Steps){if(WorldView)WorldView->Zoom(Steps);}
void UColdSteelWoodworkingWidget::ResetWorldCamera(){if(WorldView)WorldView->ResetCamera();}
void UColdSteelWoodworkingWidget::BoardChanged(){if(WorldView)WorldView->InvalidateBoard();}
FString UColdSteelWoodworkingWidget::PresentationStatus() const {return !EntryNotice.IsEmpty()?EntryNotice:IsValid(WorldView)?WorldView->Status():FString();}

bool UColdSteelWoodworkingWidget::CanConfirmProject() const
{return ManagementInputReady()&&EntryFlow.Selecting()&&Woodworking&&!Woodworking->TransactionPending()&&Woodworking->Pattern()
    &&(Woodworking->CanResume()||(!Woodworking->HasPendingJob()&&Woodworking->State()==EWoodworkingPhase::Preview));}
void UColdSteelWoodworkingWidget::SelectProject(FName Id)
{if(EntryFlow.Selecting()&&Woodworking&&Woodworking->Select(Id)){EntryNotice.Reset();UpdateImages(true);}}
void UColdSteelWoodworkingWidget::ConfirmProject()
{
    if(!CanConfirmProject()||!EnsureStation()||!EntryFlow.Confirm())return;
    CancelInput();EntryNotice.Reset();bStartRequested=false;bCanvasFallback=false;
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(Workbench.Get());
    FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;Params.Owner=GetOwningPlayer();Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    WorldView=GetWorld()->SpawnActor<AWoodworkingWorldView>(AWoodworkingWorldView::StaticClass(),FTransform::Identity,Params);
    if(!WorldView||!Piece||!WorldView->Prepare(GetOwningPlayer(),Piece->Body(),Woodworking))
    {ReleaseWorldView();EntryFlow.Back();EntryNotice=TEXT("工作台资源未就绪，请重试或退出。");}
    if(Panel){Panel->ResetConfirm();Panel->Build();}SetKeyboardFocus();
}
void UColdSteelWoodworkingWidget::ReleaseWorldView()
{
    if(auto* Saw=SawVisual.Get())Saw->SetPowered(false);
    if(IsValid(WorldView)){WorldView->Leave();WorldView->Destroy();}WorldView=nullptr;
    if(CutAudio)CutAudio->Stop();StopMotorAudio();
}
void UColdSteelWoodworkingWidget::EndSession()
{
    // Called synchronously by the controller. A delayed NativeDestruct must not close a newer session.
    if(!EntryFlow.Close())return;
    CancelInput();ReleaseWorldView();if(Woodworking)Woodworking->Close();
    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))if(auto* HUD=PC->GetColdSteelHUD())HUD->SetWoodworkingManagement(false);
}
void UColdSteelWoodworkingWidget::RequestReturnToSelection()
{
    if(EntryFlow.Closed())return;
    if(Woodworking&&Woodworking->HasPendingJob()&&!Woodworking->Job().bFinished&&!Woodworking->Settle())return;
    ReturnToSelection();
}
void UColdSteelWoodworkingWidget::ReturnToSelection()
{
    if(Woodworking&&Woodworking->HasPendingJob()&&!Woodworking->Job().bFinished&&!Woodworking->Suspend())return;
    if(!EntryFlow.Back())return;bStartRequested=false;
    CancelInput();ReleaseWorldView();EntryNotice.Reset();bCanvasFallback=bDrawerClosing=false;ManagementMotion=0;
    if(!Woodworking||(!Woodworking->HasPendingJob()&&!Woodworking->Open(false))){CloseConfirmed();return;}
    ShowManagementInventory(true);
    LastRevision=-1;UpdateImages(true);
    if(Panel){Panel->ResetConfirm();Panel->Build();}SetKeyboardFocus();
}

bool UColdSteelWoodworkingWidget::RestartProject()
{
    CancelInput();if(!Woodworking||!Woodworking->Restart())return false;
    UpdateImages(true);BoardChanged();StopMotorAudio();return true;
}
void UColdSteelWoodworkingWidget::SetWorkshopInsets(FMargin Insets)
{if(WorldView)WorldView->SetScreenInsets(Insets);}
void UColdSteelWoodworkingWidget::SetReviewOverlay(bool Enabled)
{if(WorldView)WorldView->SetReview(Enabled);}
void UColdSteelWoodworkingWidget::NotifyCutContact()
{LastContactTime=FPlatformTime::Seconds();}
void UColdSteelWoodworkingWidget::ShowManagementInventory(bool Open)
{if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))if(auto* HUD=PC->GetColdSteelHUD())
    {if(Open)HUD->SetWoodworkingManagement(true);else HUD->SetWoodworkingDrawerOpen(false);}}
float UColdSteelWoodworkingWidget::DrawerProgress() const
{if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))if(auto* HUD=PC->GetColdSteelHUD())return HUD->WoodworkingDrawerProgress();return bDrawerClosing?0.f:1.f;}
bool UColdSteelWoodworkingWidget::ManagementInputReady() const
{return IsProjectMenu()&&!bDrawerClosing&&!bCloseRequested&&ManagementMotion>1.f-KINDA_SMALL_NUMBER&&DrawerProgress()>1.f-KINDA_SMALL_NUMBER;}
FVector2D UColdSteelWoodworkingWidget::ManagementSlide(float Width,float Scale,bool Outer) const
{
    const float X=bDrawerClosing?(Outer?(1.f-ColdSteelUI::EaseSmooth(DrawerProgress()))*(2*Width+ColdSteelUI::NavigationDrawerInset+24):0.f):
        Outer?0.f:(1.f-ColdSteelUI::EaseSmooth(ManagementMotion))*(Width+24);
    return FVector2D(X/Scale,0);
}
bool UColdSteelWoodworkingWidget::BeginAnimatedClose()
{
    if(bCloseAnimationDone||!IsProjectMenu())return false;
    if(!bCloseRequested)
    {
        bCloseRequested=bDrawerClosing=true;CancelInput();
        if(Woodworking&&Woodworking->HasPendingJob())Woodworking->Suspend();
        ShowManagementInventory(false);
    }
    return true;
}
void UColdSteelWoodworkingWidget::UseCanvasFallback()
{
    CancelInput();if(Woodworking->MotorRunning())Woodworking->ToggleMotor();
    bCanvasFallback=true;ReleaseWorldView();UpdateImages(true);
    EntryNotice=TEXT("实景显示暂不可用，已切换平面台面；加工进度保留，按空格继续切割。");
    if(Panel)Panel->Build();
}
void UColdSteelWoodworkingWidget::StopMotorAudio()
{
    if(MotorAudio){MotorAudio->Stop();MotorAudio->DestroyComponent();MotorAudio=nullptr;}
    MotorWave=nullptr;AudioPhase=0;LastContactTime=-1;
}
void UColdSteelWoodworkingWidget::UpdateMotorAudio()
{
    if(!Woodworking->MotorRunning()){if(MotorAudio)StopMotorAudio();return;}
    constexpr int32 Rate=22050,Frames=1764;
    if(!MotorWave)
    {
        MotorWave=NewObject<USoundWaveProcedural>(this);MotorWave->SetSampleRate(Rate);MotorWave->NumChannels=1;
        MotorWave->Duration=INDEFINITELY_LOOPING_DURATION;MotorWave->SoundGroup=SOUNDGROUP_Effects;
    }
    if(MotorWave->GetAvailableAudioByteCount()<Frames*2)
    {
        // Authored motor/contact synthesis: bounded mono voice, no external recording/license dependency.
        TArray<int16> PCM;PCM.SetNumUninitialized(Frames);
        const double Load=FPlatformTime::Seconds()-LastContactTime<.12?1.0:0.0;
        for(int32 I=0;I<Frames;++I)
        {
            AudioNoise=AudioNoise*1664525u+1013904223u;const double Noise=double(AudioNoise>>8)/8388607.5-1;
            const double Ramp=FMath::Min(1.0,AudioPhase/.035);
            const double Tone=FMath::Sin(AudioPhase*2*PI*96)*.055+FMath::Sin(AudioPhase*2*PI*384)*.021;
            const double Contact=Noise*(.018+.105*Load)*( .75+.25*FMath::Sin(AudioPhase*2*PI*29));
            PCM[I]=int16(FMath::Clamp((Tone+Contact)*Ramp,-.8,.8)*32767);AudioPhase+=1.0/Rate;
        }
        MotorWave->QueueAudio(reinterpret_cast<const uint8*>(PCM.GetData()),PCM.Num()*sizeof(int16));
    }
    if(!MotorAudio)MotorAudio=UGameplayStatics::SpawnSound2D(this,MotorWave,.28f,1,0,nullptr,false,false);
}
