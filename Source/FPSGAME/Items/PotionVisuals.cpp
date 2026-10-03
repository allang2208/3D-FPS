#include "PotionVisuals.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
    struct FPotionVisualCatalog
    {
        TArray<FPotionTierVisual> Tiers;
        FString HealthMaterial, ManaMaterial;
        FPotionVisualCatalog()
        {
            FString Text;
            TSharedPtr<FJsonObject> Root;
            if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/potion_visuals.json"))) ||
                !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root) || !Root.IsValid())return;
            Root->TryGetStringField(TEXT("health_material"),HealthMaterial);
            Root->TryGetStringField(TEXT("mana_material"),ManaMaterial);
            const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
            if(!Root->TryGetArrayField(TEXT("tiers"),Entries))return;
            for(const auto& Value:*Entries)
            {
                const auto O=Value->AsObject();if(!O.IsValid())continue;
                FPotionTierVisual V;
                O->TryGetStringField(TEXT("tier"),V.Tier);
                O->TryGetStringArrayField(TEXT("definitions"),V.Definitions);
                O->TryGetStringField(TEXT("shell"),V.Shell);
                O->TryGetStringField(TEXT("liquid"),V.Liquid);
                O->TryGetStringField(TEXT("stopper"),V.Stopper);
                O->TryGetStringField(TEXT("closed"),V.Closed);
                O->TryGetNumberField(TEXT("height_cm"),V.HeightCm);
                O->TryGetNumberField(TEXT("grip_height_cm"),V.GripHeightCm);
                O->TryGetStringField(TEXT("liquid_material"),V.LiquidMaterial);
                O->TryGetStringField(TEXT("half_closed"),V.HalfClosed);
                O->TryGetNumberField(TEXT("liquid_bottom_cm"),V.LiquidBottomCm);
                O->TryGetNumberField(TEXT("liquid_full_cm"),V.LiquidFullCm);
                if(!V.Definitions.IsEmpty()&&!V.Shell.IsEmpty()&&!V.Liquid.IsEmpty()&&!V.Stopper.IsEmpty()&&!V.Closed.IsEmpty())
                    Tiers.Add(MoveTemp(V));
            }
        }
    };

    // Immutable, process-lifetime authoring catalog: no JSON reads in pose ticks
    // or repeated pickup refreshes. Reload authored changes on the next launch.
    const FPotionVisualCatalog& Catalog()
    {
        static const FPotionVisualCatalog Value;
        return Value;
    }
}

const TArray<FPotionTierVisual>& PotionVisuals::Tiers(){return Catalog().Tiers;}
int32 PotionVisuals::FindTier(const FString& Definition)
{
    const auto& All=Tiers();
    for(int32 I=0;I<All.Num();++I)if(All[I].Definitions.Contains(Definition))return I;
    return INDEX_NONE;
}
const FString& PotionVisuals::LiquidMaterial(bool bMana)
{
    return bMana?Catalog().ManaMaterial:Catalog().HealthMaterial;
}
