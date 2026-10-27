#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelCampfirePanel.generated.h"

class AColdSteelCampfire;
class UColdSteelHUDWidget;
class UColdSteelStatusModel;
class UColdSteelSmeltingSystem;
class UColdSteelCampfireRecipeProxy;
class UVerticalBox;
class UTextBlock;
class UButton;
class UProgressBar;
class UTexture2D;

/** Public station snapshot presentation. Transactions remain on the owning PlayerState. */
UCLASS()
class UColdSteelCampfirePanel : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner,AColdSteelCampfire* Station);
    void SelectRecipe(FName Recipe);
    void Refresh();
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
private:
    void Build();
    void ShowDetails();
    void Submit(uint8 Action);
    UTextBlock* Label(const FString& Text,float Size=14,bool Wrap=true);
    UButton* Button(const FString& Text);
    UVerticalBox* Section(UVerticalBox* Parent,const FString& Title);
    const FColdSteelItem& Item(const FString& Id);
    FString Name(const FString& Id);
    UFUNCTION() void Close();
    UFUNCTION() void Start();
    UFUNCTION() void Collect();
    UFUNCTION() void AddFuel();
    UFUNCTION() void Minus();
    UFUNCTION() void Plus();
    UFUNCTION() void Filter();
    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    TWeakObjectPtr<AColdSteelCampfire> Fire;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UColdSteelSmeltingSystem> System;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StateText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TimeText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> QueueText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ProductsText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FuelText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> BatchText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FreeText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EmptyText;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> CookingBar;
    UPROPERTY(Transient) TObjectPtr<UButton> StartButton;
    UPROPERTY(Transient) TObjectPtr<UButton> CollectButton;
    UPROPERTY(Transient) TObjectPtr<UButton> FuelButton;
    UPROPERTY(Transient) TObjectPtr<UButton> MinusButton;
    UPROPERTY(Transient) TObjectPtr<UButton> PlusButton;
    UPROPERTY(Transient) TObjectPtr<UButton> FilterButton;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> Details;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> ProductRows;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UTextBlock>> ProductLabels;
    UPROPERTY(Transient) TArray<TObjectPtr<UColdSteelCampfireRecipeProxy>> Proxies;
    UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> Textures;
    struct FRecipeRow { FName Id; TWeakObjectPtr<UButton> Button; TWeakObjectPtr<UTextBlock> Stock; };
    TArray<FRecipeRow> Rows;
    TMap<FString,FColdSteelItem> Items;
    FName Selected;
    int64 Batch=1,MaxBatch=0;
    bool bOnlyCraftable=false;
    float Scale=1.f,RefreshTime=0.f;
};

UCLASS()
class UColdSteelCampfireRecipeProxy : public UObject
{
    GENERATED_BODY()
public:
    TWeakObjectPtr<UColdSteelCampfirePanel> Panel;
    FName Recipe;
    UFUNCTION() void Clicked(){if(Panel.IsValid())Panel->SelectRecipe(Recipe);}
};
