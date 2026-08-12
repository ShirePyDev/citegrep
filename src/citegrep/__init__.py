"""DocuMind: RAG over PDFs with verifiable citations."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("citegrep")
except PackageNotFoundError:  # running from a checkout that was never installed
    __version__ = "0.0.0"
