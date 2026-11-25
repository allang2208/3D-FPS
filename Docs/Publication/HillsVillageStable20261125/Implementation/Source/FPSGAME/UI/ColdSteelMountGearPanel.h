#pragma once
#include "Blueprint/UserWidget.h"
#include "ColdSteelMountGearPanel.generated.h"

class SComboButton;
class SImage;
class SProgressBar;
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
    TArray<TSharedPtr<STextBlock>> Captions,Values,GrowthValues;
    TArray<TSharedPtr<SImage>> GearImages;
    UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> Textures;
    TArray<FSlateBrush> Brushes,CellBrushes;
    TArray<TSharedPtr<STextBlock>> EmptyMarks,Performance;
    TSharedPtr<STextBlock> NameText,LevelText,CoatText,HairText,StateText,CountText,ExperienceText;
    TSharedPtr<SImage> Portrait;
    TSharedPtr<SProgressBar> ExperienceBar,HealthBar,StaminaBar;
    TSharedPtr<STextBlock> HealthText,StaminaText;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> PortraitAtlas;
    FSlateBrush PortraitBrush;
    int32 DropIndex=INDEX_NONE;
    bool bDropAllowed=false;
    int64 LastXP=-1;
    int32 LastLevel=INDEX_NONE;
    FVector4 LastVitals=FVector4(-1,-1,-1,-1);
    FString LastState;
};
