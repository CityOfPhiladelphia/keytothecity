#!/usr/bin/env python

from distutils.core import setup

setup(
    name='keytothecity',
    version='0.1dev',
    packages=['keytothecity',],
    description='Maintain who has SSH access to your servers automatically',
    long_description=open('README.md').read(),
    install_requires=[
        'boto3==1.4.4',
        'click==6.7',
        'PyYAML==3.12',
        'python-crontab==2.1.1'
    ],
    entry_points={
        'console_scripts': [
            'keytothecity=keytothecity:main',
        ],
    }
)
