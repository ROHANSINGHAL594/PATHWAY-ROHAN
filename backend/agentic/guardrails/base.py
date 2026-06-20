import sys
import logging
from pydantic.dataclasses import dataclass
from pydantic import Field, BaseModel

# Get logger for guardrails
logger = logging.getLogger(__name__)

# Changed to False - never call sys.exit() in a container environment
# This would crash the entire container. Use exceptions instead.
TERMINATE_ON_EXTRA_FAILURE: bool = False

@dataclass
class DetectorResult:
    entity: str = Field(..., description="The type of entity that was detected.")
    start: int = Field(..., description="The start index of the detected entity.")
    end: int = Field(..., description="The end index of the detected entity.")


class model_DetectorResult(BaseModel):
    entity: str = Field(..., description="The type of entity that was detected.")
    start: int = Field(..., description="The start index of the detected entity.")
    end: int = Field(..., description="The end index of the detected entity.")

class BaseDetector:
    """Base class for detectors."""

    def get_entities(self, results: list[DetectorResult]) -> list[str]:
        """Returns a list of entities from a list of DetectorResult objects.

        Args:
            results: A list of DetectorResult objects.
        Returns:
            A list of entities.
        """
        return [result.entity for result in results]

    def detect_all(self, text: str, *args, **kwargs) -> list[DetectorResult]:
        """Performs detection on the given text and returns a list of DetectorResult objects.

        Args:
            text: The text to analyze.
        Returns:
            A list of DetectorResult objects.
        """
        raise NotImplementedError("")

    def detect(self, text: str, *args, **kwargs) -> bool:
        """Performs detection on the given text and returns a boolean indicating whether there has been any detection.

        Args:
            text: The text to analyze.
        Returns:
            A boolean indicating whether there has been any detection.
        """
        return len(self.detect_all(text, *args, **kwargs)) > 0

    async def preload(self):
        """
        Some workload to run to initialize the detector for lower-latency inference later on.

        For instance, model loading or other expensive operations.
        """
        pass



class ExtrasImport:
    
    def __init__(self, import_name, package_name, version_constraint):
        """Creates a new ExtrasImport object.

        Args:
            import_name (str): The name or specifier of the module to import (e.g. 'lib' or 'lib.submodule')
            package_name (str): The name of the pypi package that contains the module.
            version_constraint (str): The version constraint for the package (e.g. '>=1.0.0')
        """
        self.name = import_name
        self.package_name = package_name
        self.version_constraint = version_constraint

        # collection of sites where this dependency is used
        # (only available if find_all is used)
        self.sites = []

    def import_names(self, *specifiers):
        
        module = self.import_module()
        elements = [getattr(module, specifier) for specifier in specifiers]
        if len(elements) == 1:
            return elements[0]
        return elements

    def import_module(self):
        module = __import__(self.name, fromlist=[self.name])
        return module

    def __str__(self):
        if len(self.sites) > 0:
            sites_str = f", sites={self.sites}"
        else:
            sites_str = ""
        return f"ExtrasImport('{self.name}', '{self.package_name}', '{self.version_constraint}'{sites_str})"

    def __repr__(self):
        return str(self)



class Extra:
    """
    An Extra is a group of optional dependencies that can be installed on demand.
    The extra is defined by a name, a description, and a collection of packages.
    For a list of available extras, see `Extra.find_all()` and below.
    """

    def __init__(self, name, description, packages):
        self.name = name
        self.description = description
        self.packages = packages
        self._is_available = None

        Extra.extras[name] = self

    def is_available(self) -> bool:
        """Returns whether the extra is available (all assigned imports can be resolved)."""
        if self._is_available is not None:
            return self._is_available

        for package in self.packages.values():
            try:
                __import__(package.name)
            except ImportError:
                self._is_available = False
                return False

        self._is_available = True
        return True

    def package(self, name) -> ExtrasImport:
        """Returns the package with the given name."""
        if not self.is_available():
            self.install()

        return self.packages[name]

    def install(self):
        """Installs all required packages for this extra (using pip if available)."""
        # like for imports, but all in one go
        msg = "You are trying to use a feature that relies on the extra dependency '{}', which requires the following packages to be installed:\n".format(
            self.name
        )
        for imp in self.packages.values():
            msg += "   - " + imp.package_name + imp.version_constraint + "\n"

        logger.warning(msg)

        # check if terminal input is possible
        if sys.stdin.isatty():
            sys.stderr.write("Press (y/enter) to install the packages or Ctrl+C to exit: ")
            answer = input()
            if answer == "y" or len(answer) == 0:
                import subprocess

                # check if 'pip' is installed
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "--version"], capture_output=True
                )
                if result.returncode != 0:
                    sys.stderr.write(
                        "error: 'pip' is not installed. Please install the above mentioned packages manually.\n"
                    )
                    if TERMINATE_ON_EXTRA_FAILURE:
                        sys.exit(1)
                    else:
                        raise RuntimeError(
                            "policy execution failed due to missing dependencies in the runtime environment"
                        )
                for imp in self.packages.values():
                    subprocess.call(
                        [
                            sys.executable,
                            "-m",
                            "pip",
                            "install",
                            f"{imp.package_name}{imp.version_constraint}",
                        ]
                    )
            else:
                if TERMINATE_ON_EXTRA_FAILURE:
                    sys.exit(1)
                else:
                    raise RuntimeError(
                        "policy execution failed due to missing dependencies in the runtime environment"
                    )
        else:
            if TERMINATE_ON_EXTRA_FAILURE:
                sys.exit(1)
            else:
                raise RuntimeError(
                    "policy execution failed due to missing dependencies in the runtime environment"
                )

    @staticmethod
    def find_all() -> list["Extra"]:
        return list(Extra.extras.values())
