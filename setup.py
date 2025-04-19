from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-ui-explorer",
    version="0.1.2",
    author="UI Explorer Developer",
    author_email="example@example.com",
    description="An MCP server for exploring and interacting with UI elements",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/modularflow/mcp-ui-explorer",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.10",
    install_requires=[
        "pyautogui",
        "pywinauto",
        "pillow",
        "pydantic>=2.0.0",
        "mcp>=1.6.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-ui-explorer=mcp_ui_explorer:wrapper.run",
        ],
    },
) 