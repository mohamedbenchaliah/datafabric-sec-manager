import os
import sys

from setuptools import find_namespace_packages, setup
from setuptools.command.test import test as TestCommand


here = os.path.abspath(os.path.dirname(__file__))
about = {}
path = os.path.join(here, "src", "__version__.py")
with open(file=path, mode="r", encoding="utf-8") as f:
    exec(f.read(), about)

with open("README.md", "r") as fh:
    long_description = fh.read()


class UseTox(TestCommand):
    RED = 31
    RESET_SEQ = "\033[0m"
    BOLD_SEQ = "\033[1m"
    COLOR_SEQ = "\033[1;%dm"

    def run_tests(self):
        sys.stderr.write(
            "%s%spython setup.py test is deprecated by pypa.  Please invoke "
            "'tox' with no arguments for a basic test run.\n%s"
            % (self.COLOR_SEQ % self.RED, self.BOLD_SEQ, self.RESET_SEQ)
        )
        sys.exit(1)


setup(
    name=about["__title__"],
    version=about["__version__"],
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    cmdclass={"test": UseTox},
    package_dir={'': 'src'},
    packages=find_namespace_packages(where='src'),
    namespace_packages=['datafabric'],
    include_package_data=True,
    zip_safe=True,
    platforms='any',
    python_requires=">=3.6, <3.10",
    # install_requires=[open("requirements.txt").read().strip().split("\n")],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
