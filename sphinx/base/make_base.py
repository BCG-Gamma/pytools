#!/usr/bin/env python3
"""
Sphinx documentation build script
"""
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from glob import glob
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type, TypeVar
from weakref import ref

from packaging import version as pkg_version

cwd = os.getcwd()

# Sphinx commands
CMD_SPHINX_BUILD = "sphinx-build"
CMD_SPHINX_AUTOGEN = "sphinx-autogen"

# File paths
DIR_MAKE_BASE = os.path.dirname(os.path.realpath(__file__))
DIR_REPO_ROOT = os.path.realpath(os.path.join(os.getcwd(), os.pardir))
DIR_REPO_PARENT = os.path.realpath(os.path.join(DIR_REPO_ROOT, os.pardir))
FACET_PROJECT = os.path.split(os.path.realpath(DIR_REPO_ROOT))[1]
DIR_PACKAGE_SRC = os.path.join(DIR_REPO_ROOT, "src")
DIR_DOCS = os.path.join(DIR_REPO_ROOT, "docs")
DIR_SPHINX_SOURCE = os.path.join(cwd, "source")
DIR_SPHINX_AUX = os.path.join(cwd, "auxiliary")
DIR_SPHINX_API_GENERATED = os.path.join(DIR_SPHINX_SOURCE, "apidoc")
DIR_SPHINX_GET_STARTED_GENERATED = os.path.join(DIR_SPHINX_SOURCE, "getting_started")
DIR_SPHINX_BUILD = os.path.join(cwd, "build")
DIR_SPHINX_BUILD_HTML = os.path.join(DIR_SPHINX_BUILD, "html")
DIR_SPHINX_TEMPLATES = os.path.join(DIR_SPHINX_SOURCE, "_templates")
DIR_SPHINX_SOURCE_BASE = os.path.join(DIR_MAKE_BASE, os.pardir, "source")
DIR_SPHINX_TEMPLATES_BASE = os.path.join(DIR_SPHINX_SOURCE_BASE, "_templates")
DIR_SPHINX_AUTOSUMMARY_TEMPLATE = os.path.join(DIR_SPHINX_TEMPLATES, "autosummary.rst")
DIR_SPHINX_TUTORIAL = os.path.join(DIR_SPHINX_SOURCE, "tutorial")
DIR_SPHINX_SOURCE_STATIC_BASE = os.path.join(DIR_SPHINX_SOURCE_BASE, "_static_base")
JS_VERSIONS_FILE = os.path.join(DIR_SPHINX_SOURCE_STATIC_BASE, "js", "versions.js")
DIR_ALL_DOCS_VERSIONS = os.path.join(DIR_SPHINX_BUILD, "docs-version")

print(f"DIR_DOCS:", DIR_DOCS)

print("Contents DIR_DOCS:")

try:
    print(os.listdir(DIR_DOCS))
except:
    pass


print(f"DIR_ALL_DOCS:", DIR_ALL_DOCS_VERSIONS)
print("Contents ALL_DOCS:")

try:
    print(os.listdir(DIR_ALL_DOCS_VERSIONS))
except:
    pass

# Environment variables
# noinspection SpellCheckingInspection
ENV_PYTHON_PATH = "PYTHONPATH"

T = TypeVar("T")


