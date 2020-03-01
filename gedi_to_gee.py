import subprocess
import h5py
import re
import numpy as np
import csv
from shapely.geometry import Point, mapping
from fiona import collection
from pyproj import Proj, transform
import warnings
import os
import tempfile
import sys

warnings.simplefilter(action='ignore', category=FutureWarning)

# get URL from environmental variable
URL = os.environ['URL']
print('Ingesting GEDI URL file {}...'.format(URL))

# some run information
HOME_DIR = '/content'
SERVICE_ACCOUNT='datalab-gee@appspot.gserviceaccount.com'
KEY = HOME_DIR+'/my-secret-key.json'

# get a temp directory, use TEMP_BASE environmental variable (if exists) to set to a different root than usual (e.g. /nobackup/geogz on Leeds HPC)
try:
  temp_dir = tempfile.mkdtemp(dir=os.environ['TEMP_BASE'])
except:
  temp_dir = tempfile.mkdtemp()
os.chdir(temp_dir)

print('Created temp directory {}...'.format(temp_dir))

def toScaledInt(val,multiply):
  val[val != -9999] = np.round(val[val != -9999]*multiply)
  return(val.astype(int))

def extract_shapefile(f,min_lon,max_lon,min_lat,max_lat,crs):
  schema = { 'geometry': 'Point', 'properties': { 'cover': 'int' , 'beam': 'int', 'channel': 'int', 'dem': 'int', 'fhd_normal': 'int', 'pai': 'int', 'rh100': 'int', 'pgap_theta': 'int', 'solar_elev': 'int', 'quality_fl': 'int'} }
  r = re.compile("BEAM.*")
  keys = list(filter(r.match, f.keys()))
  inProj = Proj(init='epsg:4326')
  outProj = Proj(init=crs)
  time_start = time_end = []
  total_points = 0
  with collection("data.shp", "w", "ESRI Shapefile", schema, crs) as output:
    for key in keys:
      # update start/end time. GEDI Epoch starts 2018-01-01 while GEE start 1970-01-01
      time_start.append(min(f[key]['master_int'][:])+1514764800)
      time_end.append(max(f[key]['master_int'][:])+1514764800)

      # calculate location of beam
      lon = (f[key]['geolocation/longitude_bin0'][:]+f[key]['geolocation/longitude_lastbin'][:])/2
      lat = (f[key]['geolocation/latitude_bin0'][:]+f[key]['geolocation/latitude_lastbin'][:])/2
      ind = np.nonzero(np.logical_and(lon>=min_lon,lon<max_lon) & np.logical_and(lat>=min_lat,lat<max_lat))
      num_points = np.count_nonzero(np.logical_and(lon>=min_lon,lon<max_lon) & np.logical_and(lat>=min_lat,lat<max_lat))
      if num_points == 0:
        continue
      total_points += num_points
      x,y = transform(inProj,outProj,lon,lat) # transform into projected coordinates

      # extract those fields we are interested in from the record, rescale etc.
      # Total canopy cover, defined as the percent of the ground covered by the vertical projection of canopy material
      cover = toScaledInt(f[key]['cover'][:],1000)
      # Beam number (0-11) and channel (0-8)
      beam = f[key]['beam'][:]
      channel = f[key]['channel'][:]
      # Foliage height diversity index calculated by vertical foliage profile normalized by total plant area index
      fhd_normal = toScaledInt(f[key]['fhd_normal'][:],1000)
      # Total plant area index
      pai = toScaledInt(f[key]['pai'][:],1000)
      # Height above ground of the received waveform signal start (rh[101] from L2A), often compared to vegetation height
      rh100 = f[key]['rh100'][:]
      # The elevation of the sun position vector from the laser bounce point position in the local ENU frame. The angle is measured from the East-North plane and is positive Up.
      # The negative impact of background solar illumination on GEDI waveform quality is eliminated during night (solar_elevation < 0)
      solar_elevation = toScaledInt(f[key]['geolocation/solar_elevation'][:],10)
      # quality_flag is a summation of several individual quality assessment parameters and other flags and is intended to provide general guidance only. 
      # A quality_flag value of 1 indicates the cover and vertical profile metrics represent the land surface and meet criteria based on waveform shot
      # energy, sensitivity, amplitude, and real-time surface tracking quality, and the quality of extended Gaussian fitting to the lowest mode.
      quality_flag = f[key]['l2b_quality_flag'][:]
      # Estimated Pgap(theta) for the selected L2A algorithm
      pgap_theta = toScaledInt(f[key]['pgap_theta'][:],1000)
      # Digital elevation model height above the WGS84 ellipsoid. Interpolated at latitude_bin0 and longitude_bin0 from the TandemX 90m product.
      dem = f[key]['geolocation/digital_elevation_model'][:]


      for i in np.nditer(ind):
        output.write({
          'properties': {
            'cover': int(cover[i]),
            'beam': int(beam[i]),
            'channel': int(channel[i]),
            'dem': int(dem[i]),
            'fhd_normal': int(fhd_normal[i]),
            'pai': int(pai[i]),
            'rh100': int(rh100[i]),
            'solar_elev': int(solar_elevation[i]),
            'quality_fl': int(quality_flag[i]),
            'pgap_theta': int(pgap_theta[i])
          },
          'geometry': mapping(Point(x[i], y[i]))
        })
  time_start = min(time_start)
  time_end = max(time_end)
  if total_points == 0:
    raise Exception('No points in lon/lat range')
  return(time_start, time_end)

