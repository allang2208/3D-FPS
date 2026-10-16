#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "../Building/AlchemyTypes.h"
#include "../Building/AlchemyManualView.h"
#include "ColdSteelAlchemyBookWidget.generated.h"
class UTextBlock;
class UImage;
class UHorizontalBox;
class UVerticalBox;
class UAlchemyManualComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;
class UMaterialInstanceDynamic;
class USoundBase;
class FColdSteelPreviewScene;
struct FStreamableHandle;
UCLASS()
class FPSGAME_API UColdSteelAlchemyBookWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(const FAlchemyRecipe& Recipe,int32 Spread,int32 FirstFolio=0,int32 FolioCount=0);
    void Configure(const FAlchemyManualView& View);
    static int32 Pages(const FAlchemyRecipe& Recipe);
protected:
    virtual void NativeOnInitialized() override;
private:
    friend class UAlchemyManualFlowAuditCommandlet;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> LeftPage;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> RightPage;
};

/** Read-only model viewer; selection never changes the public bench or the batch. */
UCLASS()
class FPSGAME_API UColdSteelAlchemyBookPreviewWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    UColdSteelAlchemyBookPreviewWidget(const FObjectInitializer& Initializer);
    virtual ~UColdSteelAlchemyBookPreviewWidget() override;
    void Configure(const TArray<FAlchemyRecipe>& Recipes,const FAlchemyRecipe& Selected,int32 Spread,bool PublicPageAudio=false);
    void Flip(int32 Direction);
    FName CurrentRecipeId() const {return RequestedRecipe.Id;}
    int32 CurrentSpread() const;
    void ReleasePreview(bool Final=true);
    void CancelInteraction();
    DECLARE_DELEGATE_OneParam(FPageChanged,int32);
    FPageChanged OnPageChanged;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
    virtual void NativeDestruct() override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E) override;
    virtual FReply NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E) override;
    virtual void NativeOnMouseCaptureLost(const FCaptureLostEvent& E) override;
    virtual void NativeOnMouseLeave(const FPointerEvent& E) override;
private:
    friend class UAlchemyManualFlowAuditCommandlet;
    void Loaded();
    void FrameBook();
    void ResizeCapture(const FGeometry& Geometry);
    FVector BookPoint(const FGeometry& G,const FVector2D& Screen,float PlaneZ) const;
    int32 BookmarkAt(const FVector& Point) const;
    int32 ContentsAt(const FVector& Point) const;
    FAlchemyManualView ReaderView(int32 Page) const;
    void BeginReaderDrag();
    void UpdateBookmarks();
    void PageSound(bool Commit);
    void TurnTo(int32 Page);
    UPROPERTY(Transient) TObjectPtr<UImage> Image;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> LoadingText;
    UPROPERTY(Transient) TObjectPtr<UAlchemyManualComponent> Manual;
    UPROPERTY(Transient) TObjectPtr<USceneCaptureComponent2D> Capture;
    UPROPERTY(Transient) TObjectPtr<USceneCaptureComponent2D> Coverage;
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> Target;
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> Mask;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Composite;
    UPROPERTY(Transient) TObjectPtr<USoundBase> PaperSound;
    TUniquePtr<FColdSteelPreviewScene> Studio;
    TSharedPtr<FStreamableHandle> Loading;
    struct FReaderPage {int32 Chapter=0,Spread=0;};
    TArray<FAlchemyRecipe> Chapters;
    TArray<FReaderPage> Contents;
    TArray<FAlchemyManualContentsEntry> IndexEntries;
    FAlchemyRecipe RequestedRecipe;
    FName BenchRecipe;
    int32 BenchSpread=0;
    bool bPublicPageAudio=false;
    int32 RequestedPage=0;
    float CaptureClock=0,SettleRemaining=0,LoadAge=0;
    FVector ViewEye=FVector(0,8,85);
    float ViewWidth=40.f;
    FIntPoint CaptureSize=FIntPoint(1400,1100);
    bool bPrepared=false,bClosed=true,bReleased=false;
    bool bPointerHeld=false,bDraggingPage=false;
    FVector2D PressPosition;
    FVector2D PointerPosition;
    double PressTime=0,MotionTime=0;
    float DragProgress=0,DragVelocity=0;
    int32 DragDirection=0,PressedBookmark=INDEX_NONE,HoveredBookmark=INDEX_NONE,PressedEntry=INDEX_NONE;
};
