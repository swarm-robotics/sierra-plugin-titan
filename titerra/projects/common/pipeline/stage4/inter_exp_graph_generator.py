# Copyright 2018 John Harwell, All rights reserved.
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
#

"""
Classes for generating graphs across experiments in a batch.
"""

# Core packages
import copy
import typing as tp

# 3rd party packages
import sierra.core.pipeline.stage4 as stage4
from sierra.core import types

# Project packages
import titerra.projects.common.perf_measures.self_organization as pmso
import titerra.projects.common.perf_measures.raw as pmraw
import titerra.projects.common.perf_measures.robustness as pmb
import titerra.projects.common.perf_measures.flexibility as pmf
import titerra.projects.common.perf_measures.scalability as pms
from titerra.variables import batch_criteria as bc


class InterExpGraphGenerator(stage4.inter_exp_graph_generator.InterExpGraphGenerator):
    """Extends
    :class:`~sierra.core.pipeline.stage4.inter_exp_graph_generator.InterExpGraphGenerator`
    with additional graphs for the TITAN project.

    """

    def __call__(self, criteria: bc.IConcreteBatchCriteria) -> None:
        """
        In addition to the graphs generated by
        :class:`~sierra.core.pipeline.stage4.inter_exp_graph_generator.InterExpGraphGenerator`, run
        the following to generate graphs across experiments in the batch:

        #. :class:`~sierra.core.pipeline.stage4.inter_exp_graph_generator.UnivarPerfMeasuresGenerator`
           to performance measures (univariate batch criteria only).

        #. :class:`~sierra.core.pipeline.stage4.inter_exp_graph_generator.BivarPerfMeasuresGenerator`
           to generate performance measures (bivariate batch criteria only).
        """
        super().__call__(criteria)
        if criteria.is_univar():
            UnivarPerfMeasuresGenerator(
                self.main_config, self.cmdopts)(criteria)
        else:
            BivarPerfMeasuresGenerator(self.main_config, self.cmdopts)(criteria)


class UnivarPerfMeasuresGenerator:
    """
    Generates performance measures from collated .csv data across a batch of experiments. Which
    measures are generated is controlled by the batch criteria used for the experiment. Univariate
    batch criteria only.

    Attributes:
        cmdopts: Dictionary of parsed cmdline options.
        main_config: Dictionary of parsed main YAML config.
    """

    def __init__(self,
                 main_config: types.YAMLDict,
                 cmdopts: types.Cmdopts) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us
        self.cmdopts = copy.deepcopy(cmdopts)
        self.main_config = main_config

    def __call__(self, criteria: bc.IConcreteBatchCriteria) -> None:
        perf_csv = self.main_config['sierra']['perf']['intra_perf_csv']
        perf_col = self.main_config['sierra']['perf']['intra_perf_col']
        interference_csv = self.main_config['sierra']['perf']['intra_interference_csv']
        interference_col = self.main_config['sierra']['perf']['intra_interference_col']
        raw_title = self.main_config['sierra']['perf']['raw_perf_title']
        raw_ylabel = self.main_config['sierra']['perf']['raw_perf_ylabel']

        assert isinstance(criteria, bc.IPMQueryableBatchCriteria), \
            "Batch criteria must implement IPMQueryableBatchCriteria"

        if criteria.pm_query('raw'):
            pmraw.SteadyStateRawUnivar(self.cmdopts, perf_csv, perf_col).from_batch(criteria,
                                                                                    title=raw_title,
                                                                                    ylabel=raw_ylabel)
        if criteria.pm_query('scalability'):
            pms.ScalabilityUnivarGenerator()(perf_csv, perf_col, self.cmdopts, criteria)

        if criteria.pm_query('self-org'):
            pmso.SelfOrgUnivarGenerator()(self.cmdopts,
                                          perf_csv,
                                          perf_col,
                                          interference_csv,
                                          interference_col,
                                          criteria)

        if criteria.pm_query('flexibility'):
            pmf.FlexibilityUnivarGenerator()(self.cmdopts,
                                             self.main_config,
                                             criteria)

        if criteria.pm_query('robustness-pd') or criteria.pm_query('robustness-saa'):
            pmb.RobustnessUnivarGenerator()(self.cmdopts,
                                            self.main_config,
                                            criteria)


class BivarPerfMeasuresGenerator:
    """
    Generates performance measures from collated .csv data across a batch of experiments. Which
    measures are generated is controlled by the batch criteria used for the experiment. Bivariate
    batch criteria only.

    Attributes:
        cmdopts: Dictionary of parsed cmdline options.
        main_config: Dictionary of parsed main YAML config.
    """

    def __init__(self,
                 main_config: types.YAMLDict,
                 cmdopts: types.Cmdopts) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us
        self.cmdopts = copy.deepcopy(cmdopts)
        self.main_config = main_config

    def __call__(self, criteria: bc.IConcreteBatchCriteria) -> None:
        perf_csv = self.main_config['sierra']['perf']['intra_perf_csv']
        perf_col = self.main_config['sierra']['perf']['intra_perf_col']
        interference_csv = self.main_config['sierra']['perf']['intra_interference_csv']
        interference_col = self.main_config['sierra']['perf']['intra_interference_col']
        raw_title = self.main_config['sierra']['perf']['raw_perf_title']

        assert isinstance(criteria, bc.IPMQueryableBatchCriteria), \
            "Batch criteria must implement IPMQueryableBatchCriteria"

        if criteria.pm_query('raw'):
            pmraw.SteadyStateRawBivar(self.cmdopts,
                                      perf_csv=perf_csv,
                                      perf_col=perf_col).from_batch(criteria,
                                                                    title=raw_title)

        if criteria.pm_query('scalability'):
            pms.ScalabilityBivarGenerator()(perf_csv, perf_col, self.cmdopts, criteria)

        if criteria.pm_query('self-org'):
            pmso.SelfOrgBivarGenerator()(self.cmdopts,
                                         perf_csv,
                                         perf_col,
                                         interference_csv,
                                         interference_col,
                                         criteria)

        if criteria.pm_query('flexibility'):
            pmf.FlexibilityBivarGenerator()(self.cmdopts,
                                            self.main_config,
                                            criteria)

        if criteria.pm_query('robustness-pd') or criteria.pm_query('robustness-saa'):
            pmb.RobustnessBivarGenerator()(self.cmdopts,
                                           self.main_config,
                                           criteria)


__api__ = ['InterExpGraphGenerator',
           'BivarPerfMeasuresGenerator',
           'UnivarPerfMeasuresGenerator']
