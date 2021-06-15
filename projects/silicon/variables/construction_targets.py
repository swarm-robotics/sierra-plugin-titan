# Copyright 2021 John Harwell, All rights reserved.
#
#  This file is part of SIERRA.
#
#  SIERRA is free software: you can redistribute it and/or modify it under the
#  terms of the GNU General Public License as published by the Free Software
#  Foundation, either version 3 of the License, or (at your option) any later
#  version.
#
#  SIERRA is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
#  A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  SIERRA.  If not, see <http://www.gnu.org/licenses/

"""
Classes for different types of construction targets; cannot be used as a batch criteria or as a
variable on the cmdline. See :ref:`ln-silicon-var-ct-set` for usage documentation.
"""

# Core packages
import os
import logging
import typing as tp

# 3rd party packages
import networkx as nx

# Project packages
from sierra.core.vector import Vector3D
from sierra.core.xml_luigi import XMLTagAddList, XMLTagRmList, XMLTagRm, XMLTagAdd, XMLAttrChangeSet
from sierra.core.utils import ArenaExtent as ArenaExtent


class BaseConstructTarget():
    """
    Base Construction target class defining one or more 3D structures to be built.

    Attributes:
        structure: Dictionary of (key,value) pairs defining the structure, as returned by
                   :class:`ConstructTargetSetParser`.

        target_id: Numerical UUID for the structure.

    """

    def __init__(self, spec: dict, uuid: int, gml_path: str):

        self.spec = spec
        self.uuid = uuid
        self.gml_path = gml_path
        self.extent = ArenaExtent(origin=Vector3D(self.spec['anchor'][0],
                                                  self.spec['anchor'][1],
                                                  self.spec['anchor'][2]),
                                  dims=Vector3D(self.spec['bb'][0],
                                                self.spec['bb'][1],
                                                self.spec['bb'][2]))
        self.logger = logging.getLogger(__name__)

    def gen_xml(self) -> XMLTagAddList:
        """
        Generate XML tags for the construction target.
        """
        raise NotImplementedError

    def gen_gml(self) -> nx.Graph:
        """
        Generates GraphML for the construction target.
        """
        raise NotImplementedError

    def write_gml(self, graph: nx.Graph, path: str) -> None:
        """
        Writes generated GraphML to the filesystem.
        """
        nx.write_gml(graph, path, lambda x: str(x))

    def graph_block_add(self,
                        graph: nx.Graph,
                        block_type: str,
                        length_ratio: int,
                        c: Vector3D) -> None:
        """
        Idempotently add a node of the specified type and its edges.
        """

        # You don't need to worry about whether or not the edge or node already exists--networkx
        # handles this for us.
        if block_type == 'cube':
            self._graph_cube_add(graph, c)
        elif block_type == 'ramp':
            self._graph_ramp_add(graph, length_ratio, c)

    def _graph_cube_add(self, graph: nx.Graph, c: Vector3D) -> None:
        # Add anchor node
        self.logger.trace("Add cube anchor: %s", c)
        graph.add_node(c, color='b', pos=c)

        xratio = 1
        yratio = 1
        zratio = 1

        if c.x < self.extent.xsize() - xratio:
            dest = Vector3D(c.x + xratio, c.y, c.z)
            graph.add_edge(c, dest, weight=xratio)
            self.logger.trace("Add cube edge: %s -> %s,weight=%s", c, dest, xratio)

        if c.y < self.extent.ysize() - yratio:
            dest = Vector3D(c.x, c.y + yratio, c.z)
            graph.add_edge(c, dest, weight=yratio)
            self.logger.trace("Add cube edge: %s -> %s,weight=%s", c, dest, yratio)

        if c.z < self.extent.zsize() - zratio:
            dest = Vector3D(c.x, c.y, c.z + zratio)
            graph.add_edge(c, dest, weight=zratio)
            self.logger.trace("Add cube edge: %s -> %s,weight=%s", c, dest, zratio)

    def _graph_ramp_add(self, graph: nx.Graph, length_ratio: int, c: Vector3D) -> None:
        self.logger.trace("Add ramp anchor: %s", c)
        graph.add_node(c, color='r', pos=c)
        zratio = 1
        if self.spec['orientation'] in ['0', 'PI']:
            xratio = length_ratio
            yratio = 1
        elif self.spec['orientation'] in ['PI/2', '3PI/2']:
            xratio = 1
            yratio = length_ratio

        if c.x < self.extent.xsize() - xratio:
            dest = Vector3D(c.x + xratio, c.y, c.z)
            graph.add_edge(c, dest, weight=xratio)
            self.logger.trace("Add cube edge: %s -> %s,weight=%s", c, dest, xratio)

        if c.y < self.extent.ysize() - yratio:
            dest = Vector3D(c.x, c.y + yratio, c.z)
            graph.add_edge(c, dest, weight=yratio)
            self.logger.trace("Add cube edge: %s -> %s,weight=%s", c, dest, yratio)

        if c.z < self.extent.zsize() - zratio:
            dest = Vector3D(c.x, c.y, c.z + zratio)
            graph.add_edge(c, dest, weight=zratio)
            self.logger.trace("Add cube edge: %s -> %s,weight=%s", c, dest, zratio)


