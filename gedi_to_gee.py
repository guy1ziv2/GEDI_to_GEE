import warnings, subprocess, os, numpy as np, h5py
import re, csv, tempfile
from shapely.geometry import Point, mapping
from fiona import collection
from pyproj import Proj, transform

def toScaledInt(val,multiply):
  val[val != -9999] = np.round(val[val != -9999]*multiply)
  return(val.astype(int))

def extract_shapefile(f,min_lon,min_lat,max_lon,max_lat,crs="EPSG:4326"):
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
  return(time_start, time_end, total_points)

def rasterize(min_lon,min_lat,max_lon,max_lat):
  fields_byte = ['channel','beam','quality_fl']
  for field in fields_byte:
    subprocess.run('gdal_rasterize -init 255 -a {} -ot byte -tr 0.000225 0.000225 -te {} {} {} {} data.shp {}.tif'.format(field,min_lon,min_lat,max_lon,max_lat,field),shell=True, check=True)
  fields_int16 = ['cover','fhd_normal','pai','rh100','solar_elev','dem','pgap_theta']
  for field in fields_int16:
    subprocess.run('gdal_rasterize -init -9999 -a {} -ot int16 -tr 0.000225 0.000225 -te {} {} {} {} data.shp {}.tif'.format(field,min_lon,min_lat,max_lon,max_lat,field),shell=True, check=True)

np.warnings.filterwarnings('ignore')
warnings.simplefilter(action='ignore', category=FutureWarning)

subprocess.run(['gsutil','mb','gs://guy1ziv2_gee_transfer/']) # make sure bucket exists

HOME_DIR = os.environ['HOME_DIR']
KEY = HOME_DIR+'/my-secret-key.json'

ASSET_ID = os.environ['ASSET_ID']
MINX, MINY, MAXX, MAXY = float(os.environ['MINX']), float(os.environ['MINY']), float(os.environ['MAXX']), float(os.environ['MAXY'])

URL = os.environ['URL']

TEMP_BASE = os.environ['TEMP_BASE']
temp_dir = tempfile.mkdtemp(dir=TEMP_BASE)
os.chdir(temp_dir)

print('Created temp directory {}...'.format(temp_dir))

file_name = os.path.basename(URL)
print('reading point data from {}...'.format(file_name))
f = h5py.File(TEMP_BASE+'/'+file_name, 'r')
time_start, time_end, total_points = extract_shapefile(f, MINX, MINY, MAXX, MAXY)
if total_points>0:
  print('raterizing...')
  rasterize(MINX,MINY,MAXX,MAXY)
  IMAGE_ASSET_ID,_ = os.path.splitext(file_name)
  print('copying to GCS...')
  subprocess.run(['gsutil','cp','*.tif','gs://guy1ziv2_gee_transfer/{}/'.format(IMAGE_ASSET_ID)])
  bucket_str = 'gs://guy1ziv2_gee_transfer/{}/'.format(IMAGE_ASSET_ID).replace('/','\/')
  subprocess.run("sed 's/IMAGE_ASSET_ID/{}/; s/ASSET_ID/{}/; s/URI_PREFIX/{}/; s/HDF5_FILE/{}/; s/TIME_START/{}/; s/TIME_END/{}/; s/TOTAL_POINTS/{}/' {}/manifest.template > manifest.json".format(IMAGE_ASSET_ID,ASSET_ID,bucket_str,file_name,time_start,time_end,total_points,HOME_DIR),shell=True)
  print('starting ingestion...')
  subprocess.run("earthengine --service_account_file "+HOME_DIR+"/my-secret-key.json  upload image -f --manifest manifest.json",shell=True)
  subprocess.run('rm -R {}'.format(temp_dir),shell=True)
else:
  print('no points within region of interest! skipping file...')