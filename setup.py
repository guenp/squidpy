from distutils.core import setup

setup(
    name='squidpy',
    version='0.1',
    author='Guen Prawiroatmodjo',
    author_email='guen@nbi.ku.dk',
    packages=[
        'squidpy', 'squidpy.instruments'
    ],
    scripts=[],
    url='',
    license='LICENSE.txt',
    description='Measurement suite for scanning SQUID lab. Made for smooth integration with ipython notebook.',
    long_description=open('readme.md').read(),
    install_requires=[
        "Numpy >= 1.6.1",
        "pandas >= 0.14",
        "seaborn"
    ],
)
