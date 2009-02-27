# standard preamble
from Timba.TDL import *
from Timba.Meq import meq
import math

import Meow
import Meow.StdTrees

# MS options first
mssel = Meow.MSUtils.MSSelector(has_input=False,tile_sizes=[8,16,32],flags=True);
# MS compile-time options
TDLCompileOptions(*mssel.compile_options());
# MS run-time options
TDLRuntimeOptions(*mssel.runtime_options());
## also possible:
# TDLRuntimeMenu("MS selection options",open=True,*mssel.runtime_options());

# UVW
TDLCompileOptions(*Meow.IfrArray.compile_options());

# simulation mode menu
SIM_ONLY = "sim only";
ADD_MS   = "add to MS";
SUB_MS   = "subtract from MS";
simmode_opt = TDLCompileOption("sim_mode","Simulation mode",[SIM_ONLY,ADD_MS,SUB_MS]);
simmode_opt.when_changed(lambda mode:mssel.enable_input_column(mode!=SIM_ONLY));

# now load optional modules for the ME maker
from Meow import MeqMaker
meqmaker = MeqMaker.MeqMaker();

# specify available sky models
# these will show up in the menu automatically
import gridded_sky
import transient_sky
import Meow.LSM
lsm = Meow.LSM.MeowLSM(include_options=False);

meqmaker.add_sky_models([gridded_sky,transient_sky,lsm]);

# now add optional Jones terms
# these will show up in the menu automatically

# Ncorr - correct for N
import oms_n_inverse
meqmaker.add_sky_jones('Ncorr','n-term correction',oms_n_inverse);

# Z - ionosphere
import oms_ionosphere
meqmaker.add_sky_jones('Z','ionosphere',oms_ionosphere);

# E - beam
import wsrt_beams
import oms_pointing_errors
meqmaker.add_sky_jones('E','beam',[wsrt_beams],
                                  pointing=oms_pointing_errors);

# P - parallactic angle
import jones_par_angle
meqmaker.add_uv_jones('P','parallactic angle',jones_par_angle);
  
# G - gains
import oms_gain_models
meqmaker.add_uv_jones('G','gains/phases',oms_gain_models);

# very important -- insert meqmaker's options properly
TDLCompileOptions(*meqmaker.compile_options());

# resampling option
TDLCompileMenu("Enable resampling",
  TDLOption('resample_time',"Resampling factor in time",[3,5,10],more=int),
  TDLOption('resample_freq',"Resampling factor in freq",[3,5,10],more=int),
  toggle='do_resample');
   
# noise option
TDLCompileOption("noise_stddev","Add noise, Jy",[None,1e-6,1e-3],more=float);


def _define_forest (ns):
  ANTENNAS = mssel.get_antenna_set(range(1,28));
  # sneaky, sneaky: disable MS-UVWs when resampling is in use
  if do_resample:
    ms_uvw = False;
  else:
    ms_uvw = None;
  array = Meow.IfrArray(ns,ANTENNAS,ms_uvw=ms_uvw);
  observation = Meow.Observation(ns);
  Meow.Context.set(array,observation);
  stas = array.stations();

  # setup imaging options (now that we have an imaging size set up)
  imsel = mssel.imaging_selector(npix=512,arcmin=meqmaker.estimate_image_size());
  TDLRuntimeMenu("Imaging options",*imsel.option_list());
  
  # get a predict tree from the MeqMaker
  output = meqmaker.make_predict_tree(ns);
  
  # add resampling if needed
  if do_resample:
    for p,q in array.ifrs():
      modres = ns.modres(p,q) << Meq.ModRes(output(p,q),
                                            upsample=[resample_time,resample_freq]);
      ns.resampled(p,q) << Meq.Resampler(modres,mode=2);
    output = ns.resampled;
  
  # throw in a bit of noise
  if noise_stddev:
    # make two complex noise terms per station (x/y)
    noisedef = Meq.GaussNoise(stddev=noise_stddev)
    noise_x = ns.sta_noise('x');
    noise_y = ns.sta_noise('y');
    for p in array.stations():
      noise_x(p) << Meq.ToComplex(noisedef,noisedef);
      noise_y(p) << Meq.ToComplex(noisedef,noisedef);
    # now combine them into per-baseline noise matrices
    for p,q in array.ifrs():
      noise = ns.noise(p,q) << Meq.Matrix22(
        noise_x(p)+noise_x(q),noise_x(p)+noise_y(q),
        noise_y(p)+noise_x(q),noise_y(p)+noise_y(q)
      );
      ns.noisy_predict(p,q) << output(p,q) + noise;
    output = ns.noisy_predict;
    
  # in add or subtract sim mode, make some spigots and add/subtract visibilities
  if sim_mode == ADD_MS:
    spigots = array.spigots();
    for p,q in array.ifrs():
      ns.sum(p,q) << output(p,q) + spigots(p,q);
    output = ns.sum;
  elif sim_mode == SUB_MS:
    spigots = array.spigots();
    for p,q in array.ifrs():
      ns.diff(p,q) << output(p,q) - spigots(p,q);
    output = ns.diff;
  else:
    spigots = False;
  
  # make sinks and vdm.
  # The list of inspectors comes in handy here
  Meow.StdTrees.make_sinks(ns,output,spigots=spigots,post=meqmaker.get_inspectors());


def _tdl_job_1_simulate_MS (mqs,parent,wait=False):
  mqs.execute('VisDataMux',mssel.create_io_request(),wait=wait);
  
  
# this is a useful thing to have at the bottom of the script, it allows us to check the tree for consistency
# simply by running 'python script.tdl'

if __name__ == '__main__':
  ns = NodeScope();
  _define_forest(ns);
  # resolves nodes
  ns.Resolve();  
  
  print len(ns.AllNodes()),'nodes defined';
