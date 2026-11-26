#pragma once

#include "Components/TextRenderComponent.h"
#include "Engine/Font.h"
#include "UObject/ConstructorHelpers.h"

namespace ColdSteelWorldText
{
    inline constexpr const TCHAR* Asset = TEXT("/Game/UI/GunsmithWorkbench/WorldText/F_ColdSteelWorldText.F_ColdSteelWorldText");

    inline void SetConstructorFont(UTextRenderComponent& Text)
    {
        static ConstructorHelpers::FObjectFinder<UFont> Face(Asset);
        if (Face.Succeeded()) Text.SetFont(Face.Object);
    }

    inline void RestoreInstanceDefault(UTextRenderComponent& Text)
    {
        // Placed actors can serialize the engine default independently of their class default.
        if (!Text.Font || Text.Font == GetDefault<UTextRenderComponent>()->Font)
            if (auto* Face = Cast<UFont>(FSoftObjectPath(Asset).ResolveObject())) Text.SetFont(Face);
    }
}
