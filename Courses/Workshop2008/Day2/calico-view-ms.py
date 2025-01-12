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
from Timba.Meq import meq
from Timba.array import *
import os
import random

import Meow

from Meow import Bookmarks,Context
import Meow.StdTrees

# MS options first
mssel = Context.mssel = Meow.MSUtils.MSSelector(has_input=True,has_output=False,tile_sizes=[10,100,200],flags=False,hanning=True);
# MS compile-time options
TDLCompileOptions(*mssel.compile_options());
# MS run-time options
TDLRuntimeMenu("MS/data selection options",*mssel.runtime_options());
## also possible:

TDLCompileOption('do_invert_phase',"Invert phases in input data",True,
     doc="""Inverts phases in the input data. Some e.g. WSRT MSs require this."""),

def _define_forest(ns):
  ANTENNAS = mssel.get_antenna_set(range(1,15));
  array = Meow.IfrArray(ns,ANTENNAS,mirror_uvw=False);
  observation = Meow.Observation(ns);
  Meow.Context.set(array,observation);
  stas = array.stations();

  # make spigot nodes
  spigots = spigots0 = array.spigots();
  # invert phases if necessary
  if do_invert_phase:
    for p,q in array.ifrs():
      ns.conj_spigot(p,q) << Meq.Conj(spigots(p,q));
    spigots = ns.conj_spigot;
  
  # ...and an inspector for them
  Meow.StdTrees.vis_inspector(ns.inspector('input'),spigots,
                              bookmark="Inspect input visibilities");
  inspector = ns.inspector('input');
  Bookmarks.make_node_folder("Input visibilities by baseline",
    [ spigots(p,q) for p,q in array.ifrs() ],sorted=True,ncol=2,nrow=2);

  # add sink
  vdm = ns.VisDataMux << Meq.VisDataMux(post=inspector);
  vdm.add_stepchildren(*[spigots0(p,q) for p,q in array.ifrs()]);
  
  # add imaging options
  imsel = mssel.imaging_selector(npix=512,arcmin=72);
  TDLRuntimeMenu("Imaging options",*imsel.option_list());

def _tdl_job_view_MS (mqs,parent,**kw):
  req = mssel.create_io_request();
  mqs.execute('VisDataMux',req,wait=False);


