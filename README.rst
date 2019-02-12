sigrid (PSS sincal importer for grids) contains Python based scripts to import networks from PSS Sincal and convert them to PyPSA and TESPy networks. It was developed during the EU-funded project ES-Flex-Infra by Christian Brosig and is now published as a free package in the hope, that it may be useful to others. Feel free to further develop it!

Documentation
=============

The package consists of the modules xml_import, xml_to_pypsa and xml_to_tespy.
xml_import is the base class and provides basic functionality.
xml_to_pypsa implements filters to acquire the necessary data for pypsa and provides further functionality to test and process the grid.
xml_to_tespy does the same for the tespy environment

Installation
============

There is no integration in PyPSA or TESPy yet. To use this package, just clone it. It depends on the following packages, that are not in the standard library:
- pandas
- networkx
- utm
- pypsa
- tespy



License
=======

Copyright (C) 2018/2019 TH Köln, Christian Brosig.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

