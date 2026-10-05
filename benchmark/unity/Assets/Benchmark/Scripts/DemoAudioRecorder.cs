using System;
using System.IO;
using System.Text;
using UnityEngine;

namespace KragKings.Benchmark
{
    // Game listener output only. No microphone or desktop-loopback recording.
    public sealed class DemoAudioRecorder : MonoBehaviour
    {
        readonly object sync=new();
        float[] samples;
        int count,channels,sampleRate;
        volatile bool recording;
        public void BeginRecording(int maximumSeconds)
        {
            lock(sync){sampleRate=AudioSettings.outputSampleRate;samples=new float[sampleRate*maximumSeconds*8];count=0;channels=0;recording=true;}
        }
        void OnAudioFilterRead(float[] data,int channelCount)
        {
            if(!recording)return;
            lock(sync)
            {
                if(!recording)return;
                if(channels==0)channels=channelCount;
                if(channels!=channelCount)return;
                int length=Math.Min(data.Length,samples.Length-count);
                Array.Copy(data,0,samples,count,length);count+=length;
            }
        }
        public void EndRecording(string path)
        {
            lock(sync)
            {
                recording=false;
                if(count==0||channels==0)throw new InvalidOperationException("Game audio recorder received no listener samples");
                using var stream=File.Create(path);using var writer=new BinaryWriter(stream);
                int bytes=count*4;
                writer.Write(Encoding.ASCII.GetBytes("RIFF"));writer.Write(bytes+36);writer.Write(Encoding.ASCII.GetBytes("WAVEfmt "));
                writer.Write(16);writer.Write((short)3);writer.Write((short)channels);writer.Write(sampleRate);
                writer.Write(sampleRate*channels*4);writer.Write((short)(channels*4));writer.Write((short)32);
                writer.Write(Encoding.ASCII.GetBytes("data"));writer.Write(bytes);
                byte[] data=new byte[bytes];Buffer.BlockCopy(samples,0,data,0,bytes);writer.Write(data);
                samples=null;
            }
        }
    }
}
