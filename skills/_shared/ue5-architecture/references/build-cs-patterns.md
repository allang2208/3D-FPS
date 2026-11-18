# Build.cs Patterns (UE5.6-UE5.8)

## Runtime Module Pattern
```csharp
PublicDependencyModuleNames.AddRange(new string[] {
  "Core", "CoreUObject", "Engine"
});
PrivateDependencyModuleNames.AddRange(new string[] {
  "Slate", "SlateCore", "UMG"
});
```

## Editor Module Pattern
```csharp
PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
PrivateDependencyModuleNames.AddRange(new string[] {
  "UnrealEd", "AssetTools", "Slate", "SlateCore"
});
```

## Dependency Decision Rules
- Put a module in `PublicDependencyModuleNames` only when public headers include its types.
- Prefer private dependencies for implementation-only usage. 原因：实现细节使用的依赖不应传递给所有消费者，私有依赖可以缩小编译和接口耦合。
- Remove unused dependencies after refactor to reduce compile and link overhead. 原因：确认无使用者的依赖会扩大编译与链接范围，清理时也需保留反射和动态加载实际使用项。
