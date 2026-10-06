"""Small standard-library kinematic plot of acquired motion, never character art."""
import json
import math
from pathlib import Path
import struct
import sys
import zlib

from acclaim_motion import transform, rotation


def preview(source, first, last, output):
    samples = json.loads(Path(source).read_text())['samples']
    start, finish = samples[first-1]['heads']['root'], samples[last-1]['heads']['root']
    heading = math.degrees(math.atan2(finish[0]-start[0], -(finish[1]-start[1])))
    align = rotation('z', -heading)
    width, height = 1280, 960
    pixels = bytearray([239, 236, 227])*(width*height)
    def dot(x, y, radius, color):
        for yy in range(max(0, y-radius), min(height, y+radius+1)):
            for xx in range(max(0, x-radius), min(width, x+radius+1)):
                if (xx-x)**2+(yy-y)**2 <= radius**2:
                    i = 3*(yy*width+xx); pixels[i:i+3] = bytes(color)
    def line(a, b, radius, color):
        length = max(abs(b[0]-a[0]), abs(b[1]-a[1]), 1)
        for t in range(length+1):
            dot(round(a[0]+(b[0]-a[0])*t/length), round(a[1]+(b[1]-a[1])*t/length), radius, color)
    frames = [round(first+(last-first)*p) for p in [0, .25, .5, .75]]
    for column, frame in enumerate(frames):
        sample = samples[frame-1]
        center = sample['heads']['root']
        def point(value, side):
            x, y, z = transform(align, [value[0]-center[0], value[1]-center[1], value[2]])
            return round(column*320+160+(-y if side else x)*225), round(side*480+430-z*225)
        for side in range(2):
            line((column*320+8, side*480+430), (column*320+312, side*480+430), 1, (140, 136, 124))
            for bone in sample['heads']:
                if bone == 'root' or any(k in bone for k in ['finger', 'thumb', 'wrist']): continue
                color = (27, 129, 125) if bone.startswith('l') and bone not in ['lowerback', 'lowerneck'] else (189, 105, 45) if bone.startswith('r') else (61, 61, 62)
                a, b = point(sample['heads'][bone], side), point(sample['tails'][bone], side)
                line(a, b, 4, color); dot(*a, 6, color)
    raw = b''.join(b'\x00'+bytes(pixels[y*width*3:(y+1)*width*3]) for y in range(height))
    def chunk(name, data):
        return struct.pack('!I', len(data))+name+data+struct.pack('!I', zlib.crc32(name+data)&0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(raw))+chunk(b'IEND', b'')
    Path(output).write_bytes(png)
    print(json.dumps({'output': str(output), 'frames': frames, 'headingDegrees': heading,
                      'rows': ['front', 'side'], 'left': 'teal', 'right': 'orange'}))


if __name__ == '__main__':
    preview(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
