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
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# Import the Google Cloud Platform public key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
# Update the package list and install the Cloud SDK
sudo apt-get update && sudo apt-get install google-cloud-sdk

# install earth engine
conda install -c conda-forge earthengine-api