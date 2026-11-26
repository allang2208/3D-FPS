#include "WoodworkingSystem.h"
#include "WoodworkingQuality.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

bool UWoodworkingSystem::LoadCores()
{
    FString Raw;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/wood-cores.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Root)||!Root)return false;
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;if(!Root->TryGetArrayField(TEXT("cores"),Values))return false;
    TArray<FWoodworkingCore> Parsed;
    for(const auto& Value:*Values)
    {
        const TSharedPtr<FJsonObject>* O=nullptr;FString Id,Path;FWoodworkingCore C;
        if(!Value->TryGetObject(O)||!O||!*O||!(*O)->TryGetStringField(TEXT("item"),Id)||Id.IsEmpty()
            ||!(*O)->TryGetStringField(TEXT("name"),C.Name)||!(*O)->TryGetStringField(TEXT("material"),Path)
            ||!(*O)->TryGetNumberField(TEXT("damage_bonus"),C.Bonus)||!FMath::IsFinite(C.Bonus)||C.Bonus<0||C.Bonus>ColdSteelWoodQuality::MaxMaterialBonus)return false;
        C.Id=FName(*Id);C.Material=FSoftObjectPath(Path);
        if(C.Material.IsNull()||Parsed.ContainsByPredicate([&](const auto& Existing){return Existing.Id==C.Id;}))return false;
        Parsed.Add(MoveTemp(C));
    }
    if(Parsed.IsEmpty())return false;CoreCatalog=MoveTemp(Parsed);SelectedCore=CoreCatalog[0].Id;return true;
}
const FWoodworkingCore* UWoodworkingSystem::FindCore(FName Id) const
{return CoreCatalog.FindByPredicate([Id](const auto& C){return C.Id==Id;});}
FName UWoodworkingSystem::Core() const {return HasPendingJob()?Job().Core:SelectedCore;}
bool UWoodworkingSystem::SelectCore(FName Id)
{
    if(!CanSelect()||!FindCore(Id)){Notice=TEXT("请先处理已有工件，并选择可用木芯");return false;}
    SelectedCore=Id;return true;
}
bool UWoodworkingSystem::InputsFor(TArray<FColdSteelCraftingInput>& Inputs) const
{
    Inputs.Reset();const auto* P=Pattern();
    if(!P)return false;
    if(HasPendingJob())
    {
        for(const auto& Paid:Job().PaidMaterials)Inputs.Add({Paid.Key,Paid.Value});return true;
    }
    return RecipeInputs(P->CraftRecipe,SelectedCore,Inputs);
}
bool UWoodworkingSystem::RecipeInputs(FName CraftRecipe,FName CoreId,TArray<FColdSteelCraftingInput>& Inputs) const
{
    Inputs.Reset();
    const auto* Craft=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>();
    const auto* Recipe=Craft?Craft->Find(CraftRecipe):nullptr;
    const auto* C=FindCore(CoreId);
    if(!Recipe||!C||!Catalog.ContainsByPredicate([CraftRecipe](const auto& Entry){return Entry.CraftRecipe==CraftRecipe;}))return false;
    Inputs=Recipe->Inputs;
    if(auto* Existing=Inputs.FindByPredicate([&](const auto& Input){return Input.Item==C->Id.ToString();}))++Existing->Count;
    else Inputs.Add({C->Id.ToString(),1});return true;
}
double UWoodworkingSystem::MaterialBonus() const
{if(HasPendingJob())return Job().QualityVersion>=ColdSteelWoodQuality::Version?Job().MaterialBonus:0.;const auto* C=FindCore(SelectedCore);return C?C->Bonus:0.;}
double UWoodworkingSystem::ProcessingBonus() const
{
    if(!HasPendingJob())return 0.;
    const bool Settled=Job().bFinished;const double Score=Settled?Job().Quality:Quality();
    if(Job().QualityVersion<ColdSteelWoodQuality::Version)return ColdSteelWoodQuality::FromScore(Score)-1.;
    const bool Finished=Settled||Phase==EWoodworkingPhase::Complete||Phase==EWoodworkingPhase::Failed;
    const double Progress=Finished?1.:FMath::Clamp(Board.Metrics().Clearance/FMath::Max(.01,Rules.RequiredClearance),0.,1.);
    return ColdSteelWoodQuality::SkillBonus(Score)*Progress;
}
