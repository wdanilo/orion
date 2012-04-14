#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from setuptools import setup, find_packages

setup(
    name                 = 'orion.example',
    version              = '0.1a',
    author               = 'Orion Team',
    author_email         = 'info@orion-wm.org',
    license              = 'BSD',
    zip_safe             = True,
    packages             = find_packages(),
    include_package_data = True,

    namespace_packages   = [
        'orion',
        'orion.example',
    ],

    install_requires     = [
    ],

    entry_points = """

    [orion.plugins]
    orion.example = orion.example.plugin
    """


)