class CommandMeta(ABCMeta):
    """
    Meta-class for command classes.

    Subsequent instantiations of a command class return the identical object.
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        cls.__instance_ref: Optional[ref] = None

    def __call__(cls: Type[T], *args, **kwargs: Any) -> T:
        """
        Return the existing command instance, or create a new one if none exists yet.

        :return: the command instance
        """
        if args or kwargs:
            raise ValueError("command classes may not take any arguments")

        cls: CommandMeta

        if cls.__instance_ref:
            obj = cls.__instance_ref()
            if obj is not None:
                return obj

        instance = super(CommandMeta, cls).__call__()
        cls.__instance_ref = ref(instance)
        return instance


class Command(metaclass=CommandMeta):
    """ Defines an available command that can be launched from this module."""

    __RE_CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")

    def __init__(self) -> None:
        self.name = self.__RE_CAMEL_TO_SNAKE.sub("_", type(self).__name__).lower()

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    def get_dependencies(self) -> Tuple["Command", ...]:
        pass

    def get_prerequisites(self) -> Iterable["Command"]:
        dependencies_extended: List[Command] = []

        for dependency in self.get_dependencies():
            dependencies_inherited = dependency.get_dependencies()
            if self in dependencies_inherited:
                raise ValueError(
                    f"circular dependency: {dependency.name} " f"depends on {self.name}"
                )
            dependencies_extended.extend(
                dependency
                for dependency in dependencies_inherited
                if dependency not in dependencies_extended
            )
            dependencies_extended.append(dependency)

        return dependencies_extended

    def run(self) -> None:
        print(f"Running command {self.name} – {self.get_description()}")
        self._run()

    @abstractmethod
    def _run(self) -> None:
        pass


#
# commands
#


class Clean(Command):
    def get_description(self) -> str:
        return "remove Sphinx build output"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        if os.path.exists(DIR_SPHINX_BUILD):
            shutil.rmtree(path=DIR_SPHINX_BUILD)
        if os.path.exists(DIR_SPHINX_API_GENERATED):
            shutil.rmtree(path=DIR_SPHINX_API_GENERATED)
        if os.path.exists(DIR_SPHINX_GET_STARTED_GENERATED):
            shutil.rmtree(path=DIR_SPHINX_GET_STARTED_GENERATED)


class ApiDoc(Command):
    def get_description(self) -> str:
        return "generate Sphinx API documentation from sources"

    def get_dependencies(self) -> Tuple[Command, ...]:
        # noinspection PyRedundantParentheses
        return (Clean(),)

    def _run(self) -> None:
        packages = [
            package for package in os.listdir(DIR_PACKAGE_SRC) if package[:1].isalnum()
        ]
        print(f"Generating api documentation for {', '.join(packages)}")

        package_lines = "\n   ".join(packages)
        # noinspection SpellCheckingInspection
        autosummary_rst = f""".. autosummary::
   :toctree: ../apidoc
   :template: custom-module-template.rst
   :recursive:

   {package_lines}
