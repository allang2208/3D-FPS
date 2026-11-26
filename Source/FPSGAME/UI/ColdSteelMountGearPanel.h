#pragma once
#include "Blueprint/UserWidget.h"
#include "ColdSteelMountGearPanel.generated.h"

class SBorder;
class SComboButton;
class SHorseMarketPlate;
class SImage;
class SProgressBar;
class SWrapBox;
class UTexture2D;
class STextBlock;
class UColdSteelItemDrag;
class UColdSteelStatusModel;
struct FStableMountRecord;

UCLASS()
class UColdSteelMountGearPanel : public UUserWidget
{
    GENERATED_BODY()
public:
    void ClearHorse();
    void ShowHorse(UColdSteelStatusModel* InModel,const FStableMountRecord& Horse,bool bCanEquip,const FString& DisplayName);
    void UpdateCondition(const FStableMountRecord& Horse,const FString& State,float Health,float Stamina);
    bool HandleItemDrop(UColdSteelItemDrag* Drag,FVector2D Position);
    bool TryQuickEquip(const FString& ItemId);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool ReleaseChildren) override;
    virtual bool NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
    virtual void NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*) override;
    virtual bool NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
private:
    TSharedRef<SWidget> Choices(int32 GearIndex);
    FReply Change(FGuid Id,int32 GearIndex,FString Item,bool Equip);
    TWeakObjectPtr<UColdSteelStatusModel> Model;
    FGuid HorseId;
    bool Editable=false;
    TArray<TSharedPtr<SComboButton>> Buttons;
    TArray<TSharedPtr<STextBlock>> Captions,GearSubLabels,Values,GrowthValues,TraitRanks;
    TArray<TSharedPtr<SBorder>> TraitCards,GearAccentBars,GearArtFrames;
    TArray<TSharedPtr<SProgressBar>> TraitBars;
    TArray<TSharedPtr<SImage>> GearImages;
    UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> Textures;
    TArray<FSlateBrush> Brushes,CellBrushes,GearAccentBrushes,GearArtFrameBrushes;
    TArray<TSharedPtr<STextBlock>> EmptyMarks,Performance,PerformanceDeltas;
    TSharedPtr<STextBlock> NameText,LevelText,CoatText,HairText,StateText,CountText,ExperienceText,TotalRatingText;
    TSharedPtr<SHorseMarketPlate> HeroPlate;
    TSharedPtr<SBorder> StateBadge;
    TSharedPtr<SProgressBar> ExperienceBar,HealthBar,StaminaBar;
    TSharedPtr<STextBlock> HealthText,StaminaText;
    TSharedPtr<SWrapBox> AffixWrap;
    TSharedPtr<STextBlock> AffixCountText;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UTexture2D>> AffixTextures;
    TMap<FString,TSharedPtr<FSlateBrush>> AffixBrushes;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> PortraitAtlas;
    FSlateBrush PortraitBrush;
    int32 DropIndex=INDEX_NONE;
    bool bDropAllowed=false;
    int64 LastXP=-1;
    int32 LastLevel=INDEX_NONE;
    FVector4 LastVitals=FVector4(-1,-1,-1,-1);
    FString LastState;
};
