#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  9 17:14:55 2018

@author: christian
"""

import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import operator
import pickle
import pylab

from tespy import nwk, con, subsys, cmp
from tespy.helpers import MyComponentError
from dhs_comps import single_consumer as sc
from dhs_comps import pressurereg
from dhs_comps import infeeder
from dhs_comps import simple_fork as sf
from dhs_comps import pipe_fb as pipe

from xmlimport import XMLimport


class DHimport():
    """
    This class enables you to import district heating networks from
    xml-files by PSS-Sincal and transform it into a TESPy district heating
    network.
    It provides functions to read the data in, convert it, test it and also
    to repair it, if necessary.

    """

    # %%
    def __init__(self, name, foldername):
        """
        Initialization of the DHimport class.

        Parameters
        ----------
        name: str
            Name of the network.
        foldername: str
            Name of the folder to import from.

        +++
        TODO: imply a possibility to indicate paths different from the
        basepath.
        +++
        """
        self.name = name
        self.foldername = foldername
        # Filepath of the programm
        path = os.path.dirname(os.path.realpath(__file__))
        self.base_path = path + '/' + foldername
        # List of filenames which are relevant to import the network:
        self.list_file = {'flowNode': ['FlowNode.xml', 'Node_ID'],
                          'flowTerminal': ['FlowTerminal.xml', 'Element_ID'],
                          'flowLine': ['FlowLine.xml', 'Element_ID'],
                          'flowElement': ['FlowElement.xml', 'Element_ID'],
                          'flowGraphicNode': ['FlowGraphicNode.xml', 'Node_ID'],
                          'flowConsumer': ['FlowConsumer.xml', 'Element_ID'],
                          'flowNetworkLevel': ['FlowNetworkLevel.xml', ],
                          'flowHSNodeResult': ['FlowHSNodeResult_Schleppzeiger.xml', 'Node_ID'],
                          'flowPressureReg': ['FlowPressureReg.xml', 'Element_ID'],
                          'flowInfeeder': ['FlowInfeederH.xml', 'Element_ID']}

    def import_xml(self):
        """
        Execute the import by calling class XMLimport
        """
        xml = XMLimport(self.name, foldername=self.foldername,
                        list_file=self.list_file)
        xml.xmltodfs()
        self.xmls = xml.xmls

    def export_xml_topickles(self, directory):
        """
        Export the dataframes to the indicated directory.

        Parameters
        ----------
            directory: str

            self.list_file: dict

        +++
        TODO: imply a possibility to indicate paths different from the
        basepath.
        +++
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        for name in self.list_file:
            filename = directory + '/' + str(name) + '.p'
            pickle.dump(self.xmls[name], open(filename, 'wb'))

    # %%
    def import_xml_frompickles(self, directory):
        """
        Import the dataframes from the indicated directory.

        Parameters
        ------
            directory: str

            self.list_file: dict
                indicates which files need to be imported
            self.xmls: dict
                dict with all imported dataframes
        """
        self.xmls = {}
        for name in self.list_file:
            filename = directory + '/' + str(name) + '.p'
            self.xmls[name] = pickle.load(open(filename, 'rb'))

    # %%
    def creategraph(self, draw=True):
        """
        This function creates a networkx graph from the imported xml dataframes
        to validate the district heating network and further process it.
        
        Parameters
        ----------
        draw: boolean, default "True"
            
        +++
        TODO: implement checking functions (e.g. to check if the necessary
        DataFrames are available)
        +++
        """

        self.g = nx.Graph()

        nodes = list(self.xmls['flowNode'].index)
        x = self.xmls['flowGraphicNode']['NodeStartX']
        y = self.xmls['flowGraphicNode']['NodeStartY']
        for node in nodes:
            self.g.add_node(node, pos=tuple([float(x[node]), float(y[node])]))
        print("{} nodes in the network.".format(self.xmls['flowNode'].index.size))

        ### Diese Zeile produziert eine Warnung... Scheint aber nicht so schlimm zu sein...
        self.flowlines = self.xmls['flowTerminal'][self.xmls['flowElement']['Type'] == 'FlowLine']
        edges_gen = self.flowlines.groupby('Element_ID')['Node_ID']
        b = pd.DataFrame(edges_gen.first())
        b['Node_ID2'] = edges_gen.last()
        self.edges = b[['Node_ID', 'Node_ID2']].apply(tuple, axis=1)
        self.g.add_edges_from(self.edges.values)
        print("{} edges in the network.".format(len(self.g.edges)))
        pos = nx.get_node_attributes(self.g, 'pos')
        if draw == True:
            # nx.draw(self.g,pos,node_size=10)
            pylab.figure(1)
            nx.draw(self.g, pos)
            nx.draw_networkx_labels(self.g, pos, node_size=0.1)
            plt.draw()

    def link(self, comp1, comp2, num1=2, num2=1):
        """
        This function connects two components withfeed and back.

        Parameters
        ----------
        comp1: tespy.cmp object
            first component to be connected from
        num1: int, default "2"
            link-number to be connected from comp1
                --> leads to outlet out2; inlet in2
        comp2: tespy.cmp object
            second component to be connected to
        num1: int, default "1"
            link-number to be connected to comp2
                --> leads to inlet in1; outlet out1

         Returns
         -------
        conns: dict
            with two objects of type tespy.con.connection

        ###
        TODO
        ----
        - include temperature, pressure and fluid in inputs of the function.
        - include error messaging!
        ###
        """
        conns = {}
        
        # the infeeder needs 
        if isinstance(comp1,infeeder):
            conn1 = 'conn_' + str(comp1.label) + '-' + str(comp2.label)
            conns[conn1] = con.connection(comp1.outlet, 'out' + str(num1),
                                          comp2.inlet, 'in' + str(num2),
                                          T=90, p=15, fluid={'water': 1})
            conn2 = 'conn_' + str(comp2.label) + '-' + str(comp1.label)
            conns[conn2] = con.connection(comp2.outlet, 'out' + str(num2),
                                          comp1.inlet, 'in' + str(num1))

        elif isinstance(comp2,infeeder):
            conn1 = 'conn_' + str(comp1.label) + '-' + str(comp2.label)
            conns[conn1] = con.connection(comp1.outlet, 'out' + str(num1),
                                          comp2.inlet, 'in' + str(num2))
            conn2 = 'conn_' + str(comp2.label) + '-' + str(comp1.label)
            conns[conn2] = con.connection(comp2.outlet, 'out' + str(num2),
                                          comp1.inlet, 'in' + str(num1),
                                          T=90, p=15, fluid={'water': 1})
        else:
            conn1 = 'conn_' + str(comp1.label) + '-' + str(comp2.label)
            conns[conn1] = con.connection(comp1.outlet, 'out' + str(num1),
                                          comp2.inlet, 'in' + str(num2))
            conn2 = 'conn_' + str(comp2.label) + '-' + str(comp1.label)
            conns[conn2] = con.connection(comp2.outlet, 'out' + str(num2),
                                          comp1.inlet, 'in' + str(num1))
