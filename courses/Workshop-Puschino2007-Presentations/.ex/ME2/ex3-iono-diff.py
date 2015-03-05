# standard preamble
from Timba.TDL import *
from Timba.Meq import meq
import math

import Meow
import Meow.StdTrees

import iono_model
import sky_models

# some GUI options
Meow.Utils.include_ms_options(has_input=False,tile_sizes=[8,16,32]);
# note how we set default image size based on grid size/step
TDLRuntimeMenu("Imaging options",
    *Meow.Utils.imaging_options(npix=512,arcmin=sky_models.imagesize(),channels=[[32,1,1]]));

# define antenna list
ANTENNAS = range(1,27+1);

def _define_forest (ns):
  array = Meow.IfrArray(ns,ANTENNAS);
  observation = Meow.Observation(ns);
  Meow.Context.set(array,observation);
    
  # create source list
  sources = sky_models.make_model(ns,"S0");
    
  # make Zjones for all positions in source list (and all stations)
  # this returns Zj which sould be qualified as Zj(srcname,station)
  # Therefore we can use Zj(srcname) as a per-stations Jones series.
  Zj = iono_model.compute_zeta_jones(ns,sources);
  dZj = ns.dZj;

  # this patch holds all sources corrupted with the Zj for their direction
  allsky = Meow.Patch(ns,'sky',observation.phase_centre);
  for src in sources:
    for p in array.stations():
      dZj(src.name,p) << Zj(src.name,p) / Zj(sources[0].name,p);
    allsky.add(src.corrupt(dZj(src.name)));

  # get predicted visibilities
  predict = allsky.visibilities();
  
  # Make some inspectors.
  # These are the "interesting" stations:
  # 10 is center of array, 9, 18 and 27 are at the end of the arms.
  # Make composers for them
  stas = [ 10,9,18,27 ];
  # make a couple of composers, for visualizations
  inspectors = [
    ns.inspect_tecs << \
      Meq.Composer(
        plot_label = [ "%s:%s"%(p,src.name) for src in sources for p in stas ],
        *[ ns.tec(src.name,p) for src in sources for p in stas ]
      ),
    ns.inspect_Z << \
      Meq.Composer(
        plot_label = [ "%s:%s"%(p,src.name) for src in sources for p in stas ],
        *[ Meq.Mean(Meq.Arg(ns.Z(src.name,p),reduction_axes="freq")) for src in sources for p in stas ]
      )
  ];
  
  # make sinks and vdm. Note that we don't want to make any spigots...
  # The list of inspectors comes in handy here
  Meow.StdTrees.make_sinks(ns,predict,spigots=False,post=inspectors);
  
  # and make some more interesting bookmarks
  Meow.Bookmarks.Page("Inspect TECs").add(ns.inspect_tecs,viewer="Collections Plotter");
  Meow.Bookmarks.Page("Inspect Z").add(ns.inspect_Z,viewer="Collections Plotter");
  
  # 10 is center of array, 9, 18 and 27 are at the end of the arms
  stas = [10,9,18,27 ];
  for p in stas:
    pg = Meow.Bookmarks.Page("TECs, station "+str(p),2,2);
    for src in sources[:4]:
      pg.add(ns.tec(src.name,p));
  for p in stas:
    pg = Meow.Bookmarks.Page("Z Jones, station "+str(p),2,2);
    for src in sources[:4]:
      pg.add(ns.Z(src.name,p));
  


def _tdl_job_1_simulate_MS (mqs,parent):
  req = Meow.Utils.create_io_request();
  # execute    
  mqs.execute('VisDataMux',req,wait=False);
  
  
# this is a useful thing to have at the bottom of the script, it allows us to check the tree for consistency
# simply by running 'python script.tdl'

if __name__ == '__main__':
  ns = NodeScope();
  _define_forest(ns);
  # resolves nodes
  ns.Resolve();  
  
  print len(ns.AllNodes()),'nodes defined';
