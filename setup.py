from setuptools import setup

# parse version ---------------------------------------------------------------

import re
import ast

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("gh_projects.py", "rb") as f:
    VERSION = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

with open("README.md", encoding="utf-8") as f:
    README = f.read()

# setup -----------------------------------------------------------------------

setup(
    name="gh-projects-api",
    py_modules=["gh_projects"],
    version=VERSION,
    description="Tiny CLI for managing github (beta) project boards.",
    author="Michael Chow",
    license="MIT",
    author_email="mc_al_github@fastmail.com",
    url="https://github.com/machow/gh-projects-cli",
    keywords=[
        "package",
    ],
    install_requires=[
        "jq",
        "requests",
    ],
    extra_requires={
        "dev": ["pytest", "pre-commit" "black"],
    },
    python_requires=">=3.9",
    long_description=README,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
