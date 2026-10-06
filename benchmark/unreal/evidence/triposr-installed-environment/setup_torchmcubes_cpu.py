"""Build the pinned upstream CPU sources without probing/installing a CUDA Toolkit."""
from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CppExtension

setup(name='torchmcubes', version='0.1.0', license='MIT',
      description='Pinned historical torchmcubes CPU extraction for isolated TripoSR reference study',
      packages=['torchmcubes'],
      ext_modules=[CppExtension('torchmcubes_module', [
          'cxx/mcubes.cpp', 'cxx/mcubes_cpu.cpp', 'cxx/grid_interp_cpu.cpp'])],
      cmdclass={'build_ext': BuildExtension.with_options(use_ninja=True)})
