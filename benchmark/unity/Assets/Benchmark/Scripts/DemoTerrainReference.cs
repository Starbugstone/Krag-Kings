using System;
using UnityEngine;

namespace KragKings.Benchmark
{
    // Source contract: shared/environment/manifest.json, central comparison area.
    // This checks actual imported collision, including normals after handedness
    // conversion. It does not substitute the formula for the playable mesh.
    public static class DemoTerrainReference
    {
        [Serializable] public class Evidence
        {
            public Vector3 sourcePoint,actualPoint,actualNormal;
            public bool hit,passed;
            public float heightErrorMeters,normalErrorDegrees;
        }
        public static Evidence[] Sample()
        {
            Vector2[] points={new(-1.35f,0),new(1.2f,.1f),new(6.3f,-4.7f),new(-9.1f,7.2f)};
            var result=new Evidence[points.Length];
            for(int i=0;i<points.Length;i++)
            {
                float x=points[i].x,y=points[i].y;
                float a=.105f*x+.035f*y,b=.055f*x-.145f*y,c=.22f*x+.13f*y;
                float height=.8f+1.1f*Mathf.Sin(a)+.65f*Mathf.Sin(b)+.30f*Mathf.Cos(c);
                float dx=.1155f*Mathf.Cos(a)+.03575f*Mathf.Cos(b)-.066f*Mathf.Sin(c);
                float dy=.0385f*Mathf.Cos(a)-.09425f*Mathf.Cos(b)-.039f*Mathf.Sin(c);
                var sample=new Evidence {sourcePoint=new Vector3(x,y,height)};
                sample.hit=DemoScene.TryGround(new Vector3(x,0,y),out var contact);
                if(sample.hit)
                {
                    sample.actualPoint=contact.point;sample.actualNormal=contact.normal;
                    sample.heightErrorMeters=Mathf.Abs(contact.point.y-height);
                    sample.normalErrorDegrees=Vector3.Angle(contact.normal,new Vector3(-dx,1,-dy).normalized);
                    // Allow linear interpolation of the authored 193-point grid.
                    sample.passed=sample.heightErrorMeters<.012f && sample.normalErrorDegrees<2f;
                }
                result[i]=sample;
            }
            return result;
        }
    }
}
