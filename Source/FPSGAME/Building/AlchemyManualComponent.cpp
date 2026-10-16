#include "AlchemyManualComponent.h"
#include "AlchemyManualGeometry.h"
#include "AlchemyManualArtwork.h"
#include "BookLeafComponent.h"
#include "../UI/ColdSteelAlchemyBookWidget.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Slate/WidgetRenderer.h"

namespace {
FSoftObjectPath ManualAsset(const TCHAR* Kind,const TCHAR* Name)
{
    const TCHAR* Version=FCString::Strcmp(Name,TEXT("SM_AlchemyManualBookmarks"))==0?TEXT("ManualV6"):
        FCString::Strcmp(Name,TEXT("SM_AlchemyManualBinding"))==0?TEXT("ManualV10"):TEXT("ManualV5");
    return FSoftObjectPath(FString::Printf(TEXT("/Game/Building/PotionWorkbench20261015/%s/%s/%s.%s"),Version,Kind,Name,Name));
}
const TCHAR* ManualMeshes[]={TEXT("SM_AlchemyManualBinding"),TEXT("SM_AlchemyManualClosed"),TEXT("SM_AlchemyManualBookmarks")};
const TCHAR* FeedbackNames[]={TEXT("M_ManualRibbonInteractive"),TEXT("M_ManualClaspInteractive")};
FSoftObjectPath FeedbackAsset(const TCHAR* Name)
{return FSoftObjectPath(FString::Printf(TEXT("/Game/Building/PotionWorkbench20261015/ManualV8/Materials/%s.%s"),Name,Name));}
const FSoftObjectPath LeafTemplate(TEXT("/Game/Building/PotionWorkbench20261015/ManualV9/Meshes/SK_BookLeafTemplate.SK_BookLeafTemplate"));
constexpr float ManualTurnSeconds=.78f;
constexpr float LeafSeparation=.045f,LeafClearance=.08f;
}
void UAlchemyManualComponent::Initialize(UWorld* WidgetWorld)
{
    ContextWorld=WidgetWorld;
    TArray<FSoftObjectPath> Assets;for(auto Name:ManualMeshes)Assets.Add(ManualAsset(TEXT("Meshes"),Name));
    for(auto Name:FeedbackNames)Assets.Add(FeedbackAsset(Name));
    Assets.Add(LeafTemplate);
    AlchemyManualArtwork::Gather(Assets);
    Loading=UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets,FStreamableDelegate::CreateUObject(this,&ThisClass::Loaded));
}
void UAlchemyManualComponent::Loaded()
{
    bLoadFinished=true;if(!IsRegistered()||!ContextWorld.IsValid()||ContextWorld->bIsTearingDown)return;
    for(auto Name:ManualMeshes)if(!ManualAsset(TEXT("Meshes"),Name).ResolveObject())return;
    for(auto Name:FeedbackNames)if(!FeedbackAsset(Name).ResolveObject())return;
    auto* Template=Cast<USkeletalMesh>(LeafTemplate.ResolveObject());if(!Template)return;
    for(auto Name:ManualMeshes)
    {
        auto* Part=NewObject<UStaticMeshComponent>(this);
        Part->SetStaticMesh(Cast<UStaticMesh>(ManualAsset(TEXT("Meshes"),Name).ResolveObject()));
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);Part->SetMobility(EComponentMobility::Movable);
        Part->SetupAttachment(this);Part->RegisterComponentWithWorld(GetWorld());Parts.Add(Part);
    }
    for(int32 I=0;I<3;++I)
    {
        auto* Leaf=NewObject<UBookLeafComponent>(this);Leaves.Add(Leaf);
        Leaf->SetupAttachment(this);Leaf->SetVisibility(false);
        if(!Leaf->InitializeTemplate(Template))return;
        Leaf->RegisterComponentWithWorld(GetWorld());
        for(const auto* Slot:{TEXT("RecipeLeft"),TEXT("RecipeRight")})
        {
            const int32 Index=Leaf->GetMaterialIndex(Slot);if(Index<0)return;
            auto* Material=Leaf->CreateDynamicMaterialInstance(Index);if(!Material)return;
            PaperMaterials.Add(Material);
        }
    }
    BookmarkMaterials.Add(Parts[2]->CreateDynamicMaterialInstance(Parts[2]->GetMaterialIndex(TEXT("ManualRibbonV6")),Cast<UMaterialInterface>(FeedbackAsset(FeedbackNames[0]).ResolveObject())));
    BookmarkMaterials.Add(Parts[2]->CreateDynamicMaterialInstance(Parts[2]->GetMaterialIndex(TEXT("ManualClaspV6")),Cast<UMaterialInterface>(FeedbackAsset(FeedbackNames[1]).ResolveObject())));
    bReady=true;SetOpen(bOpen);
}
void UAlchemyManualComponent::SetOpen(bool Open)
{
    bOpen=Open;if(!bReady)return;
    Parts[0]->SetVisibility(Open);Parts[1]->SetVisibility(!Open);Parts[2]->SetVisibility(Open);
    // Tabletop state may reopen the same recipe/page without another SetView.
    // Closing freed the targets, so restore that retained print view here.
    if(Open&&bHasView&&!bHasDisplayedView)DrawSpread();
    if(!Open)
    {
        FinishTurn(bCommitTurn);for(auto Leaf:Leaves)Leaf->SetVisibility(false);
        // Idle workbenches retain the small mesh assets, not two full page targets.
        for(auto Material:PaperMaterials)Material->SetTextureParameterValue(TEXT("PageTexture"),nullptr);
        PageTargets.Reset();PageWidget=nullptr;DisplayedView=FAlchemyManualView();bHasDisplayedView=false;CurrentTarget=0;
        if(Renderer){BeginCleanup(Renderer);Renderer=nullptr;}
    }
}
void UAlchemyManualComponent::SetRecipe(const FAlchemyRecipe& Recipe,int32 Page,bool Animate,int32 Direction,int32 FirstFolio,int32 FolioCount)
{
    FAlchemyManualView View;View.Recipe=Recipe;View.Spread=FMath::Max(0,Page);View.FirstFolio=FirstFolio;View.TotalFolios=FolioCount;SetView(View,Animate,Direction);
}
void UAlchemyManualComponent::SetView(const FAlchemyManualView& View,bool Animate,int32 Direction)
{
    if(bHasView&&PendingView.SamePage(View)&&bHasDisplayedView&&(!bTurning||bCommitTurn))return;
    FinishTurn(bCommitTurn);PendingView=View;bHasView=true;
    bForward=Direction!=0?Direction>0:View.Spread>DisplayedView.Spread;
    bTurning=Animate&&bHasDisplayedView&&!DisplayedView.SamePage(View)&&!PageTargets.IsEmpty();TurnTime=TurnStart=TurnProgress=0;TurnDuration=ManualTurnSeconds;bPageDrag=false;bCommitTurn=true;
    if(bReady)DrawSpread();
}
void UAlchemyManualComponent::DrawSpread()
{
    if(!bReady||!ContextWorld.IsValid()||ContextWorld->bIsTearingDown||!bOpen)return;
    if(!PageWidget)PageWidget=CreateWidget<UColdSteelAlchemyBookWidget>(ContextWorld.Get());
    if(!PageWidget)return;
    if(!Renderer)Renderer=new FWidgetRenderer(true,true);
    if(PageTargets.IsEmpty())for(int32 I=0;I<2;++I)PageTargets.Add(FWidgetRenderer::CreateTargetFor(FVector2D(2048,1536),TF_Bilinear,true));
    const int32 Next=1-CurrentTarget;
    // Only the previously covered pool member is recycled. Neither currently
    // readable face is rebound, hidden, or drawn over while it turns.
    Leaves[SpareLeaf]->SetVisibility(false);
    PageWidget->Configure(PendingView);
    Renderer->DrawWidget(PageTargets[Next],PageWidget->TakeWidget(),FVector2D(2048,1536),0.f);
    if(bTurning)
    {
        TurningLeaf=bForward?RightLeaf:LeftLeaf;
        StationaryLeaf=bForward?LeftLeaf:RightLeaf;UnderLeaf=SpareLeaf;
        // The opposite face is still hidden here. Once the sheet starts moving
        // both faces keep these bindings through landing and subsequent rest.
        BindFace(TurningLeaf,!bForward,Next,bForward?0:1);
        BindFace(UnderLeaf,bForward,Next,bForward?1:0);
        PoseLeaf(0);Leaves[UnderLeaf]->SetVisibility(true);
    }
    else
    {
        BindFace(LeftLeaf,false,Next,0);BindFace(RightLeaf,true,Next,1);
        PlaceLeaf(LeftLeaf,1);PlaceLeaf(RightLeaf,0);
        Leaves[LeftLeaf]->SetVisibility(true);Leaves[RightLeaf]->SetVisibility(true);
        CurrentTarget=Next;
    }
    if(!bTurning){DisplayedView=PendingView;bHasDisplayedView=true;}
}
void UAlchemyManualComponent::FinishTurn(bool Commit)
{
    if(!bTurning)return;
    PoseLeaf(Commit?1.f:0.f);bTurning=bPageDrag=false;
    if(!bReady||PageTargets.Num()!=2)return;
    if(Commit)
    {
        CurrentTarget=1-CurrentTarget;DisplayedView=PendingView;bHasDisplayedView=true;
        LeftLeaf=bForward?TurningLeaf:UnderLeaf;RightLeaf=bForward?UnderLeaf:TurningLeaf;
        SpareLeaf=StationaryLeaf;
    }
    else PendingView=DisplayedView;
    // Commit changes logical roles only. The landed mesh, both material
    // bindings, and its visibility are retained. No texture redraw or handoff.
    TurningLeaf=UnderLeaf=StationaryLeaf=INDEX_NONE;
}
void UAlchemyManualComponent::BindFace(int32 Leaf,bool Front,int32 Target,int32 Side)
{
    auto* Material=PaperMaterials[Leaf*2+(Front?1:0)].Get();
    Material->SetTextureParameterValue(TEXT("PageTexture"),PageTargets[Target]);
    Material->SetVectorParameterValue(TEXT("PageOffset"),FLinearColor(Side*.5f,0,0,1));
}
void UAlchemyManualComponent::PlaceLeaf(int32 Leaf,float Turn,float Layer,float CurlDirection,float Peel)
{
    Leaves[Leaf]->SetRelativeLocation(FVector(0,0,AlchemyManualGeometry::LeafHeight+LeafClearance+Layer));
    Leaves[Leaf]->SetPagePose(Turn,CurlDirection,Peel);
}
void UAlchemyManualComponent::PoseLeaf(float Progress)
{
    TurnProgress=FMath::Clamp(Progress,0.f,1.f);
    if(!Leaves.IsValidIndex(TurningLeaf))return;
    const float Stack=FMath::SmoothStep(.18f,.84f,TurnProgress);
    PlaceLeaf(TurningLeaf,bForward?TurnProgress:1.f-TurnProgress,0,bForward?1.f:-1.f,CornerPeel);
    // Ease the supporting sheets by one paper thickness while occlusion moves.
    // This leaves the destination at exactly the same resting height both ways.
    PlaceLeaf(StationaryLeaf,bForward?1.f:0.f,-LeafSeparation*Stack);
    PlaceLeaf(UnderLeaf,bForward?0.f:1.f,-LeafSeparation*(1.f-Stack));
}
bool UAlchemyManualComponent::BeginPageDrag(const FAlchemyManualView& View,int32 Direction)
{
    if(!bReady||bTurning||DisplayedView.SamePage(View))return false;
    SetView(View,true,Direction);bPageDrag=bTurning;return bPageDrag;
}
void UAlchemyManualComponent::DragPage(float Progress){if(bPageDrag)PoseLeaf(Progress);}
void UAlchemyManualComponent::ReleasePage(bool Commit)
{
    if(!bPageDrag)return;bPageDrag=false;bCommitTurn=Commit;TurnStart=TurnProgress;TurnTime=0;
    TurnDuration=.18f+.34f*FMath::Abs((Commit?1.f:0.f)-TurnStart);
}
bool UAlchemyManualComponent::Advance(float Delta)
{
    if(!bReady)return false;const bool Feedback=AdvanceFeedback(Delta);if(!bTurning)return Feedback;
    if(bPageDrag)return true;
    TurnTime+=Delta;const float Alpha=FMath::SmoothStep(0.f,1.f,FMath::Clamp(TurnTime/TurnDuration,0.f,1.f));
    PoseLeaf(FMath::Lerp(TurnStart,bCommitTurn?1.f:0.f,Alpha));
    if(TurnTime>=TurnDuration)FinishTurn(bCommitTurn);return true;
}
void UAlchemyManualComponent::SetBookmarkState(int32 Hovered,int32 Pressed,bool AtFirst,bool AtLast)
{HoveredBookmark=Hovered;PressedBookmark=Pressed;bFirstPage=AtFirst;bLastPage=AtLast;}
bool UAlchemyManualComponent::AdvanceFeedback(float Delta)
{
    bool Dirty=false;
    for(int32 I=0;I<2;++I)
    {
        const bool AtEnd=I==0?bFirstPage:bLastPage;
        const float Lift=PressedBookmark==I?0.f:HoveredBookmark==I?(AtEnd?.035f:.13f):0.f;
        const float Fade=AtEnd?.62f:1.f;
        const float NewLift=FMath::FInterpConstantTo(BookmarkLift[I],Lift,Delta,.9f),NewFade=FMath::FInterpConstantTo(BookmarkFade[I],Fade,Delta,3.f);
        if(NewLift==BookmarkLift[I]&&NewFade==BookmarkFade[I])continue;
        BookmarkLift[I]=NewLift;BookmarkFade[I]=NewFade;Dirty=true;
        for(auto Material:BookmarkMaterials)if(Material)
        {
            Material->SetScalarParameterValue(I==0?TEXT("BookmarkLiftLeft"):TEXT("BookmarkLiftRight"),NewLift);
            Material->SetScalarParameterValue(I==0?TEXT("BookmarkFadeLeft"):TEXT("BookmarkFadeRight"),NewFade);
        }
    }
    const float NewPeel=FMath::FInterpConstantTo(CornerPeel,bPageDrag?.22f:0.f,Delta,2.f);
    if(NewPeel!=CornerPeel){CornerPeel=NewPeel;if(bTurning)PoseLeaf(TurnProgress);Dirty=true;}
    return Dirty;
}
void UAlchemyManualComponent::OnComponentDestroyed(bool DestroyingHierarchy)
{
    bReady=bOpen=bTurning=bPageDrag=false;bHasView=bHasDisplayedView=false;ContextWorld.Reset();
    if(Loading)Loading->CancelHandle();Loading.Reset();
    for(auto Part:Parts)if(Part)Part->DestroyComponent();Parts.Reset();
    for(auto Leaf:Leaves)if(Leaf)Leaf->DestroyComponent();Leaves.Reset();
    PaperMaterials.Reset();BookmarkMaterials.Reset();PageTargets.Reset();PageWidget=nullptr;
    if(Renderer){BeginCleanup(Renderer);Renderer=nullptr;}
    Super::OnComponentDestroyed(DestroyingHierarchy);
}
