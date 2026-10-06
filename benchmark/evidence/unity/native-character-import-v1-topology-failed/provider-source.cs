using System;
using UnityEngine;
using Unity.Collections;
using Unity.DemoTeam.Hair;

namespace KragKings.StrandPilot
{
    // Authored Blender streams stay byte-exact. The transform is established
    // from the actual imported character anchors, never an assumed axis flip.
    public sealed class NativeBinaryCurveProvider : HairAssetCustomData
    {
        public TextAsset positions,radii,counts,rootUV;
        public Matrix4x4 sourceToUnity=Matrix4x4.identity;
        public int expectedCurves,expectedPoints;
        public static float[] Floats(TextAsset input)
        {
            if(!input || input.bytes.Length%4!=0 || !BitConverter.IsLittleEndian)throw new Exception("Invalid little-endian float stream");
            var result=new float[input.bytes.Length/4];Buffer.BlockCopy(input.bytes,0,result,0,input.bytes.Length);
            foreach(float value in result)if(float.IsNaN(value)||float.IsInfinity(value))throw new Exception("Nonfinite groom stream");
            return result;
        }
        public override bool AcquireCurves(out HairAssetProvisional.CurveSet curves,Allocator allocator)
        {
            var p=Floats(positions);var r=Floats(radii);var uv=Floats(rootUV);
            if(!counts || counts.bytes.Length!=4*expectedCurves || p.Length!=expectedPoints*3 || r.Length!=expectedPoints || uv.Length!=expectedCurves*2)
                throw new Exception("Incomplete authored native groom streams");
            var c=new int[expectedCurves];Buffer.BlockCopy(counts.bytes,0,c,0,counts.bytes.Length);
            int total=0;foreach(int n in c){if(n<2)throw new Exception("Degenerate native curve");total=checked(total+n);}
            if(total!=expectedPoints)throw new Exception("Native curve point count mismatch");
            curves=new HairAssetProvisional.CurveSet(expectedCurves,expectedPoints,allocator);
            try
            {
                curves.curveCount=expectedCurves;
                curves.curveFeatures=HairAssetProvisional.CurveSet.CurveFeatures.TexCoord;
                curves.vertexFeatures=HairAssetProvisional.CurveSet.VertexFeatures.Position|HairAssetProvisional.CurveSet.VertexFeatures.Diameter;
                curves.unitScalePosition=curves.unitScaleDiameter=1;
                for(int i=0;i<expectedCurves;i++){curves.curveVertexCount.Add(c[i]);curves.curveDataTexCoord.Add(new Vector2(uv[2*i],uv[2*i+1]));}
                for(int i=0;i<expectedPoints;i++)
                {
                    if(!(r[i]>0 && r[i]<.01f))throw new Exception("Invalid authored radius");
                    curves.vertexDataPosition.Add(sourceToUnity.MultiplyPoint3x4(new Vector3(p[3*i],p[3*i+1],p[3*i+2])));
                    curves.vertexDataDiameter.Add(2*r[i]);
                }
                return true;
            }
            catch {curves.Dispose();throw;}
        }
    }
}
