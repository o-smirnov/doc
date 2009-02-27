#
#% $Id$
#
#
# Copyright (C) 2002-2007
# The MeqTree Foundation &
# ASTRON (Netherlands Foundation for Research in Astronomy)
# P.O.Box 2, 7990 AA Dwingeloo, The Netherlands
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>,
# or write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from Timba.TDL import *
import Meow
from Meow import Context
from Meow import Jones,ParmGroup,Bookmarks
from Meow.Parameterization import resolve_parameter

class DiagAmplPhase (object):
  def __init__ (self):
    self.options = [];

  def runtime_options (self):
    return self.options;

  def compute_jones (self,nodes,stations=None,tags=None,label='',**kw):
    stations = stations or Context.array.stations();
    g_ampl_def = Meow.Parm(1);
    g_phase_def = Meow.Parm(0);
    nodes = Jones.gain_ap_matrix(nodes,g_ampl_def,g_phase_def,tags=tags,series=stations);

    # make parmgroups for phases and gains
    self.pg_phase = ParmGroup.ParmGroup(label+"_phase",
                    nodes.search(tags="solvable phase"),
                    table_name="%s_phase.mep"%label,bookmark=4);
    self.pg_ampl  = ParmGroup.ParmGroup(label+"_ampl",
                    nodes.search(tags="solvable ampl"),
                    table_name="%s_ampl.mep"%label,bookmark=4);

    # make solvejobs
    ParmGroup.SolveJob("cal_"+label+"_phase","Calibrate %s phases"%label,self.pg_phase);
    ParmGroup.SolveJob("cal_"+label+"_ampl","Calibrate %s amplitudes"%label,self.pg_ampl);

    return nodes;

class FullRealImag (object):
  def __init__ (self):
    self.options = [];

  def runtime_options (self):
    return self.options;

  def compute_jones (self,jones,stations=None,tags=None,label='',**kw):
    stations = stations or Context.array.stations();
    # create parm definitions for each jones element
    tags = NodeTags(tags) + "solvable";
    diag_real = Meq.Parm(1,tags=tags+"diag real");
    diag_imag = Meq.Parm(0,tags=tags+"diag imag");
    offdiag_real = Meq.Parm(0,tags=tags+"offdiag real");
    offdiag_imag = Meq.Parm(0,tags=tags+"offdiag imag");
    # now loop to create nodes
    for p in stations:
      jones(p) << Meq.Matrix22(
        jones(p,"xx") << Meq.ToComplex(
            jones(p,"rxx") << diag_real,
            jones(p,"ixx") << diag_imag
        ),
        jones(p,"xy") << Meq.ToComplex(
            jones(p,"rxy") << offdiag_real,
            jones(p,"ixy") << offdiag_imag
        ),
        jones(p,"yx") << Meq.ToComplex(
            jones(p,"ryx") << offdiag_real,
            jones(p,"iyx") << offdiag_imag
        ),
        jones(p,"yy") << Meq.ToComplex(
            jones(p,"ryy") << diag_real,
            jones(p,"iyy") << diag_imag
        )
      );
    # make parmgroups for diagonal and off-diagonal terms
    self.pg_diag  = ParmGroup.ParmGroup(label+"_diag",
            [ jones(p,zz) for p in stations for zz in "rxx","ixx","ryy","iyy" ],
            table_name="%s_diag.mep"%label,bookmark=False);
    self.pg_offdiag  = ParmGroup.ParmGroup(label+"_offdiag",
            [ jones(p,zz) for p in stations for zz in "rxy","ixy","ryx","iyx" ],
            table_name="%s_offdiag.mep"%label,bookmark=False);

    # make bookmarks
    Bookmarks.make_node_folder("%s diagonal terms"%label,
      [ jones(p,zz) for p in stations for zz in "xx","yy" ],sorted=True);
    Bookmarks.make_node_folder("%s off-diagonal terms"%label,
      [ jones(p,zz) for p in stations for zz in "xy","yx" ],sorted=True);

    # make solvejobs
    ParmGroup.SolveJob("cal_"+label+"_diag","Calibrate %s diagonal terms"%label,self.pg_diag);
    ParmGroup.SolveJob("cal_"+label+"_offdiag","Calibrate %s off-diagonal terms"%label,self.pg_offdiag);

    return jones;
