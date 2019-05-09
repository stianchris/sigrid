#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2018-2019 Christian Brosig (TH Köln), Timo Platte (TH Köln)

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This package is used to import and store XML files originating from PSS-Sincal
in dataframes via the class XMLimport. It is based on the etree package.
"""

import os
import xml.etree.ElementTree as ET
import pandas as pd
import pickle

__author__ = "Christian Brosig (TH Köln), Timo Platte (TH Köln)"
__copyright__ = "Copyright 2018-2019 Christian Brosig (TH Köln), Timo Platte (TH Köln), GNU GPL 3"


class XMLimport():
    """
    This class enables you to import xml-files by PSS-Sincal.
    It provides functions to read the data in and store it in dataframes.

    """

    # %%
    def __init__(self, name, foldername, list_file, path=False):
        """
        Initialization of the DHimport class.

        Parameters
        ----------
        name: string
            Name of the network.

        foldername: string
            Name of the folder to import from

        list_file: dict
            list with the name of the files to be imported
            structure:
                {name of the dataframe: [filename , index-column]}
                    name of the dataframe: str
                    filename: str
                    index-column: str

        +++
        TODO:
            - imply a possibility to indicate paths different from
            the basepath.
        +++
        """
        self.name = name

        if path is False:
            # Filepath of the programm
            dname = os.path.dirname(os.path.realpath(__file__))
            self.base_path = dname+'/'+foldername
        else:
            self.base_path = path


        # List of filenames which are relevant to import the network:
        self.list_file = list_file

    # %%
    def find_file(self, filename):
        """
            Searches for filename in all folders below the programmfolder

            Parameters
            ----------
            filename: str
                This is the filename we are searching for
            base_path: str
                It is the base path where the programm is saved.
            xml_path: str
                This is the path of the file which is searched for.

            Returns
            ----------
            xml_path: str
                pathname of the searched file
        """

        for roots, dirs, files in os.walk(self.base_path):
            if filename in files:
                xml_path = os.path.join(roots, filename)

        return xml_path

    # %%
    def find_attributes(self, root):
        """
            searches for attributes of elements in XML_file

            Parameters
            ----------
            root:
                This is the root of the xml-file
            attr_series: list
                This is the list where all attributes of each element of the
                xml-file will be saved
            tagname:
                This is the name of the childs in xml-file
            attrib:
                These are the attributes of one element

            Returns
            ----------
            attr_series: list
                two series of all attributes in all elements in the
                xml-file

            TODO
            ----

            """

        attr_series = []
        if root.tag == 'xml':
            for child in root:
                tagname = child.tag.split('}', 1)[1]
                if tagname == 'data':
                    for element in child:
                        # transform the attributes to series
                        attrib = element.attrib
                        attr_series.append(pd.Series(attrib))
        return attr_series

    # %%
    def xmltodfs(self):
        """
        This function reads in the raw data of the xml-files specified in
        list_file and saves them in separate dataframes.

        Parameters
        ----------
        :self.list_file: dict
            a list of all files to be imported; parameter is taken from the
            class - no input parameter

        Returns
        -------
        None

        TODO
        ----
        - recode the for-loop to make it slimmer!
        """
        self.xmls = {}

        # for-loop for each name of list_file
        for name in self.list_file:
            # print of handling file
            print('Handling file: ' + self.list_file[name][0])

            # inserts all found files to list
            filepath = self.find_file(self.list_file[name][0])

            # parse the xml-file
            tree = ET.parse(filepath)

            # finds root of the xml-file
            xml_root = tree.getroot()

            # finds all attributes in xml-file
            attr_series_result = self.find_attributes(xml_root)

            # converts list into dataframe
            self.xmls[name] = pd.DataFrame.from_dict(data=attr_series_result,
                                                     orient='columns')

            # set the index column of the file, if one is given
            namegiven = len(self.list_file[name]) > 1
            isempty = self.xmls[name].empty

            if namegiven and not isempty:
                index = self.xmls[name][self.list_file[name][1]]
                self.xmls[name].index = index

            # The column Type contained lots of disturbing whitespaces
            if 'Type' in self.xmls[name].columns:
                self.xmls[name]['Type'] = self.xmls[name]['Type'].str.strip()

    # %%
    def exp_topickles(self, directory):
        """
        Exports the dataframes to the indicated directory.

        Parameters
        ----------
        directory: str
            name of the directory to be exported to

        self.list_file: dict
            a list of all files to be imported

        Returns
        -------
        None
        """
        for name in self.list_file:
            filename = directory+str(name)+'.p'
            pickle.dump(self.xmls[name], open(filename, 'wb'))

    # %%
    def imp_frompickles(self, directory):
        """
        Imports the dataframes from the indicated directory.

        Parameters
        ----------
        directory: str
            name of the directory to be imported from

        self.list_file: dict
            a list of all files to be imported

        Returns
        -------
        None
        """
        for name in self.list_file:
            filename = directory+str(name)+'.p'
            self.xmls[name] = pickle.load(open(filename, 'rb'))
