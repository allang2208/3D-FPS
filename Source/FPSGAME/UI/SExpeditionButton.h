#pragma once

#include "ColdSteelUIStyle.h"
#include "Widgets/Input/SButton.h"

// Slate controls when navigation focus is painted; selection belongs to the page.
class SExpeditionButton : public SButton
{
public:
    void UseDarkFocus() { bDarkFocus = true; }

protected:
    virtual const FSlateBrush* GetFocusBrush() const override
    {
        static const FSlateBrush Light = ColdSteelUI::RoundedBrush(FLinearColor::Transparent, ColdSteelUI::ButtonRadius, ColdSteelUI::TextPrimary, 2);
        static const FSlateBrush Dark = ColdSteelUI::RoundedBrush(FLinearColor::Transparent, ColdSteelUI::ButtonRadius, ColdSteelUI::Content, 2);
        return bDarkFocus ? &Dark : &Light;
    }

private:
    bool bDarkFocus = false;
};
