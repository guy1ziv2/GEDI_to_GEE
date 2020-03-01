#!/bin/sh
gdal_rasterize -init -9999 -a cover -ot int16 -tr 25 25 data.shp cover.tif
gdal_rasterize -init 255 -a beam -ot byte -tr 25 25 data.shp beam.tif
gdal_rasterize -init 255 -a channel -ot byte -tr 25 25 data.shp channel.tif
gdal_rasterize -init -9999 -a fhd_normal -ot int16 -tr 25 25 data.shp fhd_normal.tif
gdal_rasterize -init -9999 -a pai -ot int16 -tr 25 25 data.shp pai.tif
gdal_rasterize -init -9999 -a rh100 -ot int16 -tr 25 25 data.shp rh100.tif
gdal_rasterize -init -9999 -a solar_elev -ot int16 -tr 25 25 data.shp solar_elevation.tif
gdal_rasterize -init -9999 -a dem -ot int16 -tr 25 25 data.shp dem.tif
gdal_rasterize -init -9999 -a pgap_theta -ot int16 -tr 25 25 data.shp pgap_theta.tif
gdal_rasterize -init 255 -a quality_fl -ot byte -tr 25 25 data.shp quality_flag.tif