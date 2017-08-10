#!/usr/bin/env python
from distutils.core import setup
from setuptools import find_packages

setup(
    name='Halocoin',
    version='0.0.4.5',
    description='An educational blockchain implementation. Forked from zack-bitcoin/basiccoin',
    author='Halil Ozercan',
    author_email='halilozercan@gmail.com',
    url='https://github.com/halilozercan/halocoin',
    download_url='https://github.com/halilozercan/halocoin/tarball/0.0.4.5',
    entry_points={
        'console_scripts': [
            'halocoin = halocoin.cli:main'
        ],
    },
    install_requires=['requests', 'wheel', 'pyyaml', 'filelock', 'pycrypto', 'leveldb', 'm3-cdecimal'],
    packages=find_packages(exclude=("tests", "tests.*")),
)
