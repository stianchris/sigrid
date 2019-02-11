#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  5 11:20:55 2018

@author: christian
"""

import os
import pandas as pd
import numpy as np
import math
import pypsa
import networkx as nx
import pickle
from xmlimport import XMLimport


class ImporterXMLSincal():
    """
    This class enables you to import xmls from PSS-Sincal into PyPSA.
    It provides functions to read the data in, convert it, test it and also
    to repair it if necessary.

    Parameters
    ----------
    list_file: (dict)
        list with all xml-files needed with their name and index-column

    +++
    TODO: - provide more functions to facilitate repairing of data.
          - clean up the code!
    +++
    """

    list_file = {'node': ['Node.xml', 'Node_ID'],
                 'terminal': ['Terminal.xml', 'Terminal_ID'],
                 'line': ['Line.xml', 'Element_ID'],
                 'element': ['Element.xml', 'Element_ID'],
                 'load': ['Load.xml', 'Element_ID'],
                 'graphicNode': ['GraphicNode.xml', 'Node_ID'],
                 'calcParameter': ['CalcParameter.xml', ],
                 'ecoStation': ['EcoStation.xml','EcoStation_ID'],
                 'breaker': ['Breaker.xml','Terminal_ID']}

    def __init__(self, name, foldername):
        """
        Initialization of the ImporterXMLSincal class.

        Parameters
        ----------
        name: string
            Name of the network.
        foldername: string
            Name of the folder to import from.

        +++
        TODO: - imply a possibility to indicate paths different
                from the basepath.
        +++
        """
        self.name = name
        self.foldername = foldername
        # Filepath of the programm
        self.base_path = os.path.dirname(os.path.realpath(__file__))+'/'+foldername

    def __repr__(self):
        return 'ImporterXMLSincal(name: {}, folder: {})'.format(self.name,
                                                                self.foldername)

    # %%
    def import_xml(self):
        xml = XMLimport(self.name,
                        foldername=self.foldername,
                        list_file=self.list_file)
        xml.xmltodfs()
        self.xmls = xml.xmls

    # %%
    def export_xml_topickles(self, directory):
        """
        Exports the dataframes to the indicated directory.

        Parameters
        ----------
        :directory (str):
            name of directory to export pickle to
        :self.list_file (dict):

        +++
        TODO: - check, if directory and files get overwritten and
                imply a warning!
        +++
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        else:
            print('path already exists - files might get overwritten!')
            input("PRESS ENTER TO CONTINUE. TO ABORT PRESS CTRL+C!")

        for name in self.list_file:
            filename = directory+'/'+str(name)+'.p'
            pickle.dump(self.xmls[name], open(filename, 'wb'))

    def import_xml_frompickles(self, directory):
        """
        Imports the dataframes from the indicated directory.

        Parameters
        ----------
            :directory (str):
                name of directory to import pickle from
            :self.list_file (dict):
                indicates which files need to be imported
            :self.xmls (dict):
                dict with all imported dataframes
        """
        self.xmls = {}
        for name in self.list_file:
            filename = directory+'/'+str(name)+'.p'
            self.xmls[name] = pickle.load(open(filename, 'rb'))

    def rawdataintegrity(self):
        """
        Performs all the checks and repairs automatically...

        +++
        TODO: - Write the function!
              - Create own functions for each check.
              - Extend the ability for checking.
        +++
        """
        print('performing line-check...')
        self.linecheck()
        print('further dataintegrity-check still needs to be written...')

    def linecheck(self):
        """
        Check if the data from imported xml files is valid, or if there are
        problems.
        Problems being checked for, are:
            - Elements (Lines), that connect more than one node.
            This would raise an error in the import function.

        +++
        TODO: -maybe check if nodes are connected otherwise (see comment ins
               function)
        +++
        """
        # Number of Nodes, that are connected by one element.
        nofel = self.xmls['terminal'].Element_ID.value_counts()
        # Sum of Elements (mostly lines), that connect more than 2 Nodes and
        # would thus create an error
        nofelsum = nofel[nofel > 2].count()
        if nofelsum > 0:
            print("WARNING: " + str(nofelsum) +
                  " Elements connect more than two nodes.")
            nofelmore = pd.DataFrame()
            nofelmore['#_nodes'] = nofel[nofel > 2]
            nofelmore['Element_ID'] = self.xmls['element'].loc[nofelmore.index,
                                                               'Element_ID']
            nofelmore['Type'] = self.xmls['element'].loc[nofelmore.index,
                                                         'Type']
            nofelmore['Name'] = self.xmls['element'].loc[nofelmore.index,
                                                         'Name']
            a = nofelmore.groupby('Type')['Type']
            print("These Elements have {} different Type(s): \n{}".format(
                    str(a.ngroups), str(list(a.groups.keys()))))
            # TODO:
            # Hier könnte man noch prüfen, ob die Knoten untereinander noch
            # eine Verbindung haben, oder ob diese alle nur einmal
            # im Element auftauchen.
            # nodes = self.xmls['Terminal'].loc[nofelmore.index,'Node_ID']
            return nofelmore
        elif nofel[nofel < 2].count() > 0:
            print('{} '.format(nofel[nofel < 2].count()),
                  'lines have less than two connected nodes!')
        else:
            print('lines checked - no line connects more than two components')

    def dummyparameters_tozerolines(self,
                                    r=0.0001,
                                    x=0.0001,
                                    b=0.0000002):
        """
        This function adds (missing) dummy-parameters to lines for r, x, and b.
        PyPSA might get problems in the power flow, if these parameters are
        missing. So this function detects missing values and filles them with
        values for r, x and b.

        Parameters
        ----------
        :r (float): default: 0.0001
        :x (float): default: 0.0001
        :b (float): default: 0.0000002

        +++
        TODO
        - implement any security checks?
        +++
        """

        r = 0.0001
        x = 0.0001
        b = 0.0000002
        linesr0 = self.lines[self.lines['r'] == 0]
        for line in linesr0.index:
            self.lines.at[line, 'r'] = r

        linesx0 = self.lines[self.lines['x'] == 0]
        for line in linesx0.index:
            self.lines.at[line, 'x'] = x

        linesb0 = self.lines[self.lines['b'] == 0]
        for line in linesb0.index:
            self.lines.at[line, 'b'] = b

        print('The line parameters on following lines were changed:n/')
        print('r: {}'.format(linesr0.index.values))
        print('x: {}'.format(linesx0.index.values))
        print('b: {}'.format(linesb0.index.values))

    def repairlines(self, brokenlines):
        """
        This function repairs the lines, that are connected to more than
        two nodes, by splitting surplus nodes from the line and creating
        dummy lines with neglectable x, r and b to connect the other nodes.

        Parameters
        ----------
        :brokenlines (DataFrame):
            a list of those lines, that are broken with three columns
            #_nodes - the number of nodes connected to the element
            type - the Type of this element
            name - the Name of this element
            index - the Element-ID of this element
        +++
        TODO: clean up the code!
        - use .at instead of .loc for speedup??
        +++
        """
        line_num = 1
        for line in brokenlines['Element_ID']:

            # read and separate the data:
            filter_nodes = self.xmls['terminal']['Element_ID'] == line
            nodes = self.xmls['terminal'].loc[filter_nodes]

            line_inputnode = nodes[nodes['TerminalNo'] == '1']['Node_ID'].values[0] # unused? --> delete!
            line_outputnodes = nodes[nodes['TerminalNo'] == '2']['Node_ID']
            line_outputnode = line_outputnodes.values[0]
            surplus_nodes = line_outputnodes.values[1:]

            # change data in the xmls-dataframes
            i = 1
            node_from = line_outputnode
            for surplus_node in surplus_nodes:
                # create a new line without any resistance on the basis of
                # the old line:
                line_name = line+'s{}'.format(i)  # new nam
                # make a copy of existing line
                new_line = self.xmls['line'].loc[line].copy()
                new_line['Element_ID'] = line_name
                new_line['r'] = '0.0001'
                new_line['r0'] = '0.0001'
                new_line['x'] = '0.0001'
                new_line['x0'] = '0.0001'
                new_line['l'] = '1'
                new_line['c'] = '0.00002'
                new_line.name = line_name

                self.xmls['line'].loc[line_name] = new_line
                # duplicate also the entry in the element-dataframe:
                new_element = self.xmls['element'].loc[line].copy()
                new_element.name = line_name
                new_element['Element_ID'] = line_name
                self.xmls['element'].loc[line_name] = new_element
                # get the terminal entry
                choose_nodes = self.xmls['terminal'][self.xmls['terminal']['Node_ID']==surplus_node]
                term_id = choose_nodes['Terminal_ID'].loc[choose_nodes['Element_ID'] ==line].values[0]

                # rewrite the terminal entry
                self.xmls['terminal'].loc[term_id, 'Element_ID'] = line_name
                if self.xmls['terminal'].loc[term_id, 'TerminalNo'] == '1':
                    print('oh')
                self.xmls['terminal'].loc[term_id, 'TerminalNo'] = '2'

                # append a new terminal entry
                new_term_id = term_id+'s'+str(i)
                # duplicate entry
                terminal_entry = self.xmls['terminal'].loc[term_id]
                # rewrite entry
                terminal_entry.name = new_term_id
                self.xmls['terminal'].loc[new_term_id] = terminal_entry
                self.xmls['terminal'].loc[new_term_id, 'Terminal_ID'] = new_term_id # maybe not necessary??
                self.xmls['terminal'].loc[new_term_id, 'TerminalNo'] = '1'
                self.xmls['terminal'].loc[new_term_id, 'Node_ID'] = node_from

                node_from = surplus_node

                i = i+1
            print('repaired line {} of {}'.format(line_num,
                                                  brokenlines.index.size))
            line_num += 1
        print('finished repairing lines')

    def dfstocomponents(self, set_net_voltage='0'):
        """
        Converts and filters the dataframes from the raw xml-data
        into pypsa readable dataframes.

        Parameters
        ----------
        :set_net_voltage (String):
            with this parameter you can set the net-operating-voltage. If not
            set it will be taken from Sincal. In some cases this helps to
            include Eco-Stations as generators or loads. In 0.4 kV
            networks, declared as general stations will be translated to
            generators. In 10 kV networks they will be translated to loads.

        +++
        TODO: rewrite the function in a way, that an API can be used to
          automately translocate the values and set up the dataframes?
        - clean the code.
        - avoid int/float bus-names! write a bus- in front...

        +++

        """

        if set_net_voltage == '0':
            self.net_voltage = self.xmls['calcParameter']['Uref'].values[0]
        else:
            self.net_voltage = set_net_voltage

        try:
            import utm
        except ImportError:
            raise ImportError('<no module named utm found>')
        # create buses dataframe:
        self.buses = pd.DataFrame()
        self.buses['v_nom'] = self.xmls['node']['VoltLevel_ID']

