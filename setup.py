from setuptools import setup, find_packages

setup(
    name="tinygit",
    version="0.1.0",
    packages=["tinygit"],
    include_package_data=True,
    package_data={"tinygit": ["templates/*.html", "static/*.css"]},
    install_requires=[
        "flask>=3.0",
        "mistune>=3.0",
        "pygments>=2.17",
        "click>=8.0",
    ],
    entry_points={
        "console_scripts": [
            "tinygit=tinygit.cli:cli",
        ],
    },
)
