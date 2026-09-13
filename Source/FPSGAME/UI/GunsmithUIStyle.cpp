#include "GunsmithUIStyle.h"
FSlateFontInfo GunsmithUI::TextFont(float Size,bool Medium)
{
    // Slate's native point sizes use 96/72 pixels per point; our approved tokens are screen pixels.
    return ColdSteelUI::TextFont(Size*.75f,Medium);
}
FSlateFontInfo GunsmithUI::NumberFont(float Size,bool Medium)
{
    return ColdSteelUI::NumberFont(Size*.75f,Medium);
}
