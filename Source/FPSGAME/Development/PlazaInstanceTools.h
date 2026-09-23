#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "PlazaInstanceTools.generated.h"

class AStaticMeshActor;
class UStaticMesh;

/** Editor asset production only. Never converts gameplay actors or non-Nanite geometry. */
UCLASS()
class FPSGAME_API UPlazaInstanceTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Builds derived Nanite data before the production script creates instances. */
    UFUNCTION(BlueprintCallable, Category="Development|Plaza")
    static bool BuildNaniteData(UStaticMesh* Mesh);
    UFUNCTION(BlueprintCallable, Category="Development|Plaza")
    static FString ClusterPolicy(AStaticMeshActor* Source);
    /** Creates a serialized ISM actor; the caller saves/removes sources only after success. */
    UFUNCTION(BlueprintCallable, Category="Development|Plaza")
    static AActor* CreatePlazaCluster(const TArray<AStaticMeshActor*>& Sources, const FString& Label);
};
