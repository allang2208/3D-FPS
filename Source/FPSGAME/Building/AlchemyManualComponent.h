#pragma once
#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "AlchemyTypes.h"
#include "AlchemyManualView.h"
#include "AlchemyManualComponent.generated.h"
class UStaticMeshComponent;
class UBookLeafComponent;
class UMaterialInstanceDynamic;
class UTextureRenderTarget2D;
class UColdSteelAlchemyBookWidget;
class FWidgetRenderer;
struct FStreamableHandle;

/** The same authored book serves the public tabletop and the private reader. */
UCLASS()
class FPSGAME_API UAlchemyManualComponent : public USceneComponent
{
    GENERATED_BODY()
public:
    void Initialize(UWorld* WidgetWorld);
    void SetOpen(bool Open);
    void SetRecipe(const FAlchemyRecipe& Recipe,int32 Spread,bool Animate=true,int32 Direction=0,int32 FirstFolio=0,int32 FolioCount=0);
    void SetView(const FAlchemyManualView& View,bool Animate=true,int32 Direction=0);
    void SetBookmarkState(int32 Hovered,int32 Pressed,bool AtFirst,bool AtLast);
    bool Advance(float Delta);
    bool Ready() const {return bReady;}
    bool Failed() const {return bLoadFinished&&!bReady;}
    bool Turning() const {return bTurning;}
    bool BeginPageDrag(const FAlchemyManualView& View,int32 Direction);
    void DragPage(float Progress);
    void ReleasePage(bool Commit);
    const TArray<TObjectPtr<UStaticMeshComponent>>& Meshes() const {return Parts;}
    const TArray<TObjectPtr<UBookLeafComponent>>& Pages() const {return Leaves;}
    virtual void OnComponentDestroyed(bool DestroyingHierarchy) override;
private:
    friend class UAlchemyManualFlowAuditCommandlet;
    friend class AAlchemyManualNetAuditController;
    void Loaded();
    void DrawSpread();
    void FinishTurn(bool Commit=true);
    void PoseLeaf(float Progress);
    void BindFace(int32 Leaf,bool Front,int32 Target,int32 Side);
    void PlaceLeaf(int32 Leaf,float Turn,float Layer=0.f,float CurlDirection=1.f,float Peel=0.f);
    bool AdvanceFeedback(float Delta);
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY(Transient) TArray<TObjectPtr<UBookLeafComponent>> Leaves;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> PaperMaterials;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextureRenderTarget2D>> PageTargets;
    UPROPERTY(Transient) TObjectPtr<UColdSteelAlchemyBookWidget> PageWidget;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> BookmarkMaterials;
    TWeakObjectPtr<UWorld> ContextWorld;
    TSharedPtr<FStreamableHandle> Loading;
    FWidgetRenderer* Renderer=nullptr;
    FAlchemyManualView PendingView,DisplayedView;
    int32 CurrentTarget=0;
    int32 LeftLeaf=0,RightLeaf=1,SpareLeaf=2;
    int32 TurningLeaf=INDEX_NONE,UnderLeaf=INDEX_NONE,StationaryLeaf=INDEX_NONE;
    bool bHasView=false,bHasDisplayedView=false;
    int32 HoveredBookmark=INDEX_NONE,PressedBookmark=INDEX_NONE;
    bool bFirstPage=false,bLastPage=false;
    float BookmarkLift[2]={0,0},BookmarkFade[2]={1,1},CornerPeel=0;
    bool bReady=false,bLoadFinished=false,bOpen=false,bTurning=false,bForward=true,bPageDrag=false,bCommitTurn=true;
    float TurnTime=0,TurnProgress=0,TurnStart=0,TurnDuration=.65f;
};
