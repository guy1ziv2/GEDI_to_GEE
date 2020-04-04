Bootstrap:docker  
From: tylere/docker-ee-datascience-notebook

%files
gedi_to_gee.py
manifest.template
my-secret-key.json

%runscript
exec python3 gedi_to_gee.py

%environment
home=/home/home02/geogz

%post
CLOUD_SDK_VERSION=232.0.0

apt-get -qqy update && apt-get install -qqy \
      curl \
      gcc \
      python-dev \
      python-setuptools \
      apt-transport-https \
      lsb-release \
      openssh-client \
      git \
      gnupg \
  && easy_install -U pip && \
  pip install -U crcmod   && \
  export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" && \
  echo "deb https://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" > /etc/apt/sources.list.d/google-cloud-sdk.list && \
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
  apt-get update && \
  apt-get install -y google-cloud-sdk=${CLOUD_SDK_VERSION}-0 && \
  gcloud --version && \
  gcloud config set project datalab-gee && \
  gcloud auth activate-service-account --key-file=my-secret-key.json