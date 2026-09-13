#include "TimberAssetEditor.h"
#include "Materials/MaterialExpressionSetMaterialAttributes.h"

bool UTimberAssetEditor::PrepareFallAttributeInputs(UMaterialExpression* Expression)
{
#if WITH_EDITOR
    if (auto* Attributes=Cast<UMaterialExpressionSetMaterialAttributes>(Expression))
    {
        Attributes->Modify();
        Attributes->CreateOrGetInputAttribute(MP_OpacityMask);
        Attributes->CreateOrGetInputAttribute(MP_WorldPositionOffset);
        return true;
    }
#endif
    return false;
}
