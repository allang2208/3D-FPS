#pragma once

namespace ChainSlash
{
    inline constexpr TCHAR Standard[] = TEXT("/Game/Skills/ChainSlash20261107/Animations/A_ChainSlash_Standard.A_ChainSlash_Standard");
    inline constexpr TCHAR LongGrip[] = TEXT("/Game/Skills/ChainSlash20261107/Animations/A_ChainSlash_LongGrip.A_ChainSlash_LongGrip");
    inline constexpr TCHAR Pojun[] = TEXT("/Game/Skills/ChainSlash20261107/Animations/A_ChainSlash_Pojun.A_ChainSlash_Pojun");
    inline constexpr const TCHAR* CutRibbons[] = {
        TEXT("/Game/Skills/ChainSlash20261107/Feedback/SM_ChainSlash_Cut1.SM_ChainSlash_Cut1"),
        TEXT("/Game/Skills/ChainSlash20261107/Feedback/SM_ChainSlash_Cut2.SM_ChainSlash_Cut2"),
        TEXT("/Game/Skills/ChainSlash20261107/Feedback/SM_ChainSlash_Cut3.SM_ChainSlash_Cut3"),
        TEXT("/Game/Skills/ChainSlash20261107/Feedback/SM_ChainSlash_Cut4.SM_ChainSlash_Cut4")
    };
    inline constexpr TCHAR ImpactWave[] = TEXT("/Game/Skills/ChainSlash20261107/Feedback/SM_ChainSlash_ImpactWave.SM_ChainSlash_ImpactWave");
    inline constexpr float RibbonLead = .125f, RibbonTail = .105f;
}
