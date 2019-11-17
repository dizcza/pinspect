from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read()

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="pinspect",
    version="0.0.2",
    packages=find_packages(),
    install_requires=install_requires,
    author="Danylo Ulianych",
    author_email="d.ulianych@gmail.com",
    description="Pretty inspect object",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dizcza/pinspect",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    license="MIT",
)
