#include "ColdSteelAlchemyBookWidget.h"
#include "AlchemyManualLayout.h"
#include "ColdSteelPreviewScene.h"
#include "GunsmithUIStyle.h"
#include "../Building/AlchemyManualComponent.h"
#include "../Building/AlchemyManualGeometry.h"
#include "../Building/BookLeafComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/TextBlock.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/TextureCube.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Input/Reply.h"
#include "InputCoreTypes.h"
#include "HAL/PlatformTime.h"
#include "Framework/Application/SlateApplication.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace {
const FSoftObjectPath ManualComposite(TEXT("/Game/UI/GunsmithWorkbench/M_WeaponPreviewResolved.M_WeaponPreviewResolved"));
const FSoftObjectPath ManualEnvironment(TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment"));
const FSoftObjectPath PaperAudio(TEXT("/Game/Building/PotionWorkbench20261015/RuntimeV2/Audio/SW_AlchemyPage.SW_AlchemyPage"));
const FVector ManualEye(0,8,85),ManualAim(0,0,1.7);
constexpr float ManualAspect=1400.f/1100.f;
}
UColdSteelAlchemyBookPreviewWidget::UColdSteelAlchemyBookPreviewWidget(const FObjectInitializer& Initializer):Super(Initializer){}
UColdSteelAlchemyBookPreviewWidget::~UColdSteelAlchemyBookPreviewWidget()=default;
void UColdSteelAlchemyBookPreviewWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetVisibility(ESlateVisibility::Visible);
    auto* Overlay=WidgetTree->ConstructWidget<UOverlay>();WidgetTree->RootWidget=Overlay;
    Image=WidgetTree->ConstructWidget<UImage>();
    Image->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* PreviewSlot=Overlay->AddChildToOverlay(Image);
    // Material brushes keep their small default desired size. Fill the reader's
    // 1400x1100 design surface; its parent ScaleBox preserves the book's aspect.
    PreviewSlot->SetHorizontalAlignment(HAlign_Fill);PreviewSlot->SetVerticalAlignment(VAlign_Fill);
    LoadingText=WidgetTree->ConstructWidget<UTextBlock>();LoadingText->SetFont(GunsmithUI::TextFont(24));
    LoadingText->SetText(FText::FromString(TEXT("正在打开配方手册…")));
    auto* LoadingSlot=Overlay->AddChildToOverlay(LoadingText);LoadingSlot->SetHorizontalAlignment(HAlign_Center);LoadingSlot->SetVerticalAlignment(VAlign_Center);
    LoadingText->SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UColdSteelAlchemyBookPreviewWidget::Configure(const TArray<FAlchemyRecipe>& Recipes,const FAlchemyRecipe& Selected,int32 Spread,bool PublicPageAudio)
{
    if(bReleased)return;
    bClosed=false;
    if(LoadingText&&!Manual){LoadingText->SetText(FText::FromString(TEXT("正在打开配方手册…")));LoadingText->SetVisibility(ESlateVisibility::HitTestInvisible);}
    CancelInteraction();Chapters=Recipes;Contents.Reset();IndexEntries.Reset();RequestedPage=0;
    bPublicPageAudio=PublicPageAudio;BenchRecipe=Selected.Id;BenchSpread=Spread;
    // A paid older batch keeps its own recipe snapshot in the relevant chapter.
    int32 SelectedChapter=Chapters.IndexOfByPredicate([&Selected](const FAlchemyRecipe& R){return R.Id==Selected.Id;});
    if(SelectedChapter==INDEX_NONE)SelectedChapter=Chapters.Add(Selected);else Chapters[SelectedChapter]=Selected;
    const int32 IndexSpreads=FMath::Max(1,FMath::DivideAndRoundUp(Chapters.Num(),8));
    for(int32 Page=0;Page<IndexSpreads;++Page)Contents.Add({INDEX_NONE,Page});
    for(int32 Chapter=0;Chapter<Chapters.Num();++Chapter)
    {
        const int32 Count=UColdSteelAlchemyBookWidget::Pages(Chapters[Chapter]);
        IndexEntries.Add({Chapters[Chapter].Id,Chapters[Chapter].Name,Contents.Num()*2+1,Contents.Num()});
        if(Chapter==SelectedChapter)RequestedPage=Contents.Num()+FMath::Clamp(Spread,0,Count-1);
        for(int32 Page=0;Page<Count;++Page)Contents.Add({Chapter,Page});
    }
    RequestedRecipe=Selected;SettleRemaining=.8f;
    if(Manual){Manual->SetView(ReaderView(RequestedPage),false);UpdateBookmarks();return;}
    if(Loading||bClosed)return;
    LoadAge=0;
    Loading=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{ManualComposite,ManualEnvironment,PaperAudio},FStreamableDelegate::CreateUObject(this,&ThisClass::Loaded));
}
void UColdSteelAlchemyBookPreviewWidget::Loaded()
{
    if(bClosed)return;
    PaperSound=Cast<USoundBase>(PaperAudio.ResolveObject());
    auto* Material=Cast<UMaterialInterface>(ManualComposite.ResolveObject());auto* Environment=Cast<UTextureCube>(ManualEnvironment.ResolveObject());
    if(!Material||!Environment){LoadingText->SetText(FText::FromString(TEXT("手册展示资源未就绪，请重新进入工作台。")));return;}
    FString Reason;
    if(!Studio)Studio=FColdSteelPreviewScene::TryCreate(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(false).SetLightBrightness(3.2f).SetSkyBrightness(.85f),Reason);
    if(!Studio){LoadingText->SetText(FText::FromString(TEXT("手册展示暂不可用，请重新进入工作台。")));return;}
    Studio->ResumeRendering();
    Studio->SetSkyCubemap(Environment);Studio->SetLightDirection(FRotator(-48,-32,0));Studio->DirectionalLight->SetForwardShadingPriority(1);Studio->DirectionalLight->SetLightSourceAngle(8.f);
    Target=NewObject<UTextureRenderTarget2D>(this);Target->RenderTargetFormat=RTF_RGBA16f;Target->ClearColor=FLinearColor(0,0,0,1);Target->InitAutoFormat(1400,1100);
    Mask=NewObject<UTextureRenderTarget2D>(this);Mask->RenderTargetFormat=RTF_RGBA8;Mask->ClearColor=FLinearColor(0,0,0,1);Mask->InitAutoFormat(1400,1100);
    Composite=UMaterialInstanceDynamic::Create(Material,this);Composite->SetTextureParameterValue(TEXT("PreviewTexture"),Target);Composite->SetTextureParameterValue(TEXT("PreviewCoverage"),Mask);
    Image->SetBrushFromMaterial(Composite);
    const FTransform View((ManualAim-ManualEye).Rotation(),ManualEye);
    auto MakeCapture=[this,&View](UTextureRenderTarget2D* Texture,bool Color)
    {
        auto* C=NewObject<USceneCaptureComponent2D>(this);
        C->TextureTarget=Texture;C->CaptureSource=Color?SCS_FinalToneCurveHDR:SCS_SceneColorHDR;
        C->ProjectionType=ECameraProjectionMode::Orthographic;C->OrthoWidth=ViewWidth;
        C->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;C->bCaptureEveryFrame=false;C->bCaptureOnMovement=false;
        C->ShowFlags.SetAtmosphere(false);C->ShowFlags.SetFog(false);C->ShowFlags.SetVolumetricFog(false);C->ShowFlags.SetMotionBlur(false);C->ShowFlags.SetBloom(false);
        C->ShowFlags.SetTemporalAA(false);C->ShowFlags.SetLighting(Color);C->ShowFlags.SetDynamicShadows(Color);
        C->PostProcessSettings.bOverride_AutoExposureMethod=true;C->PostProcessSettings.AutoExposureMethod=AEM_Manual;
        C->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;C->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
        C->PostProcessSettings.bOverride_AutoExposureBias=true;C->PostProcessSettings.AutoExposureBias=0;
        if(!Color)C->bUseRayTracingIfEnabled=false;
        Studio->AddComponent(C,View);return C;
    };
    Capture=MakeCapture(Target,true);Coverage=MakeCapture(Mask,false);
    Manual=NewObject<UAlchemyManualComponent>(this);Studio->AddComponent(Manual,FTransform::Identity);
    Manual->SetOpen(true);Manual->SetView(ReaderView(RequestedPage),false);UpdateBookmarks();Manual->Initialize(GetWorld());Studio->UpdateCaptureContents();
}
void UColdSteelAlchemyBookPreviewWidget::FrameBook()
{
    const FRotationMatrix Camera((ManualAim-ManualEye).Rotation());
    const FVector Right=Camera.GetUnitAxis(EAxis::Y),Up=Camera.GetUnitAxis(EAxis::Z);
    FBox Projected(ForceInit);
    for(auto Part:Manual->Meshes())
    {
        // Only the open binding and bookmarks frame the view. The hidden closed
        // book and animated leaf must not change the camera while turning.
        if(!Part->IsVisible()||!Part->GetStaticMesh())continue;
        const FBox Box=Part->GetStaticMesh()->GetBoundingBox();
        for(int32 Corner=0;Corner<8;++Corner)
        {
            const FVector Local(Corner&1?Box.Max.X:Box.Min.X,Corner&2?Box.Max.Y:Box.Min.Y,Corner&4?Box.Max.Z:Box.Min.Z);
            const FVector P=Part->GetComponentTransform().TransformPosition(Local)-ManualEye;
            Projected+=FVector(P|Right,P|Up,0);
        }
    }
    if(!Projected.IsValid)return;
    const FVector Size=Projected.GetSize(),Center=Projected.GetCenter();
    ViewWidth=FMath::Max(Size.X,Size.Y*ManualAspect)/.985f;
    ViewEye=ManualEye+Right*Center.X+Up*Center.Y;
    for(auto* C:{Capture.Get(),Coverage.Get()}){C->OrthoWidth=ViewWidth;C->SetWorldLocation(ViewEye);}
}
void UColdSteelAlchemyBookPreviewWidget::ResizeCapture(const FGeometry& Geometry)
{
    // Use actual display pixels, with a bounded 2044x1606 maximum and coarse
    // steps so dragging a window does not reallocate a target every pixel.
    const float Pixels=FVector2D::Distance(Geometry.LocalToAbsolute(FVector2D(Geometry.GetLocalSize().X,0)),Geometry.LocalToAbsolute(FVector2D::ZeroVector));
    const int32 Width=FMath::Clamp(FMath::CeilToInt(Pixels/56.f)*56,1400,2044);
    const FIntPoint Wanted(Width,Width*11/14);
    if(Wanted==CaptureSize)return;
    CaptureSize=Wanted;Target->ResizeTarget(Wanted.X,Wanted.Y);Mask->ResizeTarget(Wanted.X,Wanted.Y);SettleRemaining=.3f;
}
void UColdSteelAlchemyBookPreviewWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);if(bClosed)return;
    if(!Manual||!Manual->Ready())
    {
        LoadAge+=Delta;
        if((Manual&&Manual->Failed())||LoadAge>20)LoadingText->SetText(FText::FromString(TEXT("手册资源加载未完成，请放下后重新进入工作台。")));
        return;
    }
    if(!bPrepared)
    {
        for(auto Part:Manual->Meshes()){Capture->ShowOnlyComponents.Add(Part.Get());Coverage->ShowOnlyComponents.Add(Part.Get());}
        for(auto Leaf:Manual->Pages()){Capture->ShowOnlyComponents.Add(Leaf.Get());Coverage->ShowOnlyComponents.Add(Leaf.Get());}
        FrameBook();
        bPrepared=true;SettleRemaining=1;LoadingText->SetVisibility(ESlateVisibility::Collapsed);
    }
    ResizeCapture(Geometry);
    if(bPointerHeld&&PressedBookmark==INDEX_NONE&&!bDraggingPage&&FPlatformTime::Seconds()-PressTime>=.16)BeginReaderDrag();
    const bool Turn=Manual->Advance(Delta);
    CaptureClock+=Delta;
    if((Turn||SettleRemaining>0)&&CaptureClock>=1.f/30.f)
    {
        // This private world does not tick. Submit changed mesh transforms before
        // requesting the two captures; there is no GPU readback or rendering flush.
        CaptureClock=0;Studio->GetWorld()->SendAllEndOfFrameUpdates();Capture->CaptureScene();Coverage->CaptureScene();
    }
    SettleRemaining=FMath::Max(0.f,SettleRemaining-Delta);
    if(Turn)SettleRemaining=.12f;
}
void UColdSteelAlchemyBookPreviewWidget::ReleasePreview(bool Final)
{
    bClosed=true;bReleased|=Final;CancelInteraction();if(Final)OnPageChanged.Unbind();
    if(Loading)Loading->CancelHandle();Loading.Reset();
    if(Manual){if(Studio)Studio->RemoveComponent(Manual);Manual->DestroyComponent();Manual=nullptr;}
    for(auto* C:{Capture.Get(),Coverage.Get()})if(C){C->TextureTarget=nullptr;C->ShowOnlyComponents.Reset();if(Studio)Studio->RemoveComponent(C);C->DestroyComponent();}
    Capture=nullptr;Coverage=nullptr;if(Image)Image->SetBrush(FSlateBrush());Composite=nullptr;Target=nullptr;Mask=nullptr;
    Chapters.Reset();Contents.Reset();IndexEntries.Reset();PaperSound=nullptr;
    bPrepared=false;RequestedPage=0;RequestedRecipe={};CaptureClock=SettleRemaining=LoadAge=0;
    CaptureSize=FIntPoint(1400,1100);ViewWidth=40.f;ViewEye=ManualEye;
    if(Studio)Studio->SuspendRendering();
}
void UColdSteelAlchemyBookPreviewWidget::NativeDestruct(){ReleasePreview();Super::NativeDestruct();}

