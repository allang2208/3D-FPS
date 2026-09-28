#include "CraftingSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    // 命名带 Craft 前缀：unity 批量编译会把本文件与 SmeltingSystem.cpp 并进同一翻译单元，
    // 匿名 namespace 拦不住重名（2026-09-24 构建 C2374 教训）。语义与冶炼侧 Deduct/Grant 完全同款。
    bool CraftDeduct(FColdSteelProfile& P,const FString& Def,int64 Count)
    {
        int64 Available=0;
        for(const FColdSteelItem& Item:P.Items)
            if(Item.Definition==Def&&(Item.Place==0||(Item.Place==4&&Item.Container.IsEmpty())))Available+=Item.Count;
        if(Available<Count)return false;
        int64 Left=Count;
        for(int32 Place:{0,4})
            for(int32 Index=P.Items.Num()-1;Index>=0&&Left>0;--Index)
            {
                FColdSteelItem& Item=P.Items[Index];
                if(Item.Definition!=Def||Item.Place!=Place||(Place==4&&!Item.Container.IsEmpty()))continue;
                const int64 Used=FMath::Min(Left,Item.Count);
                Item.Count-=Used;Left-=Used;
                if(Item.Count<=0)P.Items.RemoveAt(Index);
            }
        return Left==0;
    }
    bool CraftGrant(UColdSteelStatusModel* Model,FColdSteelProfile& P,const FString& Def,int64 Count)
    {
        // Ammo lives in the pouch. Deduction and pouch credit share this same snapshot/save.
        if(const auto* Ammo=Model->AmmoType(Def))return Ammo->Enabled&&Model->AddAmmoToState(P,Def,Count);
        const FColdSteelItem Item=Model->CreateItem(Def,Count);
        return !Item.Data.IsEmpty()&&ColdSteelInventory::Insert(P.Items,Item);
    }
    FString CraftDefinitionName(UColdSteelStatusModel* Model,const FString& Definition)
    {
        if(!Model||Definition.IsEmpty())return Definition;
        const FString Name=ColdSteelInventory::Text(Model->CreateItem(Definition),TEXT("name"));
        return Name.IsEmpty()?Definition:Name;
    }
}

void UColdSteelCraftingSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    LoadCatalog(TEXT("crafting-recipes.json"),Recipes);
    LoadCatalog(TEXT("ammo-crafting-recipes.json"),AmmoRecipes);
}
void UColdSteelCraftingSystem::LoadCatalog(const FString& File,TArray<FColdSteelCraftingRecipe>& Target)
{
    // 与 items.json／smelting-recipes.json 同一口径：只在进程启动时读一次，改表要重启（无热重载）。
    FString Json;
    const FString Path=FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File;
    if(!FFileHelper::LoadFileToString(Json,*Path))
    {UE_LOG(LogTemp,Warning,TEXT("Crafting: recipe catalog missing at %s"),*Path);return;}
    TSharedPtr<FJsonObject> Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root.IsValid())
    {UE_LOG(LogTemp,Error,TEXT("Crafting: recipe catalog is not valid JSON: %s"),*Path);return;}
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(!Root->TryGetArrayField(TEXT("recipes"),Rows))
    {UE_LOG(LogTemp,Error,TEXT("Crafting: recipe catalog has no \"recipes\" array: %s"),*Path);return;}
    for(const TSharedPtr<FJsonValue>& Row:*Rows)
    {
        const TSharedPtr<FJsonObject>* O=nullptr;
        if(!Row->TryGetObject(O)||!O||!O->IsValid())continue;
        const FJsonObject& E=**O;
        FColdSteelCraftingRecipe R;
        FString Id;E.TryGetStringField(TEXT("id"),Id);R.Id=FName(*Id);
        const TArray<TSharedPtr<FJsonValue>>* Ins=nullptr;
        if(E.TryGetArrayField(TEXT("inputs"),Ins)&&Ins)
            for(const TSharedPtr<FJsonValue>& V:*Ins)
            {
                const TSharedPtr<FJsonObject>* IO=nullptr;
                if(!V->TryGetObject(IO)||!IO||!IO->IsValid())continue;
                FColdSteelCraftingInput In;
                (*IO)->TryGetStringField(TEXT("item"),In.Item);
                double N=1.0;(*IO)->TryGetNumberField(TEXT("count"),N);
                In.Count=FMath::Max<int64>(1,FMath::RoundToInt64(N));
                if(!In.Item.IsEmpty())R.Inputs.Add(MoveTemp(In));
            }
        const TSharedPtr<FJsonObject>* Out=nullptr;
        if(E.TryGetObjectField(TEXT("output"),Out)&&Out&&Out->IsValid())
        {
            (*Out)->TryGetStringField(TEXT("item"),R.Output);
            double N=1.0;(*Out)->TryGetNumberField(TEXT("count"),N);
            R.OutputCount=FMath::Max<int64>(1,FMath::RoundToInt64(N));
        }
        // 坏行逐条跳过并点名（与存档"跳过坏记录不整废"同一口径）；重复 id 只留第一条。
        if(R.Id.IsNone()||R.Inputs.Num()==0||R.Output.IsEmpty()
            ||Find(R.Id))
        {UE_LOG(LogTemp,Warning,TEXT("Crafting: skipped malformed/duplicate recipe row: %s"),*Id);continue;}
        Target.Add(MoveTemp(R));
    }
    UE_LOG(LogTemp,Log,TEXT("Crafting: loaded %d recipe(s) from %s"),Target.Num(),*Path);
}

