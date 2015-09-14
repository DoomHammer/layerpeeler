try:
  from setuptools import setup
except ImportError:
    from distutils.core import setup
from pip.req import parse_requirements
import os
import uuid

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

install_reqs = parse_requirements("requirements.txt", session=uuid.uuid1())

reqs = [str(ir.req) for ir in install_reqs]

setup(
    name="layerpeeler",
    version="0.0.1",
    author="Piotr Gaczkowski",
    author_email="doomhammerng@gmail.com",
    description=("A simple tool to study available Docker layers."),
    url="https://github.com/DoomHammer/layerpeeler",
    license="BSD",
    keywords="docker",
    packages=['layerpeeler'],
    scripts=['scripts/layerpeeler'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=reqs
)