"""

        os.makedirs(os.path.dirname(DIR_SPHINX_AUTOSUMMARY_TEMPLATE), exist_ok=True)
        with open(DIR_SPHINX_AUTOSUMMARY_TEMPLATE, "wt") as f:
            f.writelines(autosummary_rst)
        autogen_options = " ".join(
            [
                # template path
                "-t",
                quote_path(DIR_SPHINX_TEMPLATES_BASE),
                # include imports
                "-i",
                # the autosummary source file
                quote_path(DIR_SPHINX_AUTOSUMMARY_TEMPLATE),
            ]
        )

        subprocess.run(
            args=f"{CMD_SPHINX_AUTOGEN} {autogen_options}",
            shell=True,
            check=True,
        )


class GettingStartedDoc(Command):
    def get_description(self) -> str:
        return "generate getting started documentation from sources"

    def get_dependencies(self) -> Tuple[Command, ...]:
        # noinspection PyRedundantParentheses
        return (Clean(),)

    def _run(self) -> None:

        # make dir if it does not exist
        os.makedirs(DIR_SPHINX_GET_STARTED_GENERATED, exist_ok=True)

        # open the rst readme file
        with open(os.path.join(DIR_REPO_ROOT, "README.rst"), "r") as file:
            readme_data = file.read()

        # modify links (step back needed as build will add sub directory to paths)
        readme_data = readme_data.replace("sphinx/source/", "../")
        readme_data = readme_data.replace("sphinx/auxiliary/", "../")
        readme_data = re.sub(
            r"\.\. Begin-Badges.*?\.\. End-Badges", "", readme_data, flags=re.S
        )

        with open(os.path.join(DIR_SPHINX_SOURCE, "release_notes.rst"), "w") as dst:
            dst.write(".. _release-notes:\n\n")
            with open(os.path.join(DIR_REPO_ROOT, "RELEASE_NOTES.rst"), "r") as src:
                dst.write(src.read())

        # create a new getting_started.rst that combines the header from templates and
        # adds an include for the README
        with open(
            os.path.join(DIR_SPHINX_TEMPLATES_BASE, "getting-started-header.rst"), "r"
        ) as file:
            template_data = file.read()

        with open(
            os.path.join(DIR_SPHINX_GET_STARTED_GENERATED, "getting_started.rst"),
            "wt",
        ) as file:
            file.writelines(template_data)
            file.writelines(readme_data)


class FetchPkgVersions(Command):
    def get_description(self) -> str:
        return "fetch available package versions with docs"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        versions = Versions()

        version_data = {
            "current": str(versions.latest_stable_version),
            "non_rc": list(map(str, versions.version_tags_stable)),
            "all": list(map(str, versions.version_tags)),
        }

        version_data_as_js = (
            f"const DOCS_VERSIONS = {json.dumps(version_data, indent=4,)}"
        )

        with open(JS_VERSIONS_FILE, "wt") as f:
            f.write(version_data_as_js)

        print(f"Version data written into: {JS_VERSIONS_FILE}")


class PrepareDocsDeployment(Command):
    def get_description(self) -> str:
        return "update versions of rendered documentation"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        if not is_azure_build():
            raise RuntimeError("only implemented for Azure Pipelines")

        # get the current version of the package
        current_version: pkg_version.Version = get_package_version()

        # copy new the docs version to the deployment path
        if current_version == Versions().latest_stable_version:
            # only copy to deployment path if our version is the latest stable release

            # remove docs build currently deployed, except for the docs versions folder
            if os.path.exists(os.path.join(DIR_DOCS, "docs-version")):
                with TemporaryDirectory() as DIR_TMP:
                    shutil.move(src=os.path.join(DIR_DOCS, "docs-version"), dst=DIR_TMP)
                    shutil.rmtree(path=DIR_DOCS)
                    os.makedirs(DIR_DOCS)
                    shutil.move(src=os.path.join(DIR_TMP, "docs-version"), dst=DIR_DOCS)
            else:
                os.makedirs(DIR_DOCS, exist_ok=True)

            # copy new docs version to deployment path
            shutil.copytree(src=DIR_SPHINX_BUILD_HTML, dst=DIR_DOCS, dirs_exist_ok=True)

        # get current version of package in the form of folder/URL name (e.g., "1-0-0")
        current_version_path = os.path.join(
            DIR_DOCS, "docs-version", version_string_to_url(current_version)
        )
        # update latest version in docs history
        if os.path.exists(current_version_path):
            shutil.rmtree(path=current_version_path)
        shutil.copytree(
            src=DIR_ALL_DOCS_VERSIONS,
            dst=os.path.join(DIR_DOCS, "docs-version"),
            dirs_exist_ok=True,
        )

        # Replace all docs version lists with the most up-to-date to have all versions
        # accessible also from older versions
        new_versions_js = os.path.join(DIR_DOCS, "_static", "js", "versions.js")
        print(new_versions_js)
        print(glob(os.path.join(DIR_DOCS, "docs-version", "*", "")))
        for d in glob(os.path.join(DIR_DOCS, "docs-version", "*", "")):
            old_versions_js = os.path.join(d, "_static", "js", "versions.js")
            print("Copying ", new_versions_js, "to ", old_versions_js)
            shutil.copyfile(src=new_versions_js, dst=old_versions_js)

        # remove .buildinfo which interferes with GitHub Pages build
        if os.path.exists(os.path.join(DIR_DOCS, ".buildinfo")):
            os.remove(os.path.join(DIR_DOCS, ".buildinfo"))

        # create empty file to signal that no GitHub auto-rendering is required
        # noinspection SpellCheckingInspection
        open(os.path.join(DIR_DOCS, ".nojekyll"), "a").close()

        print("Docs moved to ./docs and historic versions updated")


class Html(Command):
    def get_description(self) -> str:
        return "build Sphinx docs as HTML"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return Clean(), FetchPkgVersions(), ApiDoc(), GettingStartedDoc()

    def _run(self) -> None:

        check_sphinx_version()

        os.makedirs(DIR_SPHINX_BUILD, exist_ok=True)

        sphinx_html_opts = [
            "-M html",
            quote_path(DIR_SPHINX_SOURCE),
            quote_path(DIR_SPHINX_BUILD),
        ]

        subprocess.run(
            args=f"{CMD_SPHINX_BUILD} {' '.join(sphinx_html_opts)}",
            shell=True,
            check=True,
        )

        # create interactive versions of all notebooks
        sys.path.append(DIR_MAKE_BASE)

        # create copy of this build for the docs archive
        version_built: pkg_version.Version = get_package_version()
        dir_path_this_build = os.path.join(
            DIR_ALL_DOCS_VERSIONS, version_string_to_url(version_built)
        )

        os.makedirs(DIR_ALL_DOCS_VERSIONS, exist_ok=True)
        if os.path.exists(dir_path_this_build):
            shutil.rmtree(dir_path_this_build)

        shutil.copytree(
            src=DIR_SPHINX_BUILD_HTML,
            dst=dir_path_this_build,
        )

        if not is_azure_build():
            shutil.move(src=DIR_ALL_DOCS_VERSIONS, dst=DIR_SPHINX_BUILD_HTML)

        # empty versions file to blank template
        with open(JS_VERSIONS_FILE, "wt") as f:
            f.write("")


class Help(Command):
    def get_description(self) -> str:
        return "print this help message"

    def get_dependencies(self) -> Tuple[Command, ...]:
        return ()

    def _run(self) -> None:
        print_usage()


class Versions:
    """
    Helper class that lists all versions that have already been released.
    """

    INITIAL_VERSION_TAG = pkg_version.parse("1.0.1")

    def __init__(self) -> None:
        os.makedirs(DIR_SPHINX_BUILD, exist_ok=True)
        start_from_version_tag: pkg_version.Version = Versions.INITIAL_VERSION_TAG
        sp = subprocess.run(
            args='git tag -l "*.*.*"', shell=True, check=True, stdout=subprocess.PIPE
        )
        version_tags: List[pkg_version.Version] = [
            version_tag
            for version_tag in (
                pkg_version.parse(version_string)
                for version_string in sp.stdout.decode("UTF-8").split("\n")
                if version_string
            )
            if version_tag >= start_from_version_tag
        ]

        # add version currently build into version_tags
        version_built: pkg_version.Version = get_package_version()

        if version_built not in version_tags:
            version_tags.append(version_built)

        version_tags.sort()
        version_tags.reverse()
        version_tags_stable: List[pkg_version.Version] = [
            vt for vt in version_tags if not (vt.is_prerelease or vt.is_devrelease)
        ]
        latest_stable_version: pkg_version.Version = version_tags_stable[0]

        print(f"Found versions: {', '.join(map(str, version_tags))}")
        print("Latest stable version: ", latest_stable_version)

        self.version_tags = version_tags
        self.version_tags_stable = version_tags_stable
        self.latest_stable_version = latest_stable_version


def make(*, modules: List[str]) -> None:
    """
    Run this make script with the given arguments.
    """
    if len(sys.argv) < 2:
        print_usage()

    commands_passed = sys.argv[1:]

    unknown_commands = set(commands_passed) - available_commands.keys()

    if unknown_commands:
        print(f"Unknown build commands: {' '.join(unknown_commands)}\n")
        print_usage()
        exit(1)

    # set up the Python path
    module_paths = [
        os.path.abspath(os.path.join(DIR_REPO_PARENT, module, "src"))
        for module in modules
    ]
    if ENV_PYTHON_PATH in os.environ:
        module_paths.append(os.environ[ENV_PYTHON_PATH])
    os.environ[ENV_PYTHON_PATH] = os.pathsep.join(module_paths)

    # run all given commands:
    executed_commands: Set[Command] = set()

    for next_command_name in commands_passed:

        next_command: Command = available_commands[next_command_name]

        for prerequisite_command in next_command.get_prerequisites():

            if prerequisite_command not in executed_commands:
                prerequisite_command.run()
                executed_commands.add(prerequisite_command)

        next_command.run()
        executed_commands.add(next_command)


def quote_path(path: str) -> str:
    """
    Quote a file path if it contains whitespace.
    """
    if " " in path or "\t" in path:
        return f'"{path}"'
    else:
        return path


def get_package_version() -> pkg_version.Version:
    """
    Retrieve the package version for the project from __init__ or _version
    """
    project_src = os.path.abspath(os.path.join(DIR_REPO_ROOT, "src"))

    if FACET_PROJECT in ("sklearndf", "flow"):
        # for sklearndf and flow __init__ can't be trivially imported due to import
        # dependencies. Load the version as defined in FACET_PROJECT._version module
        spec = importlib.util.spec_from_file_location(
            "_version", os.path.join(project_src, FACET_PROJECT, "_version.py")
        )
    else:
        # pytools/facet: retrieve version from __init__.py
        spec = importlib.util.spec_from_file_location(
            "_version", os.path.join(project_src, FACET_PROJECT, "__init__.py")
        )

    version_module = importlib.util.module_from_spec(spec)
    # noinspection PyUnresolvedReferences
    spec.loader.exec_module(version_module)
    # noinspection PyUnresolvedReferences
    return pkg_version.parse(version_module.__version__)


def is_azure_build() -> bool:
    """
    Check if this is an Azure DevOps pipelines build
    """
    return "BUILD_REASON" in os.environ


def version_string_to_url(version: pkg_version.Version) -> str:
    """
    Make a Python package version string safe for URLs/folders.

    Our convention is to only replace all dots with dashes.
    """
    return str(version).replace(".", "-")


def check_sphinx_version() -> None:
    import sphinx

    sphinx_version = pkg_version.parse(sphinx.__version__)
    if sphinx_version < pkg_version.parse("3.2.1"):
        raise RuntimeError("please upgrade sphinx to version 3.2.1 or newer")


def print_usage() -> None:
    usage = """Sphinx documentation build script
=================================

Available program arguments:
"""
    usage += "\n".join(
        f"\t{name} – {command.get_description()}"
        for name, command in available_commands.items()
    )
    print(usage)


available_commands: Dict[str, Command] = {
    cmd.name: cmd
    for cmd in (
        Clean(),
        ApiDoc(),
        GettingStartedDoc(),
        Html(),
        Help(),
        FetchPkgVersions(),
        PrepareDocsDeployment(),
    )
}
