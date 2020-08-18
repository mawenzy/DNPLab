import setuptools
from distutils.core import setup

setup(
        name = 'dnpLab',
        packages = setuptools.find_packages(),
        version = '1.0.1',
        license = 'MIT',
        description = 'dnpLab - A NMR Processing Library for ODNP Experiments',
        author = 'Timothy Keller, Tom Casey, Yanxian Lin, Thorsten Maly, John Franck, Songi Han',
        author_email = 'tkeller@bridge12.com',
        url = '',
        download_url = '',
        keywords = ['ODNP','DNP','NMR'],
        install_requires = [
            'numpy',
            'scipy',
            'matplotlib',
            'h5py',
            'PyQt5'
            ],
        classifiers = [
            'Development Status :: 3 - Alpha',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3',
            ],
        entry_points=dict(console_scripts=
            ['hydrationGUI=dnpLab.hydrationGUI:main_func',
            ]
            )

        )
