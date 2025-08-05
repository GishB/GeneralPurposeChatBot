from setuptools import setup, find_packages

__version__ = "0.2.4"

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="UnionChatBot",
    version=__version__,
    python_requires=">=3.10.0",
    url="https://github.com/GishB/GeneralPurposeTelegramBOT",
    license="MIT License",
    author="Aleksandr Samofalov",
    author_email="SamofalovWORK@yandex.ru",
    description="TelegramBot for general questions related to documents via Yandex API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(
        where="src",
        exclude=[
            "tests*",
            "experiments*",
            "docs*",
            ".*",
            "*.egg-info",
            "build*",
            "dist*",
        ],
    ),
    install_requires=requirements,
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: Alpha",
        "Intended Audience :: Develop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Topic :: Develop/Engineering :: Text Information Analysis",
        "Operating System :: OS Ubuntu 2022 TLS",
    ],
    project_urls={
        "Bug Reports": "https://github.com/GishB/GeneralPurposeTelegramBOT/issues",
        "Source": "https://github.com/GishB/GeneralPurposeTelegramBOT",
    },
    keywords=["YandexGPT API", "LLM", "RAG", "TelegramBot"],
)