#        for name in self.buses.index:
#            new_name = 'b'+str(name)
#            self.buses['name'].loc[name] = new_name
#        self.buses.index = self.buses['name']
        self.buses.index.name = 'name'

        # transform utm values to latlong
        rw_list = self.xmls['graphicNode']['NodeStartX']
        hw_list = self.xmls['graphicNode']['NodeStartY']

        lat_list = rw_list.copy()
        lat_list[:] = 0.0
        lat_list[:] = 0.0 #  for some reason this needs to be done, to make this a float
        long_list = hw_list.copy()
        long_list[:] = 0.0
        long_list[:] = 0.0
        for ind in rw_list.index:
            rw = float(rw_list[ind])
            hw = float(hw_list[ind])
            lat, long = utm.to_latlon(easting=rw,
                                      northing=hw,
                                      zone_number=32,
                                      northern=True)
            lat_list[ind] = lat
            long_list[ind] = long

        self.buses['x'] = lat_list
        self.buses['y'] = long_list
        self.buses['carrier'] = 'AC'
        self.buses['frequency'] = int(self.xmls['calcParameter']['f'].values[0])

        # create lines dataframe:
        self.lines = pd.DataFrame()
        lineterminal = self.xmls['terminal']
        lineterminal['breaker_state'] = '1'
        
        # filter lines, that are not connected due to breakers:
        if not self.xmls['breaker'].empty:
            breaker_state = self.xmls['breaker']['Flag_State']
            for term_id in breaker_state.index:
                state = breaker_state[term_id]
                if len(state) == 1:
                    lineterminal['breaker_state'].loc[term_id] = state
                else:
                    # TODO: if one of the states is 0, pass that one!
                    lineterminal['breaker_state'].loc[term_id] = state.ix[0]

        lineterminal.index = lineterminal['Element_ID']
        lineterminal = lineterminal[self.xmls['element']['Type'] == 'Line']

        # gather all lines to be deleted here:
        self.line_del = lineterminal['Element_ID'][lineterminal['breaker_state'] == '0']

        self.lines['bus0'] = lineterminal[lineterminal['TerminalNo']=='1']['Node_ID']
        self.lines['bus1'] = lineterminal[lineterminal['TerminalNo']=='2']['Node_ID']
        # TODO: can this be written less time consuming???:
