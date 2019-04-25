from setuptools import find_packages, setup


setup(
    name='restorepoint',
    version='1.4.1',
    license='GPL3',
    description='Python API wrapper for RestorePoint',
    # long_description=open('README.rst').read(),
    author='Philipp Schmitt',
    author_email='philipp@schmitt.co',
    url='https://github.com/pschmitt/python-restorepoint',
    packages=find_packages(),
    install_requires=['requests', 'pathos', 'python-dateutil'],
    entry_points={
        'console_scripts': ['rp=restorepoint.rp:main']
    }
)
