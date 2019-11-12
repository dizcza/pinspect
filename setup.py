from setuptools import setup

with open('requirements.txt') as f:
    install_requires = f.read()

setup(
    name="pinspect",
    version="0.0.1",
    packages=['pinspect'],
    install_requires=install_requires,
    author="Danylo Ulianych",
    author_email="d.ulianych@gmail.com",
    description="Pretty inspect object",
    license="MIT",
)
