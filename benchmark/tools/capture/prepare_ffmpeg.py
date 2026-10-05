"""Prepare the checksum-verified FFmpeg build tested with this laptop's driver.

8.0.1 NVENC passed an actual synthetic encode; 9.0.2 requires driver API 13.1,
while this machine exposes 13.0. Tools remain local, not game deliverables.
The implementation records the distributor release URL and SHA-256.
"""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('prepare_ffmpeg_compat.py')), run_name='__main__')
