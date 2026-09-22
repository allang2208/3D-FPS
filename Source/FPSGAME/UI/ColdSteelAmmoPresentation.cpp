#include "ColdSteelStatusModel.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Styling/SlateBrush.h"

const FSlateBrush* UColdSteelStatusModel::AmmoIcon(const FString& Id)
{
    if(const auto* Cached=AmmoIconBrushes.Find(Id))return Cached->Get();
    const auto* Type=AmmoType(Id);if(!Type||Type->Icon.IsEmpty())return nullptr;
    auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Type->Icon);
    if(!Texture){AmmoIconBrushes.Add(Id,nullptr);return nullptr;}
    AmmoIconTextures.Add(Id,Texture);
    // Brushes live at stable addresses even when later ammo icons grow the map.
    auto Brush=MakeShared<FSlateBrush>();Brush->SetResourceObject(Texture);
    Brush->ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush->DrawAs=ESlateBrushDrawType::Image;
    AmmoIconBrushes.Add(Id,Brush);return &Brush.Get();
}
FString UColdSteelStatusModel::AmmoEffectSummary(const FString& Id) const
{
    const auto* Type=AmmoType(Id);if(!Type)return FString();
    const float Bonus=(Type->DamageMultiplier-1.f)*100;
    const FString Damage=FMath::IsNearlyZero(Bonus)?TEXT("无增伤"):FString::Printf(TEXT("伤害 %+.0f%%"),Bonus);
    return Damage+(Type->PhysicalArmorPenetration>0?
        FString::Printf(TEXT(" · 无视 %.0f%% 物理护甲"),Type->PhysicalArmorPenetration*100):TEXT(" · 无护甲穿透"));
}