class RectPrismTarget(BaseConstructTarget):
    """
    Construction target class for 3D rectangular prismatic structures.
    """
    @staticmethod
    def target_id(uuid: int):
        return 'rectprism' + str(uuid)

    def __init__(self,
                 spec: tp.Dict[str, tp.Any],
                 uuid: int,
                 gml_path: str) -> None:
        super().__init__(spec, uuid, gml_path)
        self.tag_adds = []

    def gen_xml(self) -> XMLTagAddList:
        if not self.tag_adds:
            # Direct XML for simulation input file
            self.tag_adds = XMLTagAddList((XMLTagAdd('.//loop_functions/construct_targets',
                                                     'rectprism',
                                                     {
                                                         'id': self.target_id(self.uuid),
                                                         'bb': "{0},{1},{2}".format(self.extent.xsize(),
                                                                                    self.extent.ysize(),
                                                                                    self.extent.zsize()),
                                                         'anchor': "{0},{1},{2}".format(self.extent.origin().x,
                                                                                        self.extent.origin().y,
                                                                                        self.extent.origin().z),
                                                         'orientation': self.spec['orientation'],
                                                         'gml': self.gml_path
                                                     })))

        return self.tag_adds

    def gen_gml(self) -> nx.Graph:
        graph = nx.Graph()

        # For rectprisms, there is no difference in the generated GML for +X vs
        # -X, or +Y vs -Y.
        if self.spec['orientation'] in ['0', 'PI']:
            for x in range(0, self.extent.xsize()):
                for y in range(0, self.extent.ysize()):
                    for z in range(0, self.extent.zsize()):
                        self.graph_block_add(graph, 'cube', 1, Vector3D(x, y, z))
        elif self.spec['orientation'] in ['PI/2', '3PI/2']:
            for y in range(0, self.extent.ysize()):
                for x in range(0, self.extent.xsize()):
                    for z in range(0, self.extent.zsize()):
                        self.graph_block_add(graph, 'cube', 1, Vector3D(x, y, z))
        else:
            assert False, "FATAL: Bad orientation {0}".format(self.spec.orientation)

        return graph


