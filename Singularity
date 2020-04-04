Bootstrap:docker  
From: tylere/docker-ee-datascience-notebook

%files
gedi_to_gee.py
manifest.template
my-secret-key.json

%runscript
exec python3 gedi_to_gee.py

%post
apt-get -y update

# Add the Cloud SDK distribution URI as a package source
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# Import the Google Cloud Platform public key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
# Update the package list and install the Cloud SDK
apt-get update && apt-get install google-cloud-sdk

# Set project and credentials
gcloud config set project datalab-gee
gcloud auth activate-service-account --key-file=my-secret-key.json