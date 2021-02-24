from setuptools import setup, find_packages

setup(
    name="scm_electron_microscopes",
    version="1.0.0",
    author="Maarten Bransen",
    author_email="m.bransen@uu.nl",
    license='GNU General Public License v3.0',
    long_description=open('README.md').read(),
    packages=find_packages(include=["scm_electron_microscopes", "scm_electron_microscopes.*"]),
    install_requires=[
        "numpy>=1.19.2",
        "scipy>=1.6.0",
        "opencv>=4.0.1",
        "pillow>=6.2.1",
    ],
)
