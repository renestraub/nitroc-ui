import setuptools
from nitrocui._version import __version__ as version


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="nitroc-ui",
    version=version,
    author="Rene Straub",
    author_email="straub@see5.com",
    description="NITROC Web UI and Cloud Logger",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/renestraub/nitroc-ui",
    packages=setuptools.find_packages(exclude=("tests",)),
    classifiers=[
        'Programming Language :: Python :: 3.7',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        'tornado',
        'requests',
        'ping3',
        'pycurl',
        'dbus-python'
    ],
    include_package_data=True,  # Use MANIFEST.in to add *.html, *.css files
    entry_points={
        'console_scripts': [
            'nitroc-ui-start = nitrocui.server:run_server'
        ]
    },
)
