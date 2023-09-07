import setuptools

from whatsapp_matrix.get_version import git_revision, git_tag, linkified_version, version

with open("requirements.txt") as reqs:
    install_requires = reqs.read().splitlines()

with open("requirements-dev.txt") as reqs:
    extras_require = {}
    current = []
    for line in reqs.read().splitlines():
        if line.startswith("#/"):
            extras_require[line[2:]] = current = []
        elif not line or line.startswith("#"):
            continue
        else:
            current.append(line)

extras_require["all"] = list({dep for deps in extras_require.values() for dep in deps})

try:
    long_desc = open("README.md").read()
except IOError:
    long_desc = "Failed to read README.md"

with open("whatsapp_matrix/version.py", "w") as version_file:
    version_file.write(
        f"""# Generated in setup.py

git_tag = {git_tag!r}
git_revision = {git_revision!r}
version = {version!r}
linkified_version = {linkified_version!r}
"""
    )

setuptools.setup(
    name="whatsapp-cloud",
    version=version,
    url="https://github.com/iKonoTelecomunicaciones/whatsapp-cloud",
    project_urls={
        "Changelog": "https://github.com/iKonoTelecomunicaciones/whatsapp-cloud/blob/master/CHANGELOG.md",
    },
    author="Juan Manuel Cardenas",
    author_email="juan.cardenas@ikono.com.co",
    description="A Whatsapp Matrix bridge.",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires="~=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Topic :: Communications :: Chat",
        "Framework :: AsyncIO",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    package_data={
        "whatsapp_matrix": [
            "example-config.yaml",
        ],
    },
    data_files=[
        (".", ["whatsapp_matrix/example-config.yaml"]),
    ],
)