class RampTarget(BaseConstructTarget):
    """
    Construction target class for 3D ramps.
    """

    """
    The ratio between the length of cube blocks and ramp blocks.
    """
    kRAMP_LENGTH_RATIO = 2

    """
    Construction target class for 3D rectangular prismatic structures.
    """
    @staticmethod
    def target_id(uuid: int):
        return 'ramp' + str(uuid)

    def __init__(self,
                 spec: tp.Dict[str, tp.Any],
                 uuid: int,
                 gml_path: str) -> None:
        super().__init__(spec, uuid, gml_path)
        self.tag_adds = []
        self._structure_sanity_checks()

    def _structure_sanity_checks(self):
        if self.spec['orientation'] in ['0', 'PI']:
            assert self.extent.xsize() % self.kRAMP_LENGTH_RATIO == 0,\
                "FATAL: X size={0} not a multiple for ramp block length ratio={1}".format(self.extent.xsize(),
                                                                                          self.kRAMP_LENGTH_RATIO)
        elif self.spec['orientation'] in ['PI/2', '3PI/2']:
            assert self.extent.ysize() % self.kRAMP_LENGTH_RATIO == 0,\
                "FATAL: Y size={0} not a multiple for ramp block length ratio {1}".format(self.extent.ysize(),
                                                                                          self.kRAMP_LENGTH_RATIO)
        else:
            assert False, "FATAL: Bad orientation {0}".format(self.spec.orientation)

    def gen_xml(self) -> XMLTagAddList:
        if not self.tag_adds:
            # Direct XML for simulation input file
            self.tag_adds = XMLTagAddList((XMLTagAdd('.//loop_functions/construct_targets',
                                                     'ramp',
                                                     {
                                                         'id': self.target_id(self.uuid),
                                                         'bb': "{0},{1},{2}".format(self.extent.xsize(),
                                                                                    self.extent.ysize(),
                                                                                    self.extent.zsize()),
                                                         'anchor': "{0},{1},{2}".format(self.extent.origin().x,
                                                                                        self.extent.origin().y,
                                                                                        self.extent.origin().z),
                                                         'orientation': self.spec['orientation'],
                                                         'gml': self.gml_path
                                                     })))

        return self.tag_adds

    def gen_gml(self) -> nx.Graph:
        graph = nx.Graph()

        # First, generate cube blocks
        self._gen_cube_blocks(graph)

        # Then, generate ramp blocks
        self._gen_ramp_blocks(graph)

        return graph

    def _gen_ramp_blocks(self, graph: nx.Graph) -> None:
        """
        Add the nodes containing the anchor cells of ramp blocks to the structure graph, along with
        the connections to their neighbors.
        """
        ratio = self.kRAMP_LENGTH_RATIO

        if self.spec['orientation'] in ['0', 'PI']:
            corr = 1
            for z in range(0, self.extent.zsize()):
                x = self.extent.xsize() - ratio * corr
                for y in range(0, self.extent.ysize()):
                    self.graph_block_add(graph, 'ramp', ratio, Vector3D(x, y, z))
                corr += 1

        elif self.spec['orientation'] in ['PI/2', '3PI/2']:
            for z in range(0, self.extent.zsize()):
                y = self.extent.ysize() - ratio * corr
                for x in range(0, self.extent.xsize()):
                    self.graph_block_add(graph, 'ramp', ratio, Vector3D(x, y, z))
                corr += 1

    def _gen_cube_blocks(self, graph: nx.Graph) -> None:
        """
        Add the nodes containing the anchor cells of cube blocks to the structure graph, along with
        the connections to their neighbors.
        """
        ratio = self.kRAMP_LENGTH_RATIO

        if self.spec['orientation'] in ['0', 'PI']:
            corr = 1
            for z in range(0, self.extent.zsize()):
                print(self.extent.xsize(), ratio, corr)
                for x in range(0, self.extent.xsize() - ratio * corr):
                    for y in range(0, self.extent.ysize()):
                        self.graph_block_add(graph, 'cube', 1, Vector3D(x, y, z))
                corr += 1
        elif self.spec['orientation'] in ['PI/2', '3PI/2']:
            corr = 1
            for z in range(0, self.extent.zsize()):
                for y in range(0, self.extent.ysize() - ratio * corr):
                    for x in range(0, self.extent.xsize()):
                        self.graph_block_add(graph, 'cube', 1, Vector3D(x, y, z))
                corr += 1
