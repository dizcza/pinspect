from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read()

setup(
    name="pinspect",
    version="0.0.2",
    packages=find_packages(),
    install_requires=install_requires,
    author="Danylo Ulianych",
    author_email="d.ulianych@gmail.com",
    description="Pretty inspect object",
    license="MIT",
)
