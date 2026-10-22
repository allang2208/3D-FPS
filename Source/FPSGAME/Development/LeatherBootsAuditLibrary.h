#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "LeatherBootsAuditLibrary.generated.h"
class USkeletalMesh;

UCLASS()
class FPSGAME_API ULeatherBootsAuditLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Read actual GPU LOD skin weights; Geometry Script's render copy omits them. */
    UFUNCTION(BlueprintCallable,Category="Development|Garment Audit")
    static bool ExportRenderWeights(USkeletalMesh* Mesh,int32 LOD,const FString& File);
};