const FColdSteelCraftingRecipe* UColdSteelCraftingSystem::Find(FName Id) const
{
    if(Id.IsNone())return nullptr;
    for(const FColdSteelCraftingRecipe& R:Recipes)if(R.Id==Id)return &R;
    for(const FColdSteelCraftingRecipe& R:AmmoRecipes)if(R.Id==Id)return &R;
    return nullptr;
}

int64 UColdSteelCraftingSystem::MaxCraftable(const UColdSteelStatusModel* Model,const FColdSteelCraftingRecipe& R) const
{
    if(!Model||R.Inputs.Num()==0)return 0;
    int64 Cap=99;
    for(const FColdSteelCraftingInput& In:R.Inputs)
    {
        if(In.Count<=0)return 0;
        Cap=FMath::Min<int64>(Cap,Model->CountMaterial(In.Item)/In.Count);
    }
    return FMath::Max<int64>(0,Cap);
}

bool UColdSteelCraftingSystem::Craft(FName Recipe,int64 Batch,FString& Reason)
{
    const FColdSteelCraftingRecipe* R=Find(Recipe);
    if(!R){Reason=TEXT("该配方不存在");return false;}
    return Craft(*R,Batch,Reason);
}

bool UColdSteelCraftingSystem::Craft(const FColdSteelCraftingRecipe& R,int64 Batch,FString& Reason)
{
    auto* M=Model();
    if(!M){Reason=TEXT("角色数据未就绪");return false;}
    M->SyncRuntime();
    FColdSteelProfile Proposed;
    if(!PrepareCraft(R,Batch,Proposed,Reason))return false;
    if(!M->CommitState(MoveTemp(Proposed))){Reason=TEXT("保存失败，材料未扣除");return false;}
    return true;
}

bool UColdSteelCraftingSystem::CanCraft(const FColdSteelCraftingRecipe& R,int64 Batch,FString& Reason) const
{
    FColdSteelProfile Proposed;
    return PrepareCraft(R,Batch,Proposed,Reason);
}

bool UColdSteelCraftingSystem::PrepareCraft(const FColdSteelCraftingRecipe& R,int64 Batch,FColdSteelProfile& Proposed,FString& Reason) const
{
    Reason.Reset();
    auto* M=Model();
    if(!M){Reason=TEXT("角色数据未就绪");return false;}
    if(R.Id.IsNone()||R.Inputs.Num()==0||R.Output.IsEmpty()){Reason=TEXT("该配方不存在");return false;}
    Batch=FMath::Clamp(Batch,1LL,99LL);   // 面板按可制作份数夹，这里兜底封顶
    for(const FColdSteelCraftingInput& In:R.Inputs)
        if(M->CreateItem(In.Item).Data.IsEmpty()){Reason=TEXT("物品目录缺少该材料");return false;}
    const auto* Ammo=M->AmmoType(R.Output);
    if(Ammo&&!Ammo->Enabled){Reason=TEXT("该弹药暂未开放制作");return false;}
    if(!Ammo&&M->CreateItem(R.Output).Data.IsEmpty()){Reason=TEXT("物品目录缺少该产物");return false;}
    // 材料不足：点名第一个缺口（与冶炼 ConsumeItem 同句式"缺少 N（背包+仓库共 M）"）。
    for(const FColdSteelCraftingInput& In:R.Inputs)
    {
        const int64 Have=M->CountMaterial(In.Item),Need=In.Count*Batch;
        if(Have<Need)
        {
            Reason=FString::Printf(TEXT("缺少 %lld 个%s（背包+仓库共 %lld）"),Need-Have,
                *CraftDefinitionName(M,In.Item),Have);
            return false;
        }
    }
    // 单事务：本地快照上先扣后发，全部成功才 CommitState——任一失败都不扣任何东西。
    Proposed=M->Snapshot();
    for(const FColdSteelCraftingInput& In:R.Inputs)
        if(!CraftDeduct(Proposed,In.Item,In.Count*Batch)){Reason=TEXT("材料不足，制作已取消");return false;}
    if(!CraftGrant(M,Proposed,R.Output,R.OutputCount*Batch)){Reason=Ammo?TEXT("弹药袋数量已达上限，材料未扣除"):TEXT("背包放不下，先整理背包");return false;}
    return true;
}

UColdSteelStatusModel* UColdSteelCraftingSystem::Model() const
{
    return GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}
