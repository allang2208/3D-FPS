#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "CraftingSystem.generated.h"

class UColdSteelStatusModel;
struct FColdSteelProfile;

/** One input material line from Content/ColdSteelData/crafting-recipes.json.
 *  item 为 items.json 与 production_tools.json 合并目录的稳定定义 id。 */
struct FColdSteelCraftingInput
{
    FString Item;
    int64 Count=1;
};

/** 工作台制造配方（Docs/UI/workbench-crafting-system-plan-20260925.md）：多输入→单输出、
 *  即时结算（一次事务全有或全无扣料并发产物），不计时、不写建筑存档。 */
struct FColdSteelCraftingRecipe
{
    FName Id;
    TArray<FColdSteelCraftingInput> Inputs;
    FString Output;
    int64 OutputCount=1;
};

/**
 * 制造配方目录与即时制造事务。与 UColdSteelSmeltingSystem 同口径：目录进程启动读一次（无热重载），
 * 扣料/发放走 UColdSteelStatusModel 的既有事务（背包优先、仓库兜底，CountMaterial 同域）；
 * 面板只做展示与按钮转发，不自己扣料或写档（UI-WORKFLOW 第 5 节）。
 */
UCLASS()
class FPSGAME_API UColdSteelCraftingSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    const TArray<FColdSteelCraftingRecipe>& Catalog() const {return Recipes;}
    const TArray<FColdSteelCraftingRecipe>& AmmoCatalog() const {return AmmoRecipes;}
    const FColdSteelCraftingRecipe* Find(FName Id) const;
    /** 可制作份数＝min(各输入 持有÷单份需)，兜底封顶 99；持有口径＝CountMaterial（背包＋主仓库）。 */
    int64 MaxCraftable(const UColdSteelStatusModel* Model,const FColdSteelCraftingRecipe& R) const;
    /** 即时制造：单事务内逐输入全有或全无扣除＋发放产物；任一环节失败都不提交、不扣任何东西并写原因。 */
    bool Craft(const FColdSteelCraftingRecipe& R,int64 Batch,FString& Reason);
    bool Craft(FName Recipe,int64 Batch,FString& Reason);
    /** Read-only quote using the same material deduction and output placement as Craft. */
    bool CanCraft(const FColdSteelCraftingRecipe& R,int64 Batch,FString& Reason) const;
private:
    bool PrepareCraft(const FColdSteelCraftingRecipe& R,int64 Batch,FColdSteelProfile& Proposed,FString& Reason) const;
    void LoadCatalog(const FString& File,TArray<FColdSteelCraftingRecipe>& Target);
    UColdSteelStatusModel* Model() const;
    TArray<FColdSteelCraftingRecipe> Recipes;
    TArray<FColdSteelCraftingRecipe> AmmoRecipes;
};
