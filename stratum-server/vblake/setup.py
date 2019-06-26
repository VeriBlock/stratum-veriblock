from setuptools import setup, Extension

vblake_module = Extension('vblake',
                               sources = ['vblakemodule.c',
                                          'vblake.c'],
                               include_dirs=['.'])

setup (name = 'vblake',
       version = '1.0',
       description = 'Bindings for vBlake proof of work used by VeriBlock',
       ext_modules = [vblake_module])