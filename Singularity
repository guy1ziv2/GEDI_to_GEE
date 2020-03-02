Bootstrap:docker  
From: osgeo/gdal

%files
rasterize_all.sh
manifest.template
gedi_to_gee.py

%runscript
exec python3 gedi_to_gee.py

%post
apt-get update
apt-get upgrade -y

# Install python 3
apt-get install -y python3-pip 

echo 'alias python=python3' >> ~/.bashrc

# install pip
wget https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
export PATH=$HOME/.local/bin:$PATH

# install Python packages
pip install fiona
pip install pyproj
pip install shapely

# Add the Cloud SDK distribution URI as a package source
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# Import the Google Cloud Platform public key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
# Update the package list and install the Cloud SDK
apt-get update && apt-get install google-cloud-sdk

# install earth engine
pip install earthengine-api