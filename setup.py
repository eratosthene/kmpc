from setuptools import setup, find_packages

setup(
    name="kmpc",
    version="1.0dev",
    author="Chris Graham",
    author_email="eratosthene@gmail.com",
    packages=find_packages(exclude=['manager']),
    package_data={'':['resources/*']},
    include_package_data=True,
    scripts=['bin/kmpc'],
    url="https://github.com/eratosthene/kmpc",
    license="Creative Commons Attribution-Noncommercial-Share Alike license",
    description="kmpc is a Kivy-based mpd client, primarily meant for use on a Raspberry Pi mounted in a car.",
    long_description=open('README.rst').read(),
    install_requires=[],
)
