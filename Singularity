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