FVector UColdSteelAlchemyBookPreviewWidget::BookPoint(const FGeometry& G,const FVector2D& Screen,float PlaneZ) const
{
    if(G.GetLocalSize().X<=0||G.GetLocalSize().Y<=0)return FVector(MAX_flt);
    const FVector2D P=G.AbsoluteToLocal(Screen)/G.GetLocalSize();
    const FRotationMatrix Camera((ManualAim-ManualEye).Rotation());
    const FVector Direction=Camera.GetUnitAxis(EAxis::X);
    const FVector Origin=ViewEye+Camera.GetUnitAxis(EAxis::Y)*((P.X-.5)*ViewWidth)+Camera.GetUnitAxis(EAxis::Z)*((.5-P.Y)*ViewWidth/ManualAspect);
    return Origin+Direction*((PlaneZ-Origin.Z)/Direction.Z);
}
int32 UColdSteelAlchemyBookPreviewWidget::BookmarkAt(const FVector& P) const
{
    using namespace AlchemyManualGeometry;
    if(P.Y<BookmarkFrontY-.22f||P.Y>BookmarkBackY+.15f)return INDEX_NONE;
    if(FMath::Abs(P.X+BookmarkCenter)<BookmarkHalfWidth+.2f)return 0;
    if(FMath::Abs(P.X-BookmarkCenter)<BookmarkHalfWidth+.2f)return 1;
    return INDEX_NONE;
}
int32 UColdSteelAlchemyBookPreviewWidget::ContentsAt(const FVector& P) const
{
    if(!Contents.IsValidIndex(RequestedPage)||Contents[RequestedPage].Chapter!=INDEX_NONE)return INDEX_NONE;
    using namespace AlchemyManualLayout;
    const int32 Side=P.X<0?0:1;
    const float X=(P.X/AlchemyManualGeometry::Width+(Side==0?1:0))*PageWidth;
    const float Y=(P.Y/AlchemyManualGeometry::Height+.5f)*PageHeight;
    const float Left=Side==0?82.f:112.f;
    if(X<Left||X>Left+ContentWidth||Y<Top+ContentsHeading)return INDEX_NONE;
    const int32 Row=FMath::FloorToInt((Y-Top-ContentsHeading)/ContentsRow);
    if(Row<0||Row>=ContentsRows)return INDEX_NONE;
    const int32 Index=Contents[RequestedPage].Spread*8+Side*4+Row;
    return IndexEntries.IsValidIndex(Index)?IndexEntries[Index].TargetSpread:INDEX_NONE;
}
FAlchemyManualView UColdSteelAlchemyBookPreviewWidget::ReaderView(int32 Page) const
{
    FAlchemyManualView View;if(!Contents.IsValidIndex(Page))return View;
    const auto& Entry=Contents[Page];View.Spread=Entry.Spread;View.FirstFolio=Page*2+1;View.TotalFolios=Contents.Num()*2;
    View.bContents=Entry.Chapter==INDEX_NONE;
    if(View.bContents)View.Chapters=IndexEntries;else View.Recipe=Chapters[Entry.Chapter];
    return View;
}
void UColdSteelAlchemyBookPreviewWidget::UpdateBookmarks()
{if(Manual)Manual->SetBookmarkState(HoveredBookmark,PressedBookmark,RequestedPage==0,RequestedPage==Contents.Num()-1);}
void UColdSteelAlchemyBookPreviewWidget::PageSound(bool Commit)
{
    // The public bench already emits the same sound when its local recipe page
    // changes. Other chapters and the contents exist only in this private reader.
    if(Commit&&bPublicPageAudio&&RequestedRecipe.Id==BenchRecipe&&CurrentSpread()<=7&&CurrentSpread()!=BenchSpread){BenchSpread=CurrentSpread();return;}
    if(PaperSound)UGameplayStatics::PlaySound2D(this,PaperSound,Commit?.24f:.09f,FMath::FRandRange(.96f,1.04f));
}
void UColdSteelAlchemyBookPreviewWidget::BeginReaderDrag()
{
    const int32 Next=RequestedPage+DragDirection;
    // Holding a directory row is still a click until the pointer actually moves.
    if(bClosed||!bPointerHeld||PressedEntry!=INDEX_NONE||!Manual||!Contents.IsValidIndex(Next))return;
    bDraggingPage=Manual->BeginPageDrag(ReaderView(Next),DragDirection);
    if(bDraggingPage){PressedEntry=INDEX_NONE;Manual->DragPage(DragProgress);SettleRemaining=.3f;SetCursor(EMouseCursor::GrabHandClosed);}
}
void UColdSteelAlchemyBookPreviewWidget::TurnTo(int32 Page)
{
    if(bClosed||!Manual||!Manual->Ready()||Manual->Turning()||Contents.IsEmpty())return;
    Page=FMath::Clamp(Page,0,Contents.Num()-1);
    if(Page==RequestedPage)return;
    const int32 Direction=Page>RequestedPage?1:-1;
    RequestedPage=Page;const auto View=ReaderView(Page);RequestedRecipe=View.Recipe;
    Manual->SetView(View,true,Direction);UpdateBookmarks();SettleRemaining=.8f;PageSound(true);OnPageChanged.ExecuteIfBound(Page);
}
int32 UColdSteelAlchemyBookPreviewWidget::CurrentSpread() const
{return Contents.IsValidIndex(RequestedPage)?Contents[RequestedPage].Spread:0;}
void UColdSteelAlchemyBookPreviewWidget::Flip(int32 Direction)
{CancelInteraction();TurnTo(RequestedPage+Direction);}
FReply UColdSteelAlchemyBookPreviewWidget::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    if(E.GetEffectingButton()!=EKeys::LeftMouseButton)return FReply::Handled();
    if(bClosed||!bPrepared||!Manual||!Manual->Ready()||Manual->Turning())return FReply::Handled();
    const FVector P=BookPoint(G,E.GetScreenSpacePosition(),AlchemyManualGeometry::LeafHeight);
    PressedBookmark=BookmarkAt(BookPoint(G,E.GetScreenSpacePosition(),AlchemyManualGeometry::BookmarkPlaneZ));
    PressedEntry=ContentsAt(P);HoveredBookmark=PressedBookmark;UpdateBookmarks();
    if(PressedBookmark==INDEX_NONE&&(FMath::Abs(P.X)>15.5f||FMath::Abs(P.Y)>12.1f))return FReply::Handled();
    PressPosition=PointerPosition=E.GetScreenSpacePosition();PressTime=MotionTime=FPlatformTime::Seconds();DragProgress=DragVelocity=0;DragDirection=P.X>0?1:-1;bPointerHeld=true;
    return FReply::Handled().CaptureMouse(TakeWidget());
}
FReply UColdSteelAlchemyBookPreviewWidget::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E)
{
    if(bClosed||!bPrepared||!Manual||!Manual->Ready())return FReply::Handled();
    PointerPosition=E.GetScreenSpacePosition();
    HoveredBookmark=BookmarkAt(BookPoint(G,PointerPosition,AlchemyManualGeometry::BookmarkPlaneZ));UpdateBookmarks();
    if(!bPointerHeld)
    {
        const FVector Point=BookPoint(G,E.GetScreenSpacePosition(),AlchemyManualGeometry::LeafHeight);
        const bool Page=FMath::Abs(Point.X)<15.5f&&FMath::Abs(Point.Y)<12.1f;
        SetCursor(HoveredBookmark!=INDEX_NONE||ContentsAt(Point)!=INDEX_NONE?EMouseCursor::Hand:Page?EMouseCursor::GrabHand:EMouseCursor::Default);
        return FReply::Handled();
    }
    if(!E.IsMouseButtonDown(EKeys::LeftMouseButton)){CancelInteraction();return FReply::Handled();}
    if(PressedBookmark!=INDEX_NONE)return FReply::Handled();
    const FVector2D Start=G.AbsoluteToLocal(PressPosition),Now=G.AbsoluteToLocal(E.GetScreenSpacePosition());
    const float Distance=(Start.X-Now.X)*DragDirection;
    if(FVector2D::Distance(Start,Now)>6)PressedEntry=INDEX_NONE;
    const double Clock=FPlatformTime::Seconds();
    if(!bDraggingPage&&Clock-PressTime>=.16)BeginReaderDrag();
    const float Progress=FMath::Clamp(Distance/float(G.GetLocalSize().X*.62),0.f,1.f);
    DragVelocity=FMath::Lerp(DragVelocity,(Progress-DragProgress)/float(FMath::Max(.008,Clock-MotionTime)),.65f);
    DragProgress=Progress;MotionTime=Clock;
    if(bDraggingPage)
    {
        Manual->DragPage(DragProgress);SettleRemaining=.12f;SetCursor(EMouseCursor::GrabHandClosed);
    }
    return FReply::Handled();
}
FReply UColdSteelAlchemyBookPreviewWidget::NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E)
{
    if(bClosed)return FReply::Handled().ReleaseMouseCapture();
    if(E.GetEffectingButton()!=EKeys::LeftMouseButton||!bPointerHeld)return FReply::Handled();
    bPointerHeld=false;
    if(bDraggingPage)
    {
        bDraggingPage=false;const bool Recent=FPlatformTime::Seconds()-MotionTime<.12;
        const bool Commit=DragProgress>=.32f||(DragProgress>=.08f&&Recent&&DragVelocity>.9f);Manual->ReleasePage(Commit);
        if(Commit){RequestedPage+=DragDirection;RequestedRecipe=ReaderView(RequestedPage).Recipe;PageSound(true);OnPageChanged.ExecuteIfBound(RequestedPage);}
        else if(DragProgress>.02f)PageSound(false);
    }
    else if(PressedBookmark!=INDEX_NONE&&BookmarkAt(BookPoint(G,E.GetScreenSpacePosition(),AlchemyManualGeometry::BookmarkPlaneZ))==PressedBookmark)TurnTo(PressedBookmark==0?0:Contents.Num()-1);
    else if(PressedEntry!=INDEX_NONE&&ContentsAt(BookPoint(G,E.GetScreenSpacePosition(),AlchemyManualGeometry::LeafHeight))==PressedEntry)TurnTo(PressedEntry);
    PressedBookmark=PressedEntry=INDEX_NONE;UpdateBookmarks();SetCursor(HoveredBookmark!=INDEX_NONE?EMouseCursor::Hand:EMouseCursor::GrabHand);return FReply::Handled().ReleaseMouseCapture();
}
void UColdSteelAlchemyBookPreviewWidget::CancelInteraction()
{
    bPointerHeld=false;PressedBookmark=PressedEntry=HoveredBookmark=INDEX_NONE;UpdateBookmarks();SetCursor(EMouseCursor::Default);
    if(bDraggingPage&&Manual)Manual->ReleasePage(false);bDraggingPage=false;
    if(HasMouseCapture()&&FSlateApplication::IsInitialized())FSlateApplication::Get().ReleaseAllPointerCapture();
}
void UColdSteelAlchemyBookPreviewWidget::NativeOnMouseCaptureLost(const FCaptureLostEvent& E)
{bPointerHeld=false;PressedBookmark=PressedEntry=INDEX_NONE;UpdateBookmarks();if(bDraggingPage&&Manual)Manual->ReleasePage(false);bDraggingPage=false;Super::NativeOnMouseCaptureLost(E);}
void UColdSteelAlchemyBookPreviewWidget::NativeOnMouseLeave(const FPointerEvent& E)
{HoveredBookmark=INDEX_NONE;UpdateBookmarks();if(!bPointerHeld)SetCursor(EMouseCursor::Default);Super::NativeOnMouseLeave(E);}
