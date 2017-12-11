#!/usr/bin/env python
from distutils.core import setup

from setuptools import find_packages

setup(
    name='Halocoin',
    version='0.1.0.4',
    description='An educational blockchain implementation. Forked from zack-bitcoin/basiccoin',
    author='Halil Ozercan',
    author_email='halilozercan@gmail.com',
    url='https://github.com/halilozercan/halocoin',
    entry_points={
        'console_scripts': [
            'halocoin = halocoin.cli:main'
        ],
    },
    include_package_data=True,
    install_requires=['requests', 'wheel', 'pyyaml', 'flask', 'flask-socketio',
                      'pycrypto', 'm3-cdecimal', 'simplekv',
                      'werkzeug', 'json-rpc', 'tabulate', 'redis', 'ecdsa'],
    packages=find_packages(exclude=("tests", "tests.*")),
)
