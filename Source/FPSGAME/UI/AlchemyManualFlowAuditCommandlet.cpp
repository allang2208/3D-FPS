#include "AlchemyManualFlowAuditCommandlet.h"
#include "AlchemyManualLayout.h"
#include "ColdSteelAlchemyBookWidget.h"
#include "ColdSteelAlchemyWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelPreviewScene.h"
#include "../Building/AlchemyManualComponent.h"
#include "../Building/AlchemyManualGeometry.h"
#include "../Building/AlchemySystem.h"
#include "../Building/BookLeafComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Components/VerticalBox.h"
#include "Components/Border.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Async/TaskGraphInterfaces.h"
#include "InputCoreTypes.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Engine/StreamableManager.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Framework/Application/SlateApplication.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Misc/ScopeExit.h"
#include "Tickable.h"
#include "RenderingThread.h"
#include "UObject/StrongObjectPtr.h"
#if WITH_EDITOR
#include "Interfaces/ISlateRHIRendererModule.h"
#include "Modules/ModuleManager.h"
#endif

int32 UAlchemyManualFlowAuditCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    if(!FSlateApplication::IsInitialized())
    {
        auto& Module=FModuleManager::LoadModuleChecked<ISlateRHIRendererModule>(TEXT("SlateRHIRenderer"));
        FSlateApplication::InitializeAsStandaloneApplication(Module.CreateSlateRHIRenderer());
    }
#else
    return 2;
