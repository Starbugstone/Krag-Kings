using System;

namespace KragKings.Editor
{
    // Input values are linear scalar samples. Pixel-center bilinear resizing
    // keeps the roughness map's resolution and clamps at atlas boundaries.
    // This has no Unity dependency so the actual packing math can be checked
    // without starting an editor or allocating imported assets.
    public sealed class LinearScalarMap
    {
        readonly float[] values;
        readonly int width,height;
        public bool IsConstant {get;private set;}
        public LinearScalarMap(float[] values,int width,int height)
        {
            if(values==null||width<=0||height<=0||values.Length!=(long)width*height)
                throw new ArgumentException("Scalar map dimensions do not match its samples.");
            this.values=values;this.width=width;this.height=height;
            IsConstant=true;
            for(int i=0;i<values.Length;i++)
            {
                if(float.IsNaN(values[i])||float.IsInfinity(values[i]))throw new ArgumentException("Scalar map contains a nonfinite sample.");
                if(values[i]!=values[0])IsConstant=false;
            }
        }
        public float AtOutputTexel(int x,int y,int outputWidth,int outputHeight)
        {
            if(x<0||x>=outputWidth||y<0||y>=outputHeight)throw new ArgumentOutOfRangeException("Output texel lies outside the target image.");
            if(IsConstant)return values[0];
            if(width==outputWidth&&height==outputHeight)return values[y*width+x];
            double sx=Math.Max(0,Math.Min(width-1,((x+.5)*width/outputWidth)-.5));
            double sy=Math.Max(0,Math.Min(height-1,((y+.5)*height/outputHeight)-.5));
            int x0=(int)Math.Floor(sx),y0=(int)Math.Floor(sy);
            int x1=Math.Min(x0+1,width-1),y1=Math.Min(y0+1,height-1);
            double tx=sx-x0,ty=sy-y0;
            double lower=values[y0*width+x0]*(1-tx)+values[y0*width+x1]*tx;
            double upper=values[y1*width+x0]*(1-tx)+values[y1*width+x1]*tx;
            return (float)(lower*(1-ty)+upper*ty);
        }
    }
}
