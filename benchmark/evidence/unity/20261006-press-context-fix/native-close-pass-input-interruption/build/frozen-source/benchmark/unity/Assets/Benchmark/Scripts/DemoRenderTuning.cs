using System;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace KragKings.Benchmark
{
    // Explicit A/B settings for measured render-cost comparisons. Character
    // geometry, texture resolution, skin scattering and output resolution remain
    // identical within these two profiles.
    public static class DemoRenderTuning
    {
        public static string Apply(string[] args)
        {
            string preset="Full";
            for(int i=0;i<args.Length-1;i++)if(args[i]=="-renderQuality")preset=args[i+1];
            if(preset!="Full"&&preset!="Balanced")throw new ArgumentException("Unknown -renderQuality "+preset);
            var volume=UnityEngine.Object.FindObjectsByType<Volume>()
                .Single(v=>v.isGlobal&&v.sharedProfile&&v.sharedProfile.Has<GlobalIllumination>());
            var profile=volume.profile;
            if(!profile.TryGet<GlobalIllumination>(out var gi)||!profile.TryGet<ScreenSpaceReflection>(out var reflections))
                throw new InvalidOperationException("Comparison lighting profile is incomplete");
            bool full=preset=="Full";
            gi.enable.Override(true);
            gi.fullResolutionSS.Override(full);
            reflections.enabled.Override(full);
            return "HDRP High Fidelity asset / "+preset+", TAA, fixed native resolution, "+
                (full?"full-resolution SSGI and SSR":"half-resolution SSGI, SSR disabled")+
                ", SSS/SSAO/contact shadows retained, no hardware ray tracing, VSync disabled";
        }
    }
}
