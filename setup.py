from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ui-explorer-mcp",
    version="0.1.0",
    author="UI Explorer Developer",
    author_email="example@example.com",
    description="An MCP server for exploring and interacting with UI elements",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ui-explorer-mcp",
    packages=find_packages(),
    py_modules=["mcp_ui_explorer", "hierarchical_ui_explorer", "ui_hierarchy_click"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.10",
    install_requires=[
        "fastmcp>=2.0.0",
        "pyautogui",
        "pywinauto",
        "pillow",
    ],
    entry_points={
        "console_scripts": [
            "ui-explorer-mcp=mcp_ui_explorer:mcp.run",
        ],
    },
) 