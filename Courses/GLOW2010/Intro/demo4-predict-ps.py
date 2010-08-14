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

# define antenna list
ANTENNAS = range(1,28);
# derive interferometer list
IFRS   = [ (p,q) for p in ANTENNAS for q in ANTENNAS if p<q ];

# useful constant: 1 deg in radians
DEG = math.pi/180.;

# source parameters
I = 1; Q = .2; U = .2; V = .2;
L = 1*(DEG/60);
M = 1*(DEG/60);
N = math.sqrt(1-L*L-M*M);


def _define_forest (ns):
  # define per-station UVW nodes
  ns.uvw(1) << Meq.Composer(0,0,0);
  for p in ANTENNAS[1:]:
    ns.uvw(p) << Meq.Spigot(station_1_index=0,station_2_index=p-1,input_col='UVW');
  
  # source l,m,n-1 vector
  ns.lmn_minus1 << Meq.Composer(L,M,N-1);
  
  # define K-jones and G-Jones matrices
  for p in ANTENNAS:
    ns.K(p) << Meq.VisPhaseShift(lmn=ns.lmn_minus1,uvw=ns.uvw(p));
    ns.Kt(p) << Meq.ConjTranspose(ns.K(p));
  
  # define source brightness, B
  ns.B << 0.5 * Meq.Matrix22(I+Q,Meq.ToComplex(U,V),Meq.ToComplex(U,-V),I-Q);
  
  # now define predicted visibilities, attach to sinks
  for p,q in IFRS:
    predict = ns.predict(p,q) << \
      Meq.MatrixMultiply(ns.K(p),ns.B,ns.Kt(q));
    ns.sink(p,q) << Meq.Sink(predict,station_1_index=p-1,station_2_index=q-1,output_col='DATA');

  # define a couple of inspector nodes
  ns.inspect_K << Meq.Composer(
    dims=[0],   # compose in tensor mode
    plot_label=["%s"%(p) for p in ANTENNAS],
    *[Meq.Mean(ns.K(p),reduction_axes="freq") for p in ANTENNAS]
  );
  ns.inspect_predict << Meq.Composer(
    dims=[0],   # compose in tensor mode
    plot_label=["%s-%s"%(p,q) for p,q in IFRS],
    *[Meq.Mean(ns.predict(p,q),reduction_axes="freq") for p,q in IFRS]
  );
  ns.inspectors = Meq.ReqMux(ns.inspect_K,ns.inspect_predict);
  
  # create VDM and attach inspectors
  ns.vdm = Meq.VisDataMux(post=ns.inspectors);

def _tdl_job_1_simulate (mqs,parent):
  # create an I/O request
  req = meq.request();
  req.input = record( 
    ms = record(  
      ms_name          = 'VLAAA4h.MS',
      tile_size        = 32
    ),
    python_init = 'Meow.ReadVisHeader'
  );
  req.output = record( 
    ms = record( 
      data_column = 'MODEL_DATA' 
    )
  );
  # execute    
  mqs.execute('vdm',req,wait=False);

def _tdl_job_2_make_image (mqs,parent):
  import os
  try:
    os.unlink('image.fits');
  except:
    pass;
  os.spawnvp(os.P_NOWAIT,'lwimager',['lwimager','data=MODEL_DATA',
    'ms=VLAAA4h.MS','mode='+imaging_mode,
    'weight='+imaging_weight,
    'stokes='+imaging_stokes,'cellsize=1arcsec','npix=512','fits=image.fits']);

# some options for the imager -- these will be automatically placed
# in the "TDL Exec" menu
TDLRuntimeOption('imaging_mode',"Imaging mode",["mfs","channel"]);
TDLRuntimeOption('imaging_weight',"Imaging weights",["natural","uniform","briggs"]);
TDLRuntimeOption('imaging_stokes',"Stokes parameters to image",["I","IQUV"]);


# setup a few bookmarks
Settings.forest_state = record(bookmarks=[
  record(name='K Jones',page=[
    record(udi="/node/K:1",viewer="Result Plotter",pos=(0,0)),
    record(udi="/node/K:2",viewer="Result Plotter",pos=(0,1)),
    record(udi="/node/K:9",viewer="Result Plotter",pos=(1,0)),
    record(udi="/node/K:26",viewer="Result Plotter",pos=(1,1)) \
  ]),
  record(name='Inspectors',page=[
    record(udi="/node/inspect_K",viewer="Collections Plotter",pos=(0,0)),
    record(udi="/node/inspect_predict",viewer="Collections Plotter",pos=(1,0))
  ]),
]);



# this is a useful thing to have at the bottom of the script, it allows us to check the tree for consistency
# simply by running 'python script.py'

if __name__ == '__main__':
  ns = NodeScope();
  _define_forest(ns);
  # resolves nodes
  ns.Resolve();  
  
  print len(ns.AllNodes()),'nodes defined';
