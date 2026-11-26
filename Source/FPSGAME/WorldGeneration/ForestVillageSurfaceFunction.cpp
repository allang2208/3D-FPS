#include "ForestVillageRegion.h"
#if WITH_EDITOR
#include "Materials/Material.h"
#include "Materials/MaterialExpressionFunctionOutput.h"
#include "Materials/MaterialExpressionMakeMaterialAttributes.h"
#include "Materials/MaterialExpressionNamedReroute.h"
#include "Materials/MaterialExpressionTextureCoordinate.h"
#include "Materials/MaterialFunction.h"
#include "Materials/MaterialParameters.h"
#endif

bool AForestVillageRegion::CopyGateMaterialInputs(UMaterial* Original, UMaterialExpression* Attributes)
{
#if WITH_EDITOR
    auto* Dest=Cast<UMaterialExpressionMakeMaterialAttributes>(Attributes);
    if(!Original || !Dest) return false;
    auto Copy=[Original](EMaterialProperty Property,FExpressionInput& To)
    {
        if(const auto* From=Original->GetExpressionInputForProperty(Property)) To=*From;
    };
    Copy(MP_BaseColor,Dest->BaseColor); Copy(MP_Metallic,Dest->Metallic);
    Copy(MP_Specular,Dest->Specular); Copy(MP_Roughness,Dest->Roughness);
    Copy(MP_Normal,Dest->Normal); Copy(MP_Anisotropy,Dest->Anisotropy);
    Copy(MP_EmissiveColor,Dest->EmissiveColor); Copy(MP_Tangent,Dest->Tangent);
    Copy(MP_AmbientOcclusion,Dest->AmbientOcclusion); Copy(MP_PixelDepthOffset,Dest->PixelDepthOffset);
    Copy(MP_Displacement,Dest->Displacement); Copy(MP_WorldPositionOffset,Dest->WorldPositionOffset);
    for(int32 I=0;I<8;++I) Copy(EMaterialProperty(MP_CustomizedUVs0+I),Dest->CustomizedUVs[I]);
    return true;
#else
    return false;
#endif
}

// Reuse the actual Sensei mesh surface, including its projection and near/far
// sampling. Freeze the palette's effective parameters under separate names so
// a village MID or the legacy fringe cannot override the sample's appearance.
bool AForestVillageRegion::BuildSurfaceFunction(UMaterialInterface* Palette, UMaterialFunction* Function)
{
#if WITH_EDITOR
    if (!Palette || !Function) return false;
    UMaterial* Master = Palette->GetMaterial();
    FExpressionInput* Surface = Master->GetExpressionInputForProperty(MP_MaterialAttributes);
    if (!Surface || !Surface->Expression) return false;
    auto& Expressions = Function->GetExpressionCollection();
    Function->Modify();
    Expressions.Empty();
    TMap<UMaterialExpression*, UMaterialExpression*> Copies;
    TFunction<UMaterialExpression*(UMaterialExpression*)> Copy = [&](UMaterialExpression* Original) -> UMaterialExpression*
    {
        if (!Original) return nullptr;
        if (auto** Found = Copies.Find(Original)) return *Found;
        auto* Node = DuplicateObject<UMaterialExpression>(Original, Function,
            MakeUniqueObjectName(Function, Original->GetClass(), Original->GetFName()));
        Copies.Add(Original, Node);
        Node->Material = nullptr;
        Node->Function = Function;
        Node->GraphNode = nullptr;
        Node->SubgraphExpression = nullptr;
        Node->UpdateMaterialExpressionGuid(true, true);
        Expressions.AddExpression(Node);
        FMaterialParameterMetadata Meta;
        const FName Name = Original->GetParameterName();
        if (!Name.IsNone() && Original->GetParameterValue(Meta))
        {
            Palette->GetParameterValue(Meta.Value.Type, FMaterialParameterInfo(Name), Meta);
            Node->SetParameterValue(Name, Meta);
            Node->SetParameterName(FName(TEXT("ForestSample_") + Name.ToString()));
        }
        if (auto* UV = Cast<UMaterialExpressionTextureCoordinate>(Node); UV && UV->CoordinateIndex==0)
            UV->CoordinateIndex=5;
        for (FExpressionInputIterator Input(Original); Input; ++Input)
            Node->GetInput(Input.Index)->Expression = Copy(Input->Expression);
        if (auto* Usage = Cast<UMaterialExpressionNamedRerouteUsage>(Node))
            Usage->Declaration = Cast<UMaterialExpressionNamedRerouteDeclaration>(
                Copy(CastChecked<UMaterialExpressionNamedRerouteUsage>(Original)->Declaration));
        return Node;
    };
    auto* Root = Copy(Surface->Expression);
    auto* Output = NewObject<UMaterialExpressionFunctionOutput>(Function);
    Output->Function = Function;
    Output->OutputName = TEXT("Forest Surface");
    Output->A = *Surface;
    Output->A.Expression = Root;
    Output->Id = FGuid(0xD27F8AE1,0x1B53480B,0xAB7C22A3,0x745A8218);
    Expressions.AddExpression(Output);
    Function->PostEditChange();
    Function->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