#        for line in self.lines.index:
#            self.lines['bus0'].loc[line] = 'b'+str(self.lines['bus0'].loc[line])
#            self.lines['bus1'].loc[line] = 'b'+str(self.lines['bus1'].loc[line])
        self.lines.index.name = 'name'

         # Filtern der benötigten Daten:
        line_fl = self.xmls['line'][['Ith',
                                     'Un',
                                     'c',
                                     'fn',
                                     'l',
                                     'q',
                                     'r',
                                     'x']].astype(float)
        # Multiplication of l and r to get the overall r
        self.lines['r'] = line_fl['l'].multiply(line_fl['r'])
        # Multiplication of l and x to get the overall x
        self.lines['x'] = line_fl['l'].multiply(line_fl['x'])
        # Multiplication of l and c, and radial frequency
        self.lines['b'] = line_fl['l'].multiply(line_fl['c']*2*math.pi*50/1000)

        self.lines['s_nom'] = line_fl['Ith'] * 1  # TODO: imply real formula!

        # delete lines, that are not connected
        self.lines = self.lines.drop(self.line_del)

        # create slack generators dataframe (for given Infeed-nodes):
        self.generators = pd.DataFrame()
        self.generators['name'] = self.xmls['element'][self.xmls['element']['Type']=='Infeeder']['Element_ID']
        self.generators.index = self.generators['name']
        self.generators = self.generators.drop(columns='name')
        self.generators['control'] = 'slack'  # Only for Infeeders!
        self.generators['bus'] = 'nan'  # create a dummy
        # TODO: is this also possible without the for loop?
        # connect the generator to a bus
        for gname in self.generators.index:
            gen_bus = self.xmls['terminal'].loc[self.xmls['terminal']['Element_ID']==gname,'Node_ID']
            self.generators.loc[gname, 'bus'] = 'b'+str(gen_bus[0])

        # create slack generators dataframe (for given EcoStations):
        slacknodes = self.xmls['node']['EcoStation_ID'].astype(float)
        # get the type of the ecostations:
        # 1 = Netstation
        # 2 = Umspannstation
        # 3 = Schaltstation
        # 4 = Allgemeine Station
        # 5 = Verteilnetzstation
        if self.net_voltage == '10':
            lo = ['4']
            gen = ['1', '2']
        if self.net_voltage == '0.4':
            gen = ['1', '2', '4']
        ecost_type = self.xmls['ecoStation']['Flag_Typ']
        slacknodes = slacknodes[slacknodes > 0]
        slacknodes = slacknodes.astype(int)
        for node_id in slacknodes.index:
            ecost = slacknodes[node_id]
            ecotp = ecost_type[str(ecost)]
            if ecotp in gen:
                gen_name = self.xmls['node'].loc[node_id, 'Name'].strip()
                generator = pd.Series()
                generator.name = gen_name
                generator['control'] = 'slack'