#            print('Linking component {} and {}.'.format(comp1.label,
#                                                        comp2.label))
#        except:
#            print('Problem with components {} and {}.'.format(comp1.label,
#                                                              comp2.label))
#            raise
        return conns

    def createTESPynet(self, name):
        """
        This function creates a district heating network with the python
        package TESPy, calculates it and saves it.

        Parameters
        ----------
            name: str
                name of the network to be created --> for storing!
        +++ 
        TODO:
        - split this function into several ones...
        - import all parameters into the components
        +++
        """
        fluids = ['water']
        T_unit = 'C'
        Tamb = 0
        Tamb_ref = 0

        # This should be parametrized to!
        self.xmls['flowNetworkLevel']

        self.nw = nwk.network(fluids=fluids, T_unit=T_unit, p_unit='bar', h_unit='kJ / kg',
                              p_range=[2, 30], T_range=[10, 100], h_range=[10, 380])

        print('Starting to create a TESPy district heating network.')

        # %% deadend-check
        self.nodeadends = False
        # TODO: put this into a function, to be able to iterate through dead-pipes!!!
        print('Terminal has {} entries bedore deadendcheck.'.format(str(len(self.xmls['flowTerminal']))))
        self.numberofdels = 0

        def deadendcheck():
            # Check for deadends first and delete them! - else there will be errors!
            allcon = self.xmls['flowTerminal'].groupby('Node_ID')['Element_ID']
            ball = allcon.count()
            self.df_filter = pd.DataFrame(data=ball, index=ball.index, columns=['Element_ID'])
            self.df_filter.columns = ['count_all']
            # dead-ends
            # network has errors - how to resolve?
            deadend = self.df_filter['count_all'][self.df_filter['count_all'] == 1]
            if len(deadend) > 0:
                print('deadend check found some dead_ends:')
                for node in ball[deadend.index].index:
                    # get the element connected to the node:
                    element = allcon.get_group(node)
                    print('deadend in node{}, with element {}.'.format(node, element[0]))
                    # delete all connections with the element
                    a = self.xmls['flowTerminal']
                    a = a.T
                    # print(len(a[element[0]].loc['Element_ID']))
                    self.numberofdels += len(a[element[0]].loc['Element_ID'])
                    del a[element[0]]
                    a = a.T
                    self.xmls['flowTerminal'] = a
                    # delete the element
                    a = self.xmls['flowElement']
                    a = a.T
                    # print(a[element[0]]['Element_ID'])
                    del a[element[0]]
                    a = a.T
                    self.xmls['flowElement'] = a
                    # delete the line
                    a = self.xmls['flowLine']
                    a = a.T
                    # print(a[element[0]]['Element_ID'])
                    del a[element[0]]
                    a = a.T
                    self.xmls['flowLine'] = a
            else:
                print('network cleaned from deadends!')
                self.nodeadends = True

        while self.nodeadends == False:
            deadendcheck()
        # print(self.numberofdels)
        print('Terminal has {} entries after deadendcheck.'.format(str(len(self.xmls['flowTerminal']))))
        
        # locate and save the input pressure!
        p_in = 15

        # %% components

        # sources and sinks in the Infeeder
        print('Creating infeeder...')
        infeed = {}
        for i in self.xmls['flowInfeeder'].index:
            infeed["infeed" + str(i)] = infeeder("infeed" + str(i))

        self.infeed = infeed

        # %% construction part
        print('Creating pipes...')

        # pipe_feedings and backs
        pipes = {}
        for i in self.xmls['flowLine'].index:
            ks = float(self.xmls['flowLine']['SandRoughness'][i]) / 1000  # TESPy parameter is in m!
            L = float(self.xmls['flowLine']['LineLength'][i])
            D = float(self.xmls['flowLine']['Diameter'][i]) / 1000  # TESPy parameter is in m!
            # TODO: kA is not yet implemented in the pipes component!!!
            # HeatingCond(uctivity) is in W/mK, whereas kA is in W/K
            kA = float(self.xmls['flowLine']['HeatingCond'][i]) * L
            kA = 2
            pipes['pipe' + str(i)] = pipe(label='pipe' + str(i), ks_pb=ks, L_pb=L,
                                          D_pb=D, ks_pf=ks, L_pf=L, D_pf=D,
                                          kA_pb=kA, kA_pf=kA, Tamb=Tamb,
                                          design_pf=['kA'], design_pb=['kA'])
        self.pipes = pipes

        # %% subsystems for consumers
        print('Creating consumers...')

        consumers = {}
        for i in self.xmls['flowConsumer'].index:
            consumers['con' + str(i)] = sc('con' + str(i))  # name of consumer; class defined above
            # consumer attributes
            ### TODO: import values from the xml-dataframes!
            # The xmls include Q1 to Q4, while Q1-Q3 are always empty,
            # Q4 sometimes is filled.. significance??
            Q = self.xmls['flowConsumer'].loc[i,'Power']
            # pDiffMin and pRelMin are given... 
            prelmin = float(self.xmls['flowConsumer'].loc[i,'pRelMin'])
            nodeid = self.xmls['flowTerminal'].loc[i,'Node_ID']
            results = self.xmls['flowHSNodeResult'].loc[nodeid]
            results = results[results['Circuit']=='1']['pDiff']
            pdiff = results.values
            pdiff = float(pdiff[0])
            pr = (p_in-prelmin)/p_in
            T_out = self.xmls['flowConsumer'].loc[i,'T']
            consumers['con' + str(i)].set_attr(Q=float(Q)*(-1000000),
                                               pr=pdiff,
                                               T_out=float(T_out))

        self.consumers = consumers

        print('Creating pressure regulators...')
        preg = {}
        for i in self.xmls['flowPressureReg'].index:
            preg["preg" + str(i)] = pressurereg("preg" + str(i))
            p_in = self.xmls['flowPressureReg'].loc[i,'pInlet']
            p_out = self.xmls['flowPressureReg'].loc[i,'pOutlet']
            pr = float(p_out)-float(p_in)
            zeta = 1
            preg["preg" + str(i)].set_attr(pr_vf=pr, pr_vb=pr,
                                           zeta_vf=zeta,zeta_vb=zeta)

        self.preg = preg

        # %% connections
        print('Creating connections...')
        # create a dict for connection objects stored inside
        conns = {}

        allcon = self.xmls['flowTerminal'].groupby('Node_ID')['Element_ID']
        ball = allcon.count()
        self.df_filter = pd.DataFrame(data=ball, index=ball.index, columns=['Element_ID'])
        self.df_filter.columns = ['count_all']

        # two-way connections
        twoway = self.df_filter['count_all'][self.df_filter['count_all'] == 2]
        self.twoway = twoway
        componentnames = {'FlowLine': 'pipe',
                          'FlowConsumer': 'con',
                          'FlowPressureReg': 'preg',
                          'FlowInfeederH': 'infeed'}
        for node in ball[twoway.index].index:
            elements = allcon.get_group(node)
            eltype = {}
            comps = []
            for i in elements:
                a = self.xmls['flowTerminal'].loc[i]
                if type(a) == type(pd.Series()):
                    side = int(a['TerminalNo'])
                else:
                    side = int(a[a['Node_ID'] == node]['TerminalNo'])
                el = {i: [componentnames[self.xmls['flowElement'].loc[i]['Type']], side]}
                eltype.update(el)
            # print(eltype)
            # Components get sorted, so that pipes always are first to be connected
            # else a consumer could get connected to the input of the fork...
            # Another solution is very welcome!
            sorted_eltype = sorted(eltype.items(), key=operator.itemgetter(1), reverse=True)
            # print('Sorted: '+str(sorted_eltype))
            for comp in sorted_eltype:
                if comp[1][0] == 'pipe':
                    comps += [pipes["pipe" + str(comp[0])]]
                elif comp[1][0] == 'con':
                    comps += [consumers["con" + str(comp[0])]]
                elif comp[1][0] == 'preg':
                    comps += [preg["preg" + str(comp[0])]]
                elif comp[1][0] == 'infeed':
                    comps += [infeed["infeed" + str(comp[0])]]

            # create connections:
            conns.update(self.link(comps[0],
                                   comps[1],
                                   num1=int(sorted_eltype[0][1][1]),
                                   num2=int(sorted_eltype[1][1][1])))

        # three-way connections
        threeway = self.df_filter['count_all'][self.df_filter['count_all'] == 3]
        self.threeway = threeway
        forks = {}
        componentnames = {'FlowLine': 'pipe',
                          'FlowConsumer': 'con',
                          'FlowPressureReg': 'preg',
                          'FlowInfeederH': 'infeed'}
        for node in ball[threeway.index].index:
            elements = allcon.get_group(node)
            eltype = {}
            comps = []
            for i in elements:
                a = self.xmls['flowTerminal'].loc[i]
                if type(a) == type(pd.Series()):
                    side = int(a['TerminalNo'])
                else:
                    side = int(a[a['Node_ID'] == node]['TerminalNo'])
                el = {i: [componentnames[self.xmls['flowElement'].loc[i]['Type']], side]}
                eltype.update(el)
            # print(eltype)
            # Components get sorted, so that pipes always are first to be connected
            # else a consumer could get connected to the input of the fork...
            # Another solution is very welcome!
            sorted_eltype = sorted(eltype.items(), key=operator.itemgetter(1), reverse=True)
            # print('Sorted: '+str(sorted_eltype))
            for comp in sorted_eltype:
                if comp[1][0] == 'pipe':
                    comps += [pipes["pipe" + str(comp[0])]]
                elif comp[1][0] == 'con':
                    comps += [consumers["con" + str(comp[0])]]
                elif comp[1][0] == 'preg':
                    comps += [preg["preg" + str(comp[0])]]
                elif comp[1][0] == 'infeed':
                    comps += [infeed["infeed" + str(comp[0])]]
            # create fork:
            forks['fork' + str(node)] = sf('fork' + str(node))

            # create connections:
            conns.update(self.link(comps[0],
                                   forks['fork' + str(node)],
                                   num1=int(sorted_eltype[0][1][1]),
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node)],
                                   comps[1],
                                   num1=2,
                                   num2=int(sorted_eltype[1][1][1])))
            conns.update(self.link(forks['fork' + str(node)],
                                   comps[2],
                                   num1=3,
                                   num2=int(sorted_eltype[2][1][1])))

        # print('node{} does not fit!!!!!!!!!!!!'.format(str(node)))

        # four-way connections
        fourway = self.df_filter['count_all'][self.df_filter['count_all'] == 4]
        self.fourway = fourway
        componentnames = {'FlowLine': 'pipe',
                          'FlowConsumer': 'con',
                          'FlowPressureReg': 'preg',
                          'FlowInfeederH': 'infeed'}
        for node in ball[fourway.index].index:
            elements = allcon.get_group(node)
            eltype = {}
            comps = []
            for i in elements:
                a = self.xmls['flowTerminal'].loc[i]
                if type(a) == type(pd.Series()):
                    side = int(a['TerminalNo'])
                else:
                    side = int(a[a['Node_ID'] == node]['TerminalNo'])
                el = {i: [componentnames[self.xmls['flowElement'].loc[i]['Type']], side]}
                eltype.update(el)
            # print(eltype)
            # Components get sorted, so that pipes always are first to be connected
            # else a consumer could get connected to the input of the fork...
            # Another solution is very welcome!
            sorted_eltype = sorted(eltype.items(), key=operator.itemgetter(1), reverse=True)
            # print('Sorted: '+str(sorted_eltype))
            for comp in sorted_eltype:
                if comp[1][0] == 'pipe':
                    comps += [pipes["pipe" + str(comp[0])]]
                elif comp[1][0] == 'con':
                    comps += [consumers["con" + str(comp[0])]]
                elif comp[1][0] == 'preg':
                    print('oho')
                    # comps += preg["preg"+str(comp[0])]
                elif comp[1][0] == 'infeed':
                    # comps += infeed["infeed"+str(comp[0])]
                    print('oho')

            # create two forks:
            forks['fork' + str(node) + '_1'] = sf('fork' + str(node) + '_1')
            forks['fork' + str(node) + '_2'] = sf('fork' + str(node) + '_2')
            # print(sorted_eltype[0][1][1][0])
            conns.update(self.link(comps[0],
                                   forks['fork' + str(node) + '_1'],
                                   num1=int(sorted_eltype[0][1][1]),
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_1'],
                                   comps[1],
                                   num1=2,
                                   num2=int(sorted_eltype[1][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_1'],
                                   forks['fork' + str(node) + '_2'],
                                   num1=3,
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_2'],
                                   comps[2],
                                   num1=2,
                                   num2=int(sorted_eltype[2][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_2'],
                                   comps[3],
                                   num1=3,
                                   num2=int(sorted_eltype[3][1][1])))

        # ES GIBT NOCH KNOTEN MIT 5 UND 6 ELEMENTEN!!!!
        # Außerdem können forks mit beliebig vielen Ausgängen erstellt werden...
        # Das auf lange Sicht komplett umschreiben... ist so viel zu langer Code...

        # fiveway
        fiveway = self.df_filter['count_all'][self.df_filter['count_all'] == 5]
        componentnames = {'FlowLine': 'pipe',
                          'FlowConsumer': 'con',
                          'FlowPressureReg': 'preg',
                          'FlowInfeederH': 'infeed'}
        for node in ball[fiveway.index].index:
            elements = allcon.get_group(node)
            eltype = {}
            comps = []
            for i in elements:
                a = self.xmls['flowTerminal'].loc[i]
                if type(a) == type(pd.Series()):
                    side = int(a['TerminalNo'])
                else:
                    side = int(a[a['Node_ID'] == node]['TerminalNo'])
                el = {i: [componentnames[self.xmls['flowElement'].loc[i]['Type']], side]}
                eltype.update(el)
            # print(eltype)
            # Components get sorted, so that pipes always are first to be connected
            # else a consumer could get connected to the input of the fork...
            # Another solution is very welcome!
            sorted_eltype = sorted(eltype.items(), key=operator.itemgetter(1), reverse=True)
            # print('Sorted: '+str(sorted_eltype))
            for comp in sorted_eltype:
                if comp[1][0] == 'pipe':
                    comps += [pipes["pipe" + str(comp[0])]]
                elif comp[1][0] == 'con':
                    comps += [consumers["con" + str(comp[0])]]
                elif comp[1][0] == 'preg':
                    print('oho')
                    # comps += preg["preg"+str(comp[0])]
                elif comp[1][0] == 'infeed':
                    # comps += infeed["infeed"+str(comp[0])]
                    print('oho')

            # create three forks:
            forks['fork' + str(node) + '_1'] = sf('fork' + str(node) + '_1')
            forks['fork' + str(node) + '_2'] = sf('fork' + str(node) + '_2')
            forks['fork' + str(node) + '_3'] = sf('fork' + str(node) + '_3')
            # print(sorted_eltype[0][1][1][0])
            conns.update(self.link(comps[0],
                                   forks['fork' + str(node) + '_1'],
                                   num1=int(sorted_eltype[0][1][1]),
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_1'],
                                   comps[1],
                                   num1=2,
                                   num2=int(sorted_eltype[1][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_1'],
                                   forks['fork' + str(node) + '_2'],
                                   num1=3,
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_2'],
                                   comps[2],
                                   num1=2,
                                   num2=int(sorted_eltype[2][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_2'],
                                   forks['fork' + str(node) + '_3'],
                                   num1=3,
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_3'],
                                   comps[3],
                                   num1=2,
                                   num2=int(sorted_eltype[3][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_3'],
                                   comps[4],
                                   num1=3,
                                   num2=int(sorted_eltype[4][1][1])))

        # sixway
        sixway = self.df_filter['count_all'][self.df_filter['count_all'] == 6]
        componentnames = {'FlowLine': 'pipe',
                          'FlowConsumer': 'con',
                          'FlowPressureReg': 'preg',
                          'FlowInfeederH': 'infeed'}
        for node in ball[sixway.index].index:
            elements = allcon.get_group(node)
            eltype = {}
            comps = []
            for i in elements:
                a = self.xmls['flowTerminal'].loc[i]
                if type(a) == type(pd.Series()):
                    side = int(a['TerminalNo'])
                else:
                    side = int(a[a['Node_ID'] == node]['TerminalNo'])
                el = {i: [componentnames[self.xmls['flowElement'].loc[i]['Type']], side]}
                eltype.update(el)
            # print(eltype)
            # Components get sorted, so that pipes always are first to be connected
            # else a consumer could get connected to the input of the fork...
            # Another solution is very welcome!
            sorted_eltype = sorted(eltype.items(), key=operator.itemgetter(1), reverse=True)
            # print('Sorted: '+str(sorted_eltype))
            for comp in sorted_eltype:
                if comp[1][0] == 'pipe':
                    comps += [pipes["pipe" + str(comp[0])]]
                elif comp[1][0] == 'con':
                    comps += [consumers["con" + str(comp[0])]]
                elif comp[1][0] == 'preg':
                    print('oho')
                    # comps += preg["preg"+str(comp[0])]
                elif comp[1][0] == 'infeed':
                    # comps += infeed["infeed"+str(comp[0])]
                    print('oho')

            # create two forks:
            forks['fork' + str(node) + '_1'] = sf('fork' + str(node) + '_1')
            forks['fork' + str(node) + '_2'] = sf('fork' + str(node) + '_2')
            forks['fork' + str(node) + '_3'] = sf('fork' + str(node) + '_3')
            forks['fork' + str(node) + '_4'] = sf('fork' + str(node) + '_4')
            # print(sorted_eltype[0][1][1][0])
            conns.update(self.link(comps[0],
                                   forks['fork' + str(node) + '_1'],
                                   num1=int(sorted_eltype[0][1][1]),
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_1'],
                                   comps[1],
                                   num1=2,
                                   num2=int(sorted_eltype[1][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_1'],
                                   forks['fork' + str(node) + '_2'],
                                   num1=3,
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_2'],
                                   comps[2],
                                   num1=2,
                                   num2=int(sorted_eltype[2][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_2'],
                                   forks['fork' + str(node) + '_3'],
                                   num1=3,
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_3'],
                                   comps[3],
                                   num1=2,
                                   num2=int(sorted_eltype[3][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_3'],
                                   forks['fork' + str(node) + '_4'],
                                   num1=3,
                                   num2=1))
            conns.update(self.link(forks['fork' + str(node) + '_4'],
                                   comps[4],
                                   num1=2,
                                   num2=int(sorted_eltype[4][1][1])))
            conns.update(self.link(forks['fork' + str(node) + '_4'],
                                   comps[5],
                                   num1=3,
                                   num2=int(sorted_eltype[5][1][1])))

        print('implementing the connections')
        self.conns = conns
        i = 0
        for conn in conns:
            # print('implement: '+str(conn))
            try:
                self.nw.add_conns(conns[conn])
                # print(str(conn))
            except:
                print("problems with connection {}; atm {} conns implemented.".format(str(conn), str(i)))
                raise
            i = i + 1

        print('implementing the consumers')
        for comp in consumers:
            self.nw.add_subsys(consumers[comp])
            # print(str(comp)+' added')

        print('implementing the pipes')
        for comp in pipes:
            self.nw.add_subsys(pipes[comp])

        print('implementing the infeeds')
        for comp in infeed:
            self.nw.add_subsys(infeed[comp])

        print('implementing the pressure-regulators')
        for comp in preg:
            self.nw.add_subsys(preg[comp])

        print('implementing all forks')
        for comp in forks:
            self.nw.add_subsys(forks[comp])

        # %% busses
        #
        heat_losses = con.bus('network losses')
        heat_consumer = con.bus('network consumer')

        print('checking network')
        self.nw.check_network()
        Tamb = 0

        for comp in self.nw.comps.index:
            if isinstance(comp, cmp.pipe):
                comp.set_attr(Tamb=Tamb)

                heat_losses.add_comps({'c': comp})

            if (isinstance(comp, cmp.heat_exchanger_simple) and
                    not isinstance(comp, cmp.pipe)):
                heat_consumer.add_comps({'c': comp})

        self.nw.add_busses(heat_losses, heat_consumer)

        self.nw.max_iter = 10
        self.nw.solve('design')
        self.nw.save(name, structure=True)
        
        print('Heat demand consumer:', heat_consumer.P.val)
        print('network losses at 0 °C outside temperature (design):', heat_losses.P.val)

    def creategraph1(self):
        import networkx as nx
        import pylab
        g = nx.Graph()
        for conn in self.nw.conns.index:
            nodename1 = str(conn.s.label) + str(conn.s_id)
            nodename2 = str(conn.t.label) + str(conn.s_id)
            if g.has_node(nodename1):
                print('node {} already in'.format(nodename1))
            else:
                g.add_node(nodename1)

            if g.has_node(nodename2):
                print('node {} already in'.format(nodename2))
            else:
                g.add_node(nodename2)
            # edgename = 'conn_'+str(conn.s.label)+'-'+str(conn.t.label)
            g.add_edge(nodename1, nodename2, name=str(conn.s.label) + str(conn.t.label))
        self.g = g
        pos = nx.spring_layout(g)
        pylab.figure(1)
        nx.draw(g, pos)
        nx.draw_networkx_labels(g, pos, node_size=0.1)


# def plotnw(nw):
#    import networkx as nx
#    from plotly.offline import download_plotlyjs, init_notebook_mode, iplot
#    from plotly.graph_objs import *
#    init_notebook_mode()
#    g = nx.Graph()
#    for conn in self.nw.conns.index:
#        nodename1 = str(conn.s.label)
#        nodename2 = str(conn.t.label)
#        if g.has_node(nodename1):
#            print('node {} already in'.format(nodename1))
#        else:
#            g.add_node(nodename1)
#        
#        if g.has_node(nodename2):
#            print('node {} already in'.format(nodename2))
#        else:
#            g.add_node(nodename2)
#        #edgename = 'conn_'+str(conn.s.label)+'-'+str(conn.t.label)
#        g.add_edge(str(conn.s.label),str(conn.t.label))
#    #print(g.nodes)
#    #print(g.edges)
#    #nx.draw_spring(g,node_size=0.1)
#    pos = nx.spectral_layout(g)
#    print(pos)
#    fig = go.Figure(data=[edge_trace, node_trace],
#                 layout=go.Layout(
#                    title='<br>Network graph made with Python',
#                    titlefont=dict(size=16),
#                    showlegend=False,
#                    hovermode='closest',
#                    margin=dict(b=20,l=5,r=5,t=40),
#                    annotations=[ dict(
#                        text="Python code: <a href='https://plot.ly/ipython-notebooks/network-graphs/'> https://plot.ly/ipython-notebooks/network-graphs/</a>",
#                        showarrow=False,
#                        xref="paper", yref="paper",
#                        x=0.005, y=-0.002 ) ],
#                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
#                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
#
#    py.iplot(fig, filename='networkx')


# %%

#dhi = DHimport('heatnet', 'WaermeNetz')
# dhi.import_xml()
# dhi.export_xml_topickles('pickles')

# dhi.creategraph(draw =True)

#dhi.import_xml_frompickles('pickles')
#dhi.import_xml_frompickles('pickles_little')
#dhi.createTESPynet()
#dhi.creategraph()


# dhi = DHimport('heatnet', 'WaermeNetz')
# dhi.import_xml_frompickles('pickles_little_little')
# dhi.createTESPynet()
#dhi.creategraph1()