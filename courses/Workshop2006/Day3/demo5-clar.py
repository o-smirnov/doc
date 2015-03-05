# standard preamble
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
import math

import Meow
import clar_model

# some GUI options
Meow.Utils.include_ms_options(has_input=False,tile_sizes=[5,10,30]);
Meow.Utils.include_imaging_options();

# GUI option for selecting a source model
TDLCompileOption('source_model',"Source model",[
    clar_model.point_sources_only,
    clar_model.point_and_extended_sources,
    clar_model.radio_galaxy,
    clar_model.faint_source
  ],default=0);

TDLCompileOption('apply_clar_beam',"Apply CLAR beam",False);

# define antenna list
ANTENNAS = range(1,28);

def _define_forest (ns):
  # create an Array object
  array = Meow.IfrArray(ns,ANTENNAS);
  # create an Observation object
  observation = Meow.Observation(ns);
    
  # create a Patch for the entire observed sky
  allsky = Meow.Patch(ns,'all',observation.phase_centre);
  
  # create nominal CLAR source model by calling the specified
  # model function
  clar_model.init_directions(ns);
  source_list = source_model(ns);
  
  if apply_clar_beam:
    # create CLAR EJones terms
    Ej = clar_model.EJones_pretab(ns,array,source_list);

    # corrupt sources with CLAR beam and add to allsky patch
    for src in source_list:
      corrupt_src = Meow.CorruptComponent(ns,src,label='E',station_jones=Ej(src.direction.name));
      allsky.add(corrupt_src);
  else:
    allsky.add(*source_list);
  
  # create set of nodes to compute visibilities...
  predict = allsky.visibilities(array,observation);

  # ...and attach them to sinks
  for p,q in array.ifrs():
    ns.sink(p,q) << Meq.Sink(predict(p,q),station_1_index=p-1,station_2_index=q-1,output_col='DATA');

  # define VisDataMux
  ns.vdm << Meq.VisDataMux(*[ns.sink(p,q) for p,q in array.ifrs()]);
  

def _tdl_job_1_simulate_MS (mqs,parent):
  req = Meow.Utils.create_io_request();
  # execute    
  mqs.execute('vdm',req,wait=False);
  
  
def _tdl_job_2_make_image (mqs,parent):
  Meow.Utils.make_dirty_image(npix=256,cellsize='1arcsec',channels=[32,1,1]);



# setup a few bookmarks
Settings.forest_state = record(bookmarks=[
  Meow.Bookmarks.PlotPage("K Jones",["K:S0:1","K:S0:9"],["K:S1:2","K:S1:9"]),
  Meow.Bookmarks.PlotPage("E Jones",["E:S1:1","E:S1:9"],["E:S8:1","E:S8:9"]),
]);


# this is a useful thing to have at the bottom of the script, it allows us to check the tree for consistency
# simply by running 'python script.tdl'

if __name__ == '__main__':
  ns = NodeScope();
  _define_forest(ns);
  # resolves nodes
  ns.Resolve();  
  
  print len(ns.AllNodes()),'nodes defined';