#                generator['bus'] = 'b'+str(node_id)
                generator['bus'] = node_id
                self.generators.loc[gen_name] = generator
            elif ecotp in lo:
                pass  # TODO! needs to be written!

        if not self.xmls['load'].empty:
            self.loads = pd.DataFrame()

            # eap = jahreswirkverbrauch in kwh
            self.loads['p_set'] = self.xmls['load']['Eap'].astype(int) / 1000
            # self.loads['q_set'] = self.xmls['load']['Eap'].astype(int)
            self.loads['bus'] = self.xmls['load']['Element_ID'] #  TODO: is this true?? Not Node_ID??? and the b in front!!
            names = []
            for name in self.xmls['load']['Element_ID']:
                names += ['l'+name]
            self.loads['name'] = names
            self.loads = self.loads.reset_index()
            # for some nodes, several loads may exist; count them:
            counts = self.loads['name'].value_counts()
            for i in counts.index:
                val = counts[i]
                if val > 1:
                    add = 0
                    group = self.loads['name'][self.loads['name'] == i]
                    for load in group.index:
                        new_name = i+'_'+str(add)
                        add += 1
                        self.loads.loc[load, 'name'] = new_name
            self.loads.index = self.loads['name']
            self.loads = self.loads.drop(columns='name')

    def check_busbars(self):
        """
        Check, if nodes are connected via busbars, which in PSS-Sincal is
        given by the InclName argument.
        Returns the InclName row with all relevant entries.

        Returns
        -------
        inc_names: pd.Series()

        """

        # store the InclName row
        inc_names = self.xmls['node']['InclName']
        # drop nans
        inc_names = inc_names.dropna()
        # drop whitespaces
        for node_id in inc_names.index:
            inc_names[node_id] = inc_names[node_id].strip()
        # drop empty entries
        inc_names_notempty = inc_names != ''
        inc_names = inc_names[inc_names_notempty]
        # print out the list of all entries, to be able to check them
        print('The following InclNames were found:')
        print(inc_names)
        return inc_names

    def connect_busbars(self, inc_names, keys=False):
        """
        Takes the series of InclName and checks them for the given keys,
        then connects all components with the given keys.

        Parameters
        ----------
        inc_names : pd.Series()
            all relevant InclNames from the PSS-Sincal node dataframe
        keys : list
            the keys allow to check for tags inside the inc_names list, which
            identify the common busbar and thus, which elements should be
            connected

        +++
        TODO: check first, if the pypsa components already exist - if not,
        it is not possible to connect the components!!
        +++
        """
        if hasattr(self, 'network'):

            connect_dict = {}
    
            # if no key for the connection is given, all nodes are connected
            # with each other
            if keys is False:
                for node_id in inc_names.index:
                    connect_dict[node_id] += [node_id]
                    i = -1
                    for number in connect_dict:
                        self.network.add("Line",
                                         "busbar" + str(number),
                                         bus0=buses_list[i],
                                         bus1=buses_list[i+1],
                                         b=0.0000002,
                                         r=0.0001,
                                         x=0.0001)
                        i += 1
    
            # else only those containing the key are connected to each other
            else:
                for key in keys:
                    connect_dict[key] = []
                    for node_id in inc_names.index:
                        if key in inc_names[node_id]:
                            connect_dict[key] += [node_id]
            # print(connect_dict)
    
                for key in keys:
                    buses_list = connect_dict[key]
                    i = -1
                    for number in buses_list:
                        self.network.add("Line",
                                         "busbar" + str(number),
                                         bus0=buses_list[i],
                                         bus1=buses_list[i+1],
                                         b=0.0000002,
                                         r=0.0001,
                                         x=0.0001)
                        i += 1

    def connect_stationstolines(self,
                                bindings,
                                b=0.0000002,
                                r=0.0001,
                                x=0.0001):
        """
        Takes a dataframe of line and node ID's to be connected and connects
        them with a dummy line

        Parameters
        ----------
        bindings : pd.DataFrame()
            line and node ID's to be connected to each other.

        +++
        TODO: - rewrite the function in a way, that it is universally usables
              - rename variable bindings to something understandable
        +++
        """
        if hasattr(self, 'network'):

            # strip whitespaces from element-names
            for element in self.xmls['element'].index:
                el_name = self.xmls['element'].loc[element, 'Name'].strip()
                self.xmls['element'].loc[element, 'Name'] = el_name

            # run through all the connections to be made and connect them
            for bin_id in bindings:
                station_id = bindings.loc['ID_Station',bin_id]
                eq_col = self.xmls['node']['Equipment_ID'] == station_id
                ecol = self.xmls['node'][eq_col]
                if not ecol.empty:
                    enode_id = ecol.index.values[0]

                line_id = bindings.loc['ID_Kabel',bin_id]
                line_id = 'ID_'+line_id
                lin_col = self.xmls['element']['Name'] == line_id
                lcol = self.xmls['element'][lin_col]
                lelement_id = lcol.index.values[0]

                term_id = self.xmls['terminal']['Node_ID'].loc[lelement_id].values
                for node in term_id:
                    term_col = self.xmls['terminal']['Node_ID'] == node
                    check = self.xmls['terminal']['Node_ID'][term_col]
                    if len(check) == 1:
                        i = 0
                        newline_name = str(lelement_id)+str(i)
                        
                        while newline_name in self.network.lines.index:
                            i += 1
                            newline_name = str(lelement_id)+str(i)
                        self.network.add("Line",
                                         newline_name,
                                         bus0=check.values[0],
                                         bus1=enode_id,
                                         b=b,
                                         r=r,
                                         x=x)

    def importloadswithprofiles(self,
                                filename,
                                ltype='rh0',
                                feedin=False,
                                replacetime=False):
        """
        This function imports loadprofiles and transforms them into a pypsa
        readable dataframe.

        Parameters
        ----------
        :filename (str):
            name of the load-profile file to be imported
            this file should be a .csv with rows:
                Time;bus;bus;...
                YYYY/MM/DD HH:MM;1,3;2,1;...
                meaning the bus, that the load is connected to.
                P in kW
        :ltype (str):
            type of the load, to distinguish several loads at the same bus
        :feedin (bool):
            if the load is actually a feedin, this can be set here
        :replacetime (bool):
            if there should be a problem with summer and winter time, this can
            be set to replace the datetimeindex

        +++
        TODO: - implement an option to include unique identifiers in the csv
              - change lambda and use a def instead...
        +++
        """
        # to correctly import date and time, this function is defined:
        dateparse = lambda x: pd.datetime.strptime(x, '%Y/%m/%d %H:%M')
        loaddat = pd.read_csv(filename,
                              sep=';',
                              parse_dates=['Time'],
                              date_parser=dateparse)
        loaddat.index = loaddat['Time']
        loaddat = loaddat.drop(columns='Time')

        # PyPSA has problems with summer and winter time. If necessary, they
        # can be replaced here:
        if replacetime is True:
            start_time = loaddat.index[0]
            end_time = loaddat.index[-1]
            f = '15min'
            dti = pd.date_range(start=start_time,
                                end=end_time,
                                freq=f)
            loaddat.index = dti

        # convert kW to MW
        loaddat = loaddat/1000

        # if it is a feedin, this is converted here:
        if feedin is True:
            loaddat = loaddat*(-1)

        if not hasattr(self, 'loads'):
            print('no loads until now. Implementing.')
            self.loads = pd.DataFrame(columns=['bus', 'p_set'])
            self.loads.index.name = 'name'

        i = 0
        for node in loaddat.columns:
            new_node = node
            if '.' in node:
#                new_node = node[0:len(node)-3]  # clean it from any float-numbers
                print('WARNING: the load on bus {} may not be recognized!'.format(node),
                      'Please clean it from any float-numbers.',
                      'If a . is part of the name, ignore this warning.')
            name = 'l'+new_node+ltype

            if feedin is True:
                p_set = loaddat[node].min()
            else:
                p_set = loaddat[node].max()
            load = {'bus': new_node,
                    'p_set': p_set}
            self.loads.loc[name] = load
            i += 1

        if not hasattr(self, 'snapshots'):
            print('no loadprofile until now. Implementing.')
            column = loaddat.columns[0]
            self.snapshots = loaddat[column].copy()
            self.snapshots.name = 'weighting'
            self.snapshots[:] = 1

        if not hasattr(self, 'loads_p_set'):
            self.loads_p_set = loaddat.copy()
            for column in self.loads_p_set.columns:
                self.loads_p_set = self.loads_p_set.rename(columns={column: 'l'+column+ltype})
        else:
            loads_p_set_local = loaddat.copy()
            for column in loads_p_set_local.columns:
                new_columnname = 'l'+column+ltype
                loads_p_set_local = loads_p_set_local.rename(columns={column: new_columnname})
                self.loads_p_set[new_columnname] = loads_p_set_local[new_columnname]

    def importnetwork(self):
        """
        This function imports the converted dataframes into pypsa, checks the
        network for consistency and prints out, if not connected subgraphs are
        present.

        +++
        TODO:
        - check if the dataframes are available. (partly done)
        - rewrite the code with less lines...
        - loads-p_set??? --> check for cls names!
        - replace try with hasattr
        +++

        """

        self.network = pypsa.Network()
        try:
            self.network.import_components_from_dataframe(self.buses, 'Bus')
            self.network.import_components_from_dataframe(self.lines, 'Line')
        except:
            print('ERROR: No buses or lines found! or problems with import')

        if hasattr(self, 'loads'):
            self.network.import_components_from_dataframe(self.loads, 'Load')
        else:
            print('no loads implemented')

        if hasattr(self, 'generators'):
            self.network.import_components_from_dataframe(self.generators,
                                                          'Generator')
        else:
            print('no generators implemented')

        if hasattr(self, 'snapshots'):
            print('implementing snapshots')
            self.network.set_snapshots(self.snapshots.index)

        if hasattr(self, 'loads_p_set'):
            print('implementing load series')
            self.network.import_series_from_dataframe(self.loads_p_set,
                                                      'Load',
                                                      'p_set')
        self.network.consistency_check()

    def check_connectivity(self, printdata=False):
        """
        checks, if there are not connected graphs inside the network and
        prints out additional information to each graph, if printdata is
        set to True.
        
        Parameters
        ----------
        printdata: boolean (default: False)
            if set to True, the function will print the nodes and edges of
            each subgraph/-network
        """

        g = self.network.graph()
        if nx.number_connected_components(g) > 1:
            print('The network consists of {} not connected subgraphs.'.format(nx.number_connected_components(g)))
            if g.is_directed():
                g = g.to_undirected()
            sub_graphs = nx.connected_component_subgraphs(g)
            if printdata is True:
                for i, sg in enumerate(sub_graphs):
                    numon = sg.number_of_nodes()
                    print("subgraph {} has {} nodes".format(i, numon))
                    print("\tNodes:", sg.nodes(data=True))
                    print("\tEdges:", sg.edges())

    def del_littlesubgraphs(self, max_busnumber=1):
        """
        function deletes subgraphs that are too small.
        
        Parameters
        ----------
        max_busnumer: (int)
            all sub_networks with less or equal amount of buses will
            be deleted

        Returns
        -------
        None

        +++
        TODO:
            - find a faster way to define the subnetwork - this is too long!
        +++
        """
        for subnet in self.network.sub_networks.index:
            sub = self.network[self.network.buses.sub_network == subnet]
            netlength = len(sub.buses)

            if netlength <= max_busnumber:
                sub_buses = sub.buses
                sub_lines = sub.lines
                sub_generators = sub.generators
                sub_loads = sub.loads
                for bus in sub_buses.index:
                    self.network.remove('Bus', name=bus)
                for line in sub_lines.index:
                    self.network.remove('Line', name=line)
                for generator in sub_generators.index:
                    self.network.remove('Generator', name=generator)
                for load in sub_loads.index:
                    self.network.remove('Load', name=load)

    def plot_subgraphs(self, networkname):
        """
        function plots subgraphs one by one and stores them.

        +++
        TODO:
            function needs to be written...
        +++
        """
        import matplotlib.pyplot as plt
        import plotly.offline as pltly
        pltly.init_notebook_mode(connected=True)
        path = 'subnetwork_plots_{}/'.format(networkname)
        for subnet in self.network.sub_networks.index:
            fig, ax = plt.subplots(nrows=1, ncols=1)
            sub = self.network[self.network.buses.sub_network == subnet]
            sub.plot(ax=ax)
            fig.savefig(path+'sub'+subnet+'.png')
            plt.close(fig)
            print('bla')

    def plot_subgraphs_onefig(self, save=False):
        """
        This function plots subgraphs in one figure with separate colors for
        each one.
        It is useful, if you want to find out, which lines are connected to
        which subgraph.
        Caution: for big networks, the plotting takes time!

        +++
        TODO:
            find an option to save this figure without losses - as pickles?
        +++
        """
        import matplotlib.pyplot as plt
        import random

        def r(): return random.randint(0, 255)
        path = 'subnetwork_plots/'
        fig, ax = plt.subplots(nrows=1, ncols=1)

        for subnet in self.network.sub_networks.index:
            color = '#%02X%02X%02X' % (r(), r(), r())
            sub = self.network[self.network.buses.sub_network == subnet]
            sub.plot(ax=ax,
                     line_colors=color)
            print('integrated subnet {}'.format(subnet))
        if save is True:
            fig.savefig(path+'subnetsincolor.png')
