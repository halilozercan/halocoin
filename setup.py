#!/usr/bin/env python
from distutils.core import setup

from setuptools import find_packages

setup(
    name='Halocoin',
    version='0.0.1',
    description='Read mapping incentivized cryptocurrency. Branch of halilozercan/halocoin',
    author='H. Ibrahim Ozercan',
    author_email='halilozercan@gmail.com',
    url='https://github.com/halilozercan/halocoin',
    entry_points={
        'console_scripts': [
            'halocoin = halocoin.cli:main'
        ],
    },
    include_package_data=True,
    install_requires=['requests', 'wheel', 'Cython', 'flask', 'flask-socketio',
                      'pycrypto', 'm3-cdecimal', 'simplekv', 'pyopenssl',
                      'werkzeug', 'tabulate', 'SQLAlchemy', 'ecdsa', 'plyvel', 'docker'],
    packages=find_packages('pyyaml', exclude=("tests", "tests.*")),
)
