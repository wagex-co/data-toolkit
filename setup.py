from setuptools import setup, find_packages
import os

# Read requirements
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Read version from src/__init__.py
about = {}
with open(os.path.join('src', '__init__.py'), 'r') as f:
    exec(f.read(), about)

setup(
    name="allthingsdatasourcing",
    version=about['__version__'],
    description="Sports data sourcing and analysis package",
    author="Wagex Team",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 