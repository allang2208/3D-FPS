#pragma once
#include "FrostSwordRunes.h"

namespace ZhanmadaoRuneInlay
{
    struct FArtwork
    {
        float Style;
        const TCHAR* Color;
        const TCHAR* ORM;
    };

    inline const FArtwork* ForRune(const FString& Rune)
    {
        static constexpr FArtwork Crimson{1.f,
            TEXT("/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/Textures/T_Chixiao_BaseColor_V1.T_Chixiao_BaseColor_V1"),
            TEXT("/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/Textures/T_Chixiao_ORM_V1.T_Chixiao_ORM_V1")};
        static constexpr FArtwork Cyan{2.f,
            TEXT("/Game/Weapons/Zhanmadao20261018/ZhufengBladeV1/Textures/T_Zhufeng_BaseColor_V1.T_Zhufeng_BaseColor_V1"),
            TEXT("/Game/Weapons/Zhanmadao20261018/ZhufengBladeV1/Textures/T_Zhufeng_ORM_V1.T_Zhufeng_ORM_V1")};
        if(Rune==ColdSteelFrostRunes::Chixiao)return &Crimson;
        if(Rune==ColdSteelFrostRunes::Zhufeng)return &Cyan;
        return nullptr;
    }
}
