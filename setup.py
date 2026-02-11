from setuptools import setup, find_packages

setup(
    name="episim",
    version="0.1.0",
    description="Transform epidemic modeling papers into interactive simulators",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "anthropic>=0.50.0",
        "pymupdf>=1.24.0",
        "pydantic>=2.0",
        "scipy>=1.12.0",
        "numpy>=1.26.0",
        "streamlit>=1.35.0",
        "plotly>=5.20.0",
    ],
    extras_require={
        "dev": ["pytest>=8.0.0"],
    },
)
