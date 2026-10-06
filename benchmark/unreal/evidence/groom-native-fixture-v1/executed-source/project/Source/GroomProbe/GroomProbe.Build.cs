using UnrealBuildTool;
public class GroomProbe : ModuleRules
{
    public GroomProbe(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","HairStrandsCore"});
        PrivateDependencyModuleNames.AddRange(new string[]{"Json","MeshDescription","UnrealEd"});
    }
}
