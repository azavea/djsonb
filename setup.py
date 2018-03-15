#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

description = """
PostgreSQL json field support for Django.
"""


setup(
    name="djsonb",
    version="0.2.3",
    url="https://github.com/azavea/djsonb",
    license="BSD",
    platforms=["OS Independent"],
    description=description.strip(),
    author="",
    author_email="",
    keywords="django, postgresql, pgsql, jsonb, json, field",
    maintainer="",
    maintainer_email="",
    packages=find_packages(),
    include_package_data=False,
    install_requires=[
        "Django <1.12",
        "psycopg2 >=2.6"
    ],
    zip_safe=False,
    test_suite='tests',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Topic :: Internet :: WWW/HTTP",
    ]
)
