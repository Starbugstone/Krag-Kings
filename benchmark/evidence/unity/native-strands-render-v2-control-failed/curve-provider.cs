using System;
using UnityEngine;
using Unity.Collections;
using Unity.DemoTeam.Hair;

namespace KragKings.StrandPilot
{
    // Engine-neutral authored curves, converted once from Blender metres by
    // prepare_fixture.py. No planar hair cards or simulation are authored here.
    public sealed class NativeCurveProvider : HairAssetCustomData
    {
        public TextAsset curveData;
        [Serializable] public class Data
        {
            public string region,coordinates,sourceSha256;
            public int[] counts;
            public float[] positions,radii,rootUV;
        }
        public Data Read()
        {
            if(!curveData)throw new InvalidOperationException("Missing authored groom data");
            var data=JsonUtility.FromJson<Data>(curveData.text);
            if(data==null || data.coordinates!="Unity metres (Blender x,z,y)" || data.counts==null || data.counts.Length==0)
                throw new InvalidOperationException("Invalid native curve metadata");
            int points=0;foreach(int count in data.counts){if(count<2)throw new InvalidOperationException("Degenerate strand");points=checked(points+count);}
            if(data.positions==null || data.positions.Length!=3*points || data.radii==null || data.radii.Length!=points || data.rootUV==null || data.rootUV.Length!=2*data.counts.Length)
                throw new InvalidOperationException("Incomplete native curve streams");
            foreach(float value in data.positions)if(float.IsNaN(value)||float.IsInfinity(value))throw new InvalidOperationException("Nonfinite groom point");
            foreach(float value in data.radii)if(!(value>0 && value<.01f))throw new InvalidOperationException("Invalid groom radius in metres");
            return data;
        }
        public override bool AcquireCurves(out HairAssetProvisional.CurveSet curves,Allocator allocator)
        {
            var d=Read();
            curves=new HairAssetProvisional.CurveSet(d.counts.Length,d.radii.Length,allocator);
            try
            {
                curves.curveCount=d.counts.Length;
                curves.curveFeatures=HairAssetProvisional.CurveSet.CurveFeatures.TexCoord;
                curves.vertexFeatures=HairAssetProvisional.CurveSet.VertexFeatures.Position|HairAssetProvisional.CurveSet.VertexFeatures.Diameter;
                curves.unitScalePosition=curves.unitScaleDiameter=1;
                for(int i=0;i<d.counts.Length;i++)
                {
                    curves.curveVertexCount.Add(d.counts[i]);
                    curves.curveDataTexCoord.Add(new Vector2(d.rootUV[2*i],d.rootUV[2*i+1]));
                }
                for(int i=0;i<d.radii.Length;i++)
                {
                    curves.vertexDataPosition.Add(new Vector3(d.positions[3*i],d.positions[3*i+1],d.positions[3*i+2]));
                    curves.vertexDataDiameter.Add(2*d.radii[i]);
                }
                return true;
            }
            catch {curves.Dispose();throw;}
        }
    }
}