#endif
    FString Report;int32 Checks=0,Failures=0;
    const auto Check=[&](bool Pass,const FString& Label)
    {
        ++Checks;Failures+=!Pass;const FString Line=(Pass?TEXT("PASS "):TEXT("FAIL "))+Label;
        Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("MANUAL_FLOW %s"),*Line);return Pass;
    };
    FString Output=FPaths::ProjectSavedDir()/TEXT("AlchemyManualFlowAudit/report.txt");
    FParse::Value(*Params,TEXT("Output="),Output);
    ON_SCOPE_EXIT
    {
        Report+=FString::Printf(TEXT("checks=%d failures=%d\n"),Checks,Failures);
        FFileHelper::SaveStringToFile(Report,*Output);
        UE_LOG(LogTemp,Display,TEXT("MANUAL_FLOW COMPLETE checks=%d failures=%d"),Checks,Failures);
    };
    // No gameplay map or user's save is opened. All subsystem access is tied to
    // this unique audit profile; its audit flag disables ordinary persistence.
    const FString OriginalCommandLine=FCommandLine::Get();
    const FString Profile=TEXT("ManualFlowAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(OriginalCommandLine+TEXT(" -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("ManualFlowAuditWorld"));
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*OriginalCommandLine);};
    auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    auto* System=GI->GetSubsystem<UColdSteelAlchemySystem>();
    if(!Check(Model&&Model->IsAudit()&&Model->ProfileSlot()==TEXT("ColdSteel_")+Profile&&System,TEXT("isolated profile and recipe system")))return 2;
    auto* Player=NewObject<ULocalPlayer>(GEngine);GI->AddLocalPlayer(Player,FPlatformUserId::CreateFromInternalId(0));
    // Native UUserWidget initialization needs a valid player/controller pair.
    // A bare engine controller supplies context without spawning the game pawn.
    auto* Controller=World->SpawnActor<APlayerController>();
    Controller->Player=Player;Player->PlayerController=Controller;
    World->AddController(Controller);
    if(!Check(FLocalPlayerContext(Player,World).IsValid(),TEXT("temporary world registers a valid UI player context")))return 2;
    const auto& Recipes=System->Recipes();
    if(!Check(!Recipes.IsEmpty(),TEXT("load real recipe catalog")))return 2;
    TStrongObjectPtr<UColdSteelAlchemyWidget> Host(CreateWidget<UColdSteelAlchemyWidget>(GI));
    auto* Reader=Host->BookPage.Get();
    if(!Check(Reader!=nullptr,TEXT("workbench constructs physical reader")))return 2;
    const TSharedRef<SWidget> HostSlate=Host->TakeWidget();
    ON_SCOPE_EXIT {Host->EndSession();Host->ReleaseSlateResources(true);FlushRenderingCommands();Host.Reset();};
    const FGeometry Geometry=FGeometry::MakeRoot(FVector2D(1400,1100),FSlateLayoutTransform());
    const auto Pump=[]()
    {
        FlushAsyncLoading();
        FTickableGameObject::TickObjects(nullptr,LEVELTICK_All,false,.02f);
        FTaskGraphInterface::Get().ProcessThreadUntilIdle(ENamedThreads::GameThread);
        ++GFrameCounter;
    };
    const auto Ready=[&]()
    {
        for(int32 I=0;I<40&&(!Reader->Manual||!Reader->Manual->Ready());++I)Pump();
        Reader->NativeTick(Geometry,.04f);FlushRenderingCommands();
        return Reader->Manual&&Reader->Manual->Ready()&&Reader->bPrepared;
    };
    const auto Finish=[&]() {Reader->NativeTick(Geometry,1.f);FlushRenderingCommands();};
    const auto Screen=[&](const FVector& Point)
    {
        const FRotationMatrix Camera((FVector(0,0,1.7)-FVector(0,8,85)).Rotation());
        const FVector Offset=Point-Reader->ViewEye;
        return FVector2D((.5+(Offset|Camera.GetUnitAxis(EAxis::Y))/Reader->ViewWidth)*1400,
            (.5-(Offset|Camera.GetUnitAxis(EAxis::Z))* (1400.f/1100.f)/Reader->ViewWidth)*1100);
    };
    const auto Mouse=[](FVector2D Position,bool Down)
    {return FPointerEvent(0,Position,Position,Down?TSet<FKey>{EKeys::LeftMouseButton}:TSet<FKey>{},EKeys::LeftMouseButton,0,FModifierKeysState());};
    const auto Click=[&](FVector Point,bool Hold=false)
    {
        const auto P=Screen(Point);Reader->NativeOnMouseButtonDown(Geometry,Mouse(P,true));
        if(Hold){Reader->PressTime-=.3;Reader->NativeTick(Geometry,.01f);}
        Reader->NativeOnMouseButtonUp(Geometry,Mouse(P,false));Finish();
    };
    const auto Key=[&](FKey K){Host->NativeOnKeyDown(Geometry,FKeyEvent(K,FModifierKeysState(),0,false,0,0));};

    Host->Book(true);
    if(!Check(Ready(),TEXT("open from workbench through async assets and first render")))return 1;
    Check(Reader->Manual->Parts.Num()==3&&Reader->Manual->Leaves.Num()==3&&Reader->Manual->PaperMaterials.Num()==6&&Reader->Manual->PageTargets.Num()==2,
        TEXT("open creates complete model, paper materials and two page targets"));
    Check(Reader->Manual->PageWidget&&Reader->Manual->PageWidget->LeftPage&&Reader->Manual->PageWidget->RightPage&&Reader->Manual->PageWidget->LeftPage->GetChildrenCount()>0&&Reader->Manual->PageWidget->RightPage->GetChildrenCount()>0,
        TEXT("first spread contains both printed pages"));
    Check(Reader->IndexEntries.Num()==Recipes.Num(),TEXT("directory includes every recipe"));
    for(int32 I=0;I<Reader->Manual->Leaves.Num();++I)
    {
        auto* Leaf=Reader->Manual->Leaves[I].Get();
        Check(Leaf->GetBoneIndex(TEXT("Page_30"))!=INDEX_NONE&&Leaf->GetMaterial(Leaf->GetMaterialIndex(TEXT("M_BookPages")))!=nullptr,
            FString::Printf(TEXT("sheet %d has full bone chain and edge material"),I));
        Check(Reader->Capture->ShowOnlyComponents.Contains(Leaf)&&Reader->Coverage->ShowOnlyComponents.Contains(Leaf),
            FString::Printf(TEXT("sheet %d is included in color and coverage capture"),I));
        for(bool Front:{false,true})
        {
            auto* Mat=Reader->Manual->PaperMaterials[I*2+(Front?1:0)].Get();
            Check(Mat&&Mat->Parent&&Mat->Parent->GetName()==TEXT("M_BookLeafPaper"),
                FString::Printf(TEXT("sheet %d %s has actual paper parent"),I,Front?TEXT("front"):TEXT("back")));
        }
    }
    CollectGarbage(RF_NoFlags);
    Check(Reader->Manual->Ready()&&Reader->Manual->Leaves.Num()==3&&Reader->Manual->PageTargets.Num()==2,TEXT("GC preserves active sheet objects and targets"));
    const auto RetainedView=Reader->Manual->DisplayedView;
    Reader->Manual->SetOpen(false);
    Check(Reader->Manual->PageTargets.IsEmpty()&&!Reader->Manual->PageWidget,TEXT("tabletop close releases printed pages"));
    Reader->Manual->SetOpen(true);FlushRenderingCommands();
    Check(Reader->Manual->PageTargets.Num()==2&&Reader->Manual->bHasDisplayedView&&Reader->Manual->DisplayedView.SamePage(RetainedView),
        TEXT("tabletop reopen redraws unchanged recipe without SetView"));
    const int32 Total=Reader->Contents.Num();const FName Selection=Host->Selection;
    // Inspect real mesh/material identities during both turn directions. A
    // matching page number alone cannot detect a hidden-sheet handoff.
    for(int32 Direction:{1,-1})
    {
        Reader->TurnTo(Direction>0?1:2);Finish();auto* Manual=Reader->Manual.Get();
        const int32 Moving=Direction>0?Manual->RightLeaf:Manual->LeftLeaf;
        auto* Sheet=Manual->Leaves[Moving].Get();
        const int32 BeforeTarget=Manual->CurrentTarget;
        Check(Manual->BeginPageDrag(Reader->ReaderView(Direction>0?2:1),Direction),TEXT("physical sheet begins directional drag"));
        UTexture* Faces[2]={};FLinearColor Regions[2];
        for(int32 Face=0;Face<2;++Face)
        {
            auto* Mat=Manual->PaperMaterials[Moving*2+Face].Get();
            Faces[Face]=Mat->K2_GetTextureParameterValue(TEXT("PageTexture"));Regions[Face]=Mat->K2_GetVectorParameterValue(TEXT("PageOffset"));
        }
        Manual->DragPage(.5f);
        const FVector Tip=Sheet->GetBoneLocationByName(TEXT("Page_28"),EBoneSpaces::ComponentSpace);
        Check(Faces[0]&&Faces[1]&&Faces[0]!=Faces[1]&&Tip.Z>5.f&&FMath::Abs(Tip.X)<6.f,TEXT("both print faces remain on a raised, curved sheet"));
        Manual->ReleasePage(true);Manual->Advance(1.f);
        bool Same=Sheet->IsVisible()&&Manual->Leaves[Direction>0?Manual->LeftLeaf:Manual->RightLeaf]==Sheet&&Manual->CurrentTarget!=BeforeTarget;
        for(int32 Face=0;Face<2;++Face)
        {
            UTexture* After=nullptr;FLinearColor Region;
            auto* Mat=Manual->PaperMaterials[Moving*2+Face].Get();After=Mat->K2_GetTextureParameterValue(TEXT("PageTexture"));Region=Mat->K2_GetVectorParameterValue(TEXT("PageOffset"));
            Same&=After==Faces[Face]&&Region==Regions[Face];
        }
        Check(Same,TEXT("landed sheet keeps the same object, texture bindings and UV regions"));
        Reader->RequestedPage=Direction>0?2:1;
    }
    // Separate reader instances model two local clients without sharing a
    // mutable widget, page target or requested-page state.
    TStrongObjectPtr<UColdSteelAlchemyBookPreviewWidget> Other(CreateWidget<UColdSteelAlchemyBookPreviewWidget>(GI));
    const auto OtherSlate=Other->TakeWidget();Other->Configure(Recipes,Recipes[0],0);
    for(int32 I=0;I<40&&(!Other->Manual||!Other->Manual->Ready());++I)Pump();
    Other->NativeTick(Geometry,.04f);
    const int32 OtherPage=Other->RequestedPage;
    Reader->TurnTo(Total-1);Finish();
    Check(Other->Manual&&Other->Manual->Ready()&&Other->RequestedPage==OtherPage&&Other->Manual->PageTargets[0]!=Reader->Manual->PageTargets[0],TEXT("independent readers do not share pages or render targets"));
    Other->ReleasePreview();Other->ReleaseSlateResources(true);Other.Reset();
    // Render every actual spread in both directions, including chapter boundaries.
    for(int32 Direction:{1,-1})for(int32 I=0;I<Total;++I)
    {
        const int32 Page=Direction>0?I:Total-1-I;
        Reader->TurnTo(Page);Finish();
        Check(Reader->RequestedPage==Page&&Reader->Manual->DisplayedView.SamePage(Reader->ReaderView(Page))&&!Reader->Manual->Turning(),
            FString::Printf(TEXT("%s spread %d/%d completes"),Direction>0?TEXT("forward"):TEXT("reverse"),Page+1,Total));
    }
    Reader->TurnTo(0);Finish();Key(EKeys::Left);Check(Reader->RequestedPage==0,TEXT("first spread blocks backward key"));
    using namespace AlchemyManualGeometry;
    Click(FVector(BookmarkCenter,(BookmarkFrontY+BookmarkBackY)*.5f,BookmarkPlaneZ));
    Check(Reader->RequestedPage==Total-1,TEXT("right bookmark jumps to last spread"));
    Key(EKeys::Right);Check(Reader->RequestedPage==Total-1,TEXT("last spread blocks forward key"));
    Click(FVector(-BookmarkCenter,(BookmarkFrontY+BookmarkBackY)*.5f,BookmarkPlaneZ));
    Check(Reader->RequestedPage==0&&Reader->Manual->DisplayedView.bContents,TEXT("left bookmark jumps to contents"));
    for(int32 Entry=0;Entry<Reader->IndexEntries.Num();++Entry)
    {
        Reader->TurnTo(Entry/8);Finish();
        const int32 Side=Entry%8/4,Row=Entry%4;
        const float X=(Side?112.f:82.f)+AlchemyManualLayout::ContentWidth*.5f;
        const float Y=AlchemyManualLayout::Top+AlchemyManualLayout::ContentsHeading+(Row+.5f)*AlchemyManualLayout::ContentsRow;
        const FVector Point((X/1024.f-(Side?0.f:1.f))*Width,(Y/1536.f-.5f)*Height,LeafHeight);
        const auto Target=Reader->IndexEntries[Entry];
        Click(Point,true);
        Check(Reader->RequestedPage==Target.TargetSpread&&Reader->CurrentRecipeId()==Target.Recipe,
            FString::Printf(TEXT("directory row %d remains clickable after a long hold"),Entry+1));
    }
    const auto Drag=[&](float Progress)
    {
        Reader->TurnTo(1);Finish();
        const FVector2D Start=Screen(FVector(Width*.98f,0,LeafHeight));
        Reader->NativeOnMouseButtonDown(Geometry,Mouse(Start,true));Reader->PressTime-=.3;
        const FVector2D End=Start-FVector2D(1400*.62*Progress,0);
        Reader->NativeOnMouseMove(Geometry,Mouse(End,true));return End;
    };
    auto End=Drag(.5f);Check(Reader->bDraggingPage,TEXT("long press and motion begins drag"));
    Reader->NativeOnMouseButtonUp(Geometry,Mouse(End,false));Finish();
    Check(Reader->RequestedPage==2&&Reader->Manual->DisplayedView.SamePage(Reader->ReaderView(2)),TEXT("drag commits and prints destination"));
    End=Drag(.12f);Reader->MotionTime-=1.;Reader->NativeOnMouseButtonUp(Geometry,Mouse(End,false));Finish();
    Check(Reader->RequestedPage==1&&Reader->Manual->DisplayedView.SamePage(Reader->ReaderView(1)),TEXT("short drag rolls back without changing recipe or page"));
    Drag(.4f);Reader->NativeOnMouseCaptureLost(FCaptureLostEvent(0,0));Finish();
    Check(!Reader->bPointerHeld&&!Reader->bDraggingPage&&Reader->RequestedPage==1&&!Reader->Manual->Turning(),TEXT("cancelled pointer interaction settles back"));
    Check(Host->Selection==Selection,TEXT("reading other chapters never changes crafting selection"));

    Drag(.4f);TStrongObjectPtr<UAlchemyManualComponent> Retired(Reader->Manual.Get());
    auto* Studio=Reader->Studio.Get();Key(EKeys::Escape);
    Check(!Host->bBook&&Reader->bClosed&&!Reader->Manual&&!Reader->Capture&&!Reader->Coverage&&!Reader->Target&&!Reader->Mask,
        TEXT("Escape during drag releases captures, book and render targets"));
    Check(!Retired->Ready()&&!Retired->Advance(.1f)&&Retired->Parts.IsEmpty(),TEXT("destroyed manual cannot advance into cleared arrays"));
    Reader->Loaded();Reader->Flip(1);Reader->NativeOnMouseMove(Geometry,Mouse(FVector2D::ZeroVector,true));
    Check(!Reader->Manual&&Reader->bClosed,TEXT("late callbacks and input cannot resurrect closed reader"));
    Key(EKeys::B);
    if(!Check(Ready(),TEXT("B reopens after closing during drag")))return 1;
    Check(Reader->Studio.Get()==Studio,TEXT("reopen reuses world shell with restored rendering"));
    Key(EKeys::B);Check(!Host->bBook&&!Reader->Manual,TEXT("B closes and frees reader"));
    Host->Book(true);Host->Book(false);for(int32 I=0;I<3;++I)Pump();
    Check(Reader->bClosed&&!Reader->Manual&&!Reader->Loading,TEXT("closing during async load cancels pending creation"));
    for(int32 I=0;I<3;++I)
    {
        Host->Book(true);if(!Check(Ready(),FString::Printf(TEXT("repeat open %d"),I+1)))return 1;
        Reader->Flip(1);Host->RequestClose();
        Check(Reader->bClosed&&!Reader->Manual&&!Host->bBook,FString::Printf(TEXT("close during automatic turn %d"),I+1));
    }
    Host->EndSession();Reader->ReleasePreview();Reader->ReleasePreview();
    Reader->Configure(Recipes,Recipes[0],0);
    Check(Reader->bReleased&&Reader->bClosed&&!Reader->Loading&&!Reader->OnPageChanged.IsBound(),TEXT("final teardown is idempotent and cannot restart loading"));
    FlushRenderingCommands();
    return Failures?1:0;
}