# Authorize gcloud and earthengine using service account. Prepare bucket if not exists
print('authorizing Google services...')
subprocess.run("gcloud config set project datalab-gee", shell=True)
subprocess.run("gcloud auth activate-service-account --key-file={}".format(KEY), shell=True)
subprocess.run(['gsutil','mb','gs://guy1ziv2_gee_transfer']) 

# Download HDF5 from LP DAAC server
print('download HDF5 from {}....'.format(URL))
subprocess.run(['wget',URL]) 

# Set up all 120 UTM zones
utms = [{'UTM': '_UTM{}S'.format(x), 'min_lon': -186+x*6, 'max_lon': -180+x*6, 'min_lat': -90, 'max_lat': 0, 'crs': 'EPSG:{}'.format(x+32700)} for x in range(1,61)]
utms += [{'UTM': '_UTM{}N'.format(x), 'min_lon': -186+x*6, 'max_lon': -180+x*6, 'min_lat': 0, 'max_lat': 90, 'crs': 'EPSG:{}'.format(x+32600)} for x in range(1,61)]

# Read HDF5 file
print('reading HDF5 file...')
file_name = os.path.basename(URL)
f = h5py.File(file_name, 'r')

# Loop over zones
for utm in utms:
  try:
    # extract points for particular UTM zone into data.shp ESRI Shapefile
    time_start, time_end = extract_shapefile(f,utm['min_lon'], utm['max_lon'], utm['min_lat'], utm['max_lat'], utm['crs'])
  except:
    # print('error processing utm {} (probably no points in sector), skipping...'.format(utm))
    continue
  ASSET_ID = os.path.splitext(file_name)[0]+utm['UTM']
  print('processing asset {}...'.format(ASSET_ID))
  # run GDAL to rasterize 25m resolution GeoTIFFs for selected record fields
  print('rasterizing...')
  subprocess.run('{}/rasterize_all.sh'.format(HOME_DIR),shell=True,check=True)
  # copy all files into Cloud Storate
  print('copying to cloud...')
  subprocess.run(['gsutil','-m','-o','GSUtil:parallel_composite_upload_threshold=150M','cp','*.tif','gs://guy1ziv2_gee_transfer/{}/'.format(ASSET_ID)],check=True)
  # prepare manifest
  bucket_str = 'gs://guy1ziv2_gee_transfer/{}/'.format(ASSET_ID).replace('/','\/')
  print('starting ingestion...')
  subprocess.run("sed 's/ASSET_ID/{}/; s/URI_PREFIX/{}/; s/HDF5_FILE/{}/; s/TIME_START/{}/; s/TIME_END/{}/' {}/manifest.template > manifest.json".format(ASSET_ID,bucket_str,file_name,time_start,time_end,HOME_DIR),shell=True)
  # start ingestion, and do not wait for task it to finish
  subprocess.run("earthengine --service_account_file {}/my-secret-key.json  upload image -f --manifest manifest.json".format(HOME_DIR),shell=True,check=True)

# clean up Cloud Storage --- REMOVED, this need to be done only after all tasks are done
# for utm in utms:
#    ASSET_ID = os.path.splitext(file_name)[0]+utm['UTM']
#    subprocess.run(['gsutil','-m','rm','-r','gs://guy1ziv2_gee_transfer/{}'.format(ASSET_ID)])

# clean up temp directory
subprocess.run('rm -R {}'.format(temp_dir),shell=True)