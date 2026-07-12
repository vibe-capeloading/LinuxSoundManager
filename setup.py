"""
Setup script for Linux Sound Manager
"""

from setuptools import setup, find_packages
import os

# Read requirements
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Read version
version = "0.1.0"

setup(
    name="linux_sound_manager",
    version=version,
    description="A SteelSeries Sonar-like audio mixer for Linux",
    author="LinuxSoundManager Team",
    author_email="",
    url="https://github.com/vibe-capeloading/LinuxSoundManager",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'lsm=linux_sound_manager.main:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
    ],
    keywords="audio mixer pipewire pulseaudio sound",
)
