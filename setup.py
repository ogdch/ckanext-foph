from setuptools import setup, find_packages
import sys
import os

version = '0.0'

setup(
    name='ckanext-foph',
    version=version,
    description="CKAN extension for the FOPH for the OGD portal of Switzerland",
    long_description="""\
    """,
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[],
    keywords='',
    author='Liip AG',
    author_email='ogd@liip.ch',
    url='http://www.liip.ch',
    license='GPL',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.foph'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points=
    """
    [ckan.plugins]
    foph=ckanext.foph.plugins:FophHarvest
    foph_harvester=ckanext.foph.harvesters:FOPHHarvester
    [paste.paster_command]
    harvester=ckanext.foph.commands.harvester:Harvester
    """,
)
