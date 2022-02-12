from setuptools import setup, find_packages

setup(
    name="scm_electron_microscopes",
    version="3.0.0",
    author="Maarten Bransen",
    author_email="m.bransen@uu.nl",
    license='GNU General Public License v3.0',
    long_description=open('README.md').read(),
    packages=find_packages(include=["scm_electron_microscopes", "scm_electron_microscopes.*"]),
    install_requires=[
        "numpy>=1.19.2",
        "scipy>=1.6.0",
        "matplotlib>=3.0.0",
        "opencv-python>=3.0.0",
        "pillow>=8.4.0",
        "h5py>=3.6.0",
    ],
)
