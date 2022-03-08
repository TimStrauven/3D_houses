import warnings
warnings.simplefilter("ignore")

import json
import requests
import os
import geopandas as gpd
from osgeo import gdal
import pandas as pd
import rasterio
from rasterio import merge as riomerge
from pyproj import Transformer
import urllib
from shapely.geometry import Point


downloadfolder = f"{os.getcwd()}/"
outputfolder = os.path.join(downloadfolder, "output/")
downloadfolder_DSM = os.path.join(downloadfolder, "DSM_tif/")
downloadfolder_DTM = os.path.join(downloadfolder, "DTM_tif/")
be_shp_path = os.path.join(downloadfolder, "Kaartbladversnijdingen_NGI_numerieke_reeks_Shapefile/Shapefile/Kbl.shp")
BpnCapa_path = os.path.join(downloadfolder, "CadGIS_fiscaal_20210101_GewVLA_Shapefile/Shapefile/BpnCapa.shp")
BpnCapa_1_path = os.path.join(downloadfolder, "CadGIS_fiscaal_20210101_GewVLA_Shapefile/Shapefile/BpnCapa_1.shp")
BpnRebu_path = os.path.join(downloadfolder, "CadGIS_fiscaal_20210101_GewVLA_Shapefile/Shapefile/BpnRebu.shp")
BpnRebu_1_path = os.path.join(downloadfolder, "CadGIS_fiscaal_20210101_GewVLA_Shapefile/Shapefile/BpnRebu_1.shp")
BpnCabu_path = os.path.join(downloadfolder, "CadGIS_fiscaal_20210101_GewVLA_Shapefile/Shapefile/BpnCabu.shp")

basefiles_missing = False
if os.path.exists(be_shp_path) == False:
    basefiles_missing = True
if os.path.exists(BpnCapa_path) == False:
    basefiles_missing = True
if os.path.exists(BpnCapa_1_path) == False:
    basefiles_missing = True
if os.path.exists(BpnRebu_path) == False:
    basefiles_missing = True
if os.path.exists(BpnRebu_1_path) == False:
    basefiles_missing = True
if os.path.exists(BpnCabu_path) == False:
    basefiles_missing = True
if basefiles_missing:
    print("Cannot run the program, download all needed files first.")
    print("Readme has info on what files to download from government.")
    quit()

cant_continue = True
while cant_continue:
    my_adress = input("Enter an adress: ")
    try:
        expandbox = int(input("Enter number of meters to be added (100m-1000m, default=400m): "))
    except ValueError:
        expandbox = 400
    if expandbox > 1000:
        expandbox = 1000
    if expandbox < 100:
        expandbox = 100
    url = "https://loc.geopunt.be/v4/Location?q=" + my_adress
    r = requests.get(url)
    try:
        r_json = json.loads(r.text)["LocationResult"][0]
    except IndexError:
        print("that adress is not recognized...")
        continue
    bbox = r_json.get('BoundingBox', {})
    lowerleft_x = bbox["LowerLeft"]["X_Lambert72"]
    lowerleft_y = bbox["LowerLeft"]["Y_Lambert72"]
    upperright_x = bbox["UpperRight"]["X_Lambert72"]
    upperright_y = bbox["UpperRight"]["Y_Lambert72"]
    print(f"Total size is {upperright_x - lowerleft_x + 2*expandbox}m, by {upperright_y - lowerleft_y + 2*expandbox}m")
    if ((upperright_x - lowerleft_x + expandbox) < 1501) or ((upperright_y - lowerleft_y + expandbox) < 1501):
        cant_continue = False
    else:
        print("That area is too large... Try again")

x_offset = 0
y_offset = 0

if len(json.loads(r.text)["LocationResult"]) == 1:
    r_json = json.loads(r.text)["LocationResult"][0]
    bbox = r_json.get('BoundingBox', {})
    lowerleft_x = bbox["LowerLeft"]["X_Lambert72"] + x_offset
    lowerleft_y = bbox["LowerLeft"]["Y_Lambert72"] + y_offset
    upperright_x = bbox["UpperRight"]["X_Lambert72"] + x_offset
    upperright_y = bbox["UpperRight"]["Y_Lambert72"] + y_offset
else:
    print("Addres not found, please check for typos etc...")

# Check in what NGI map the adress coordinates are located
be_shp = gpd.read_file(be_shp_path)

lowerleft = Point(lowerleft_x - expandbox, lowerleft_y - expandbox)
upperleft = Point(lowerleft_x - expandbox, upperright_y + expandbox)
lowerright = Point(upperright_x + expandbox, lowerleft_y - expandbox)
upperright = Point(upperright_x + expandbox, upperright_y + expandbox)
lowerleft_lst = be_shp.loc[be_shp["geometry"].apply(lambda x: lowerleft.within(x)) == True]["CODE"].tolist()
upperleft_lst = be_shp.loc[be_shp["geometry"].apply(lambda x: upperleft.within(x)) == True]["CODE"].tolist()
lowerright_lst = be_shp.loc[be_shp["geometry"].apply(lambda x: lowerright.within(x)) == True]["CODE"].tolist()
upperright_lst = be_shp.loc[be_shp["geometry"].apply(lambda x: upperright.within(x)) == True]["CODE"].tolist()
if len(lowerleft_lst) == 1 and len(upperleft_lst) == 1 and len(lowerright_lst) == 1 and len(upperright_lst) == 1:
    print("Geometry points all within unique NGI maps --> OK")
else:
    print("Geometry points NGI map error, cannot process this location (flemish gov NGI map seems incorrect)")
    print("Trying to continue anyway...")

mapnumbers = list(dict.fromkeys((upperleft_lst[0], upperright_lst[0], lowerleft_lst[0], lowerright_lst[0])))
if len(mapnumbers) == 1:
    print(f"All bounding box points are in the same Ngi map with Nr: {lowerleft_lst[0]}")
else:
    print("The property is ovelapping multiple Ngi maps:")
    print("maps top:    ", upperleft_lst[0], upperright_lst[0])
    print("maps bottom: ", lowerleft_lst[0], lowerright_lst[0])

print("creating Tiff coutouts...")

def get_dsmdtm_path(dsmdtm, thismap) -> str:
    dsmdtm = dsmdtm.upper()
    myfile = f"DHMVII{dsmdtm}RAS1m_k{thismap.zfill(2)}/GeoTIFF/DHMVII{dsmdtm}RAS1m_k{thismap.zfill(2)}.tif"
    myfilefullpath = f"{downloadfolder}{dsmdtm}_tif/{myfile}"
    if os.path.exists(myfilefullpath) == False:
        print("Cannot find the tif file you requested, missing file is:")
        print(myfilefullpath)
        quit()
    else:
        return myfile


def create_tif_cutouts(thismap):
    geotif_DSM_file = os.path.join(downloadfolder_DSM, get_dsmdtm_path("DSM", thismap))
    resized_DSM_geotif = os.path.join(outputfolder, f"output_DSM{thismap}.tif")
    geotif_DTM_file = os.path.join(downloadfolder_DTM, get_dsmdtm_path("DTM", thismap))
    resized_DTM_geotif = os.path.join(outputfolder, f"output_DTM{thismap}.tif")
    gdal.Translate(resized_DSM_geotif, geotif_DSM_file, projWin=[lowerleft_x - expandbox, upperright_y + expandbox, upperright_x + expandbox, lowerleft_y - expandbox])
    crop_white_border(resized_DSM_geotif)
    gdal.Translate(resized_DTM_geotif, geotif_DTM_file, projWin=[lowerleft_x - expandbox, upperright_y + expandbox, upperright_x + expandbox, lowerleft_y - expandbox])
    crop_white_border(resized_DTM_geotif)

# crop the image borders if they have white values
def crop_white_border(my_geotif_file):
    with rasterio.open(my_geotif_file) as src:
        window = rasterio.windows.get_data_window(src.read(1, masked=True))
        # window = Window(col_off=13, row_off=3, width=757, height=711)
        kwargs = src.meta.copy()
        kwargs.update({
            'height': window.height,
            'width': window.width,
            'transform': rasterio.windows.transform(window, src.transform)})
        with rasterio.open(my_geotif_file, 'w', **kwargs) as dst:
            dst.write(src.read(window=window))

def createfinal(dsmdtm, mylist):
    with rasterio.open(mylist[0]) as src:
        meta = src.meta.copy()
    # The merge function returns a single array and the affine transform info
    arr, out_trans = riomerge.merge(mylist)
    meta.update({
        "driver": "GTiff",
        "height": arr.shape[1],
        "width": arr.shape[2],
        "transform": out_trans
    })
    # Write the mosaic raster to disk
    with rasterio.open(os.path.join(outputfolder, f"output_{dsmdtm}.tif"), "w", **meta) as dest:
        dest.write(arr)

dsm_list = []
dtm_list = []
for thismap in mapnumbers:
    create_tif_cutouts(thismap)
    dsm_list.append(os.path.join(outputfolder, f"output_DSM{thismap}.tif"))
    dtm_list.append(os.path.join(outputfolder, f"output_DTM{thismap}.tif"))

createfinal("DSM", dsm_list)
createfinal("DTM", dtm_list)

print("creating xyz data of the surroundings for blender...")

# create xyz dataframes
resized_DSM_geotif = os.path.join(outputfolder, "output_DSM.tif")
xyz_DSM_file = os.path.join(outputfolder, "output_DSM.xyz")
resized_DTM_geotif = os.path.join(outputfolder, "output_DTM.tif")
xyz_DTM_file = os.path.join(outputfolder, "output_DTM.xyz")

geo_DSM_resized = gdal.Open(resized_DSM_geotif)
gdal.Translate(xyz_DSM_file, geo_DSM_resized)
df_dsm = pd.read_csv(xyz_DSM_file, sep=" ", header=None)
df_dsm.columns = ["x", "y", "z"]

geo_DTM_resized = gdal.Open(resized_DTM_geotif)
gdal.Translate(xyz_DTM_file, geo_DTM_resized)
df_dtm = pd.read_csv(xyz_DTM_file, sep=" ", header=None)
df_dtm.columns = ["x", "y", "z"]

df_final = pd.concat([df_dsm, df_dtm]).groupby(["x", "y"], as_index=False)["z"].sum()
final_csv = os.path.join(outputfolder, "final.csv")

df_blender = df_final.copy()
df_blender.columns = ["x", "y", "z"]
df_blender.reset_index(drop=True, inplace=True)
df_blender["z"] = df_blender['z'].where(df_blender['z'] > -1000, other=0)
x_med_blender = df_blender["x"].median()
y_med_blender = df_blender["y"].median()
z_min_blender = df_blender["z"].min()
df_blender["x"] = df_blender["x"] - x_med_blender
df_blender["y"] = df_blender["y"] - y_med_blender
df_blender["z"] = df_blender["z"] - z_min_blender
df_blender.to_csv(final_csv, sep=',', index=False)

print("Fetching sattelite images from MapBox...")

def sat_img_from_mapbox(mapbox_apikey):
    transformer = Transformer.from_crs(crs_from=31370, crs_to=4326)
    mypoint = (lowerleft_x - expandbox, lowerleft_y - expandbox)
    long1, latt1 = transformer.transform(mypoint[0], mypoint[1])
    mypoint2 = (lowerleft_x + expandbox, lowerleft_y + expandbox)
    long2, latt2 = transformer.transform(mypoint2[0], mypoint2[1])
    baselink = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/[{latt1},{long1},{latt2},{long2}]/1280x1280?access_token={mapbox_apikey}"
    urllib.request.urlretrieve(baselink, f'{outputfolder}texture.jpeg')

def sat_img_plane_from_mapbox(mapbox_apikey, box):
    transformer = Transformer.from_crs(crs_from=31370, crs_to=4326)
    mypoint = (lowerleft_x - box, lowerleft_y - box)
    long1, latt1 = transformer.transform(mypoint[0], mypoint[1])
    mypoint2 = (lowerleft_x + box, lowerleft_y + box)
    long2, latt2 = transformer.transform(mypoint2[0], mypoint2[1])
    baselink = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/[{latt1},{long1},{latt2},{long2}]/1280x1280?access_token={mapbox_apikey}"
    urllib.request.urlretrieve(baselink, f'{outputfolder}texture_plane_{box}.jpeg')

mapbox_apikey_path = os.path.join(downloadfolder, "mapbox_api_key")
if os.path.exists(mapbox_apikey_path):
    with open(mapbox_apikey_path) as f:
        mapbox_apikey = f.readline()
    sat_img_from_mapbox(mapbox_apikey)
    sat_img_plane_from_mapbox(mapbox_apikey, 10000)
    sat_img_plane_from_mapbox(mapbox_apikey, 2000)
    sat_img_plane_from_mapbox(mapbox_apikey, 150000)
else:
    mapbox_apikey = input("paste your mapbox api key to continue")
    with open(mapbox_apikey_path, 'w') as f:
        f.write(mapbox_apikey)
    sat_img_from_mapbox(mapbox_apikey)
    sat_img_plane_from_mapbox(mapbox_apikey, 10000)
    sat_img_plane_from_mapbox(mapbox_apikey, 2000)
    sat_img_plane_from_mapbox(mapbox_apikey, 150000)

print("Cycling trough shapefiles to get house area data...")

plot_df = gpd.read_file(BpnCapa_path, bbox=(lowerleft_x, upperright_y, upperright_x, lowerleft_y))
if plot_df["geometry"].count() == 0:
    plot_df = gpd.read_file(BpnCapa_1_path, bbox=(lowerleft_x, upperright_y, upperright_x, lowerleft_y))

if plot_df["geometry"].count() == 1:
    plotarea = plot_df.iloc[0]["OPPERVL"]
    building_df = gpd.read_file(BpnRebu_path, mask=plot_df["geometry"][0])
    if building_df["geometry"].count() == 0:
        building_df = gpd.read_file(BpnRebu_1_path, mask=plot_df["geometry"][0])
    if building_df["geometry"].count() == 0:
        building_df = gpd.read_file(BpnCabu_path, mask=plot_df["geometry"][0])

    building_df = gpd.overlay(plot_df, building_df, how='intersection', keep_geom_type=None, make_valid=True)
else:
    building_df = None

buildingarea = 0
if building_df is not None:
    for i in range(0, building_df["geometry"].count()):
        buildingarea += building_df.iloc[i]["OPPERVL_2"]

    print("Creating xyz data for house and plot in Blender...")
    offsetbox = 2
    plot_minx = plot_df["geometry"][0].bounds[0] - offsetbox
    plot_miny = plot_df["geometry"][0].bounds[1] - offsetbox
    plot_maxx = plot_df["geometry"][0].bounds[2] + offsetbox
    plot_maxy = plot_df["geometry"][0].bounds[3] + offsetbox

    dsm_plot = os.path.join(outputfolder, "output_plot_DSM.tif")
    dtm_plot = os.path.join(outputfolder, "output_plot_DTM.tif")

    dsm_plot_df = gdal.Translate(dsm_plot, resized_DSM_geotif, projWin=[plot_minx, plot_maxy, plot_maxx, plot_miny])
    gdal.Translate(dsm_plot, resized_DSM_geotif, projWin=[plot_minx, plot_maxy, plot_maxx, plot_miny])

    dtm_plot_df = gdal.Translate(dtm_plot, resized_DTM_geotif, projWin=[plot_minx, plot_maxy, plot_maxx, plot_miny])
    gdal.Translate(dtm_plot, resized_DTM_geotif, projWin=[plot_minx, plot_maxy, plot_maxx, plot_miny])

    xyz_DSM_plot_file = os.path.join(outputfolder, "output_plot_DSM.xyz")
    xyz_DTM_plot_file = os.path.join(outputfolder, "output_plot_DTM.xyz")

    dsm_plot_tif = gdal.Open(dsm_plot)
    gdal.Translate(xyz_DSM_plot_file, dsm_plot_tif)
    df_plot_dsm = pd.read_csv(xyz_DSM_plot_file, sep=" ", header=None)
    df_plot_dsm.columns = ["x", "y", "z"]

    dtm_plot_tif = gdal.Open(dtm_plot)
    gdal.Translate(xyz_DTM_plot_file, dtm_plot_tif)
    df_plot_dtm = pd.read_csv(xyz_DTM_plot_file, sep=" ", header=None)
    df_plot_dtm.columns = ["x", "y", "z"]

    df_plot_final = pd.concat([df_plot_dsm, df_plot_dtm]).groupby(["x", "y"], as_index=False)["z"].sum()
    final_plot_csv = os.path.join(outputfolder, "final_plot.csv")

    df_plot_blender = df_plot_final.copy()
    df_plot_blender.columns = ["x", "y", "z"]
    df_plot_blender.reset_index(drop=True, inplace=True)
    df_plot_blender["polygon1"] = df_plot_blender.apply(lambda row: plot_df["geometry"][0].contains(Point(row["x"], row["y"])), axis=1)
    elevate = df_plot_blender["z"].max() - df_plot_blender["z"].min()
    df_plot_blender["x"] = df_plot_blender["x"] - x_med_blender
    df_plot_blender["y"] = df_plot_blender["y"] - y_med_blender
    df_plot_blender["z"] = df_plot_blender["z"] - z_min_blender + elevate
    df_plot_blender["z"] = df_plot_blender['z'].where(df_plot_blender['polygon1'] == True, other=0)

    df_plot_blender.to_csv(final_plot_csv, sep=',', index=False)

    # code for building mesh
    final_building_csv = os.path.join(outputfolder, "final_building.csv")

    df_plotonly_blender = df_plot_dtm.copy()
    df_plotonly_blender.columns = ["x", "y", "z"]
    df_plotonly_blender.reset_index(drop=True, inplace=True)
    df_plotonly_blender["polygon_plot"] = df_plotonly_blender.apply(lambda row: plot_df["geometry"][0].contains(Point(row["x"], row["y"])), axis=1)

    df_houseonly_blender = df_plot_dsm.copy()
    df_houseonly_blender.columns = ["x", "y", "z"]
    df_houseonly_blender.reset_index(drop=True, inplace=True)

    def is_point_in_poly(row) -> bool:
        isinside = False
        for poly in building_df["geometry"]:
            if poly.contains(Point(row["x"], row["y"])):
                isinside = True
        return isinside

    df_houseonly_blender["polygon_building"] = df_houseonly_blender.apply(lambda row: (is_point_in_poly(row)), axis=1)
    df_houseonly_blender["z"] = df_houseonly_blender['z'].where(df_houseonly_blender['polygon_building'] == True, other=df_plotonly_blender["z"])

    df_house_blender = df_houseonly_blender.copy()
    df_house_blender['polygon_plot'] = df_plotonly_blender["polygon_plot"]
    df_house_blender["x"] = df_house_blender["x"] - x_med_blender
    df_house_blender["y"] = df_house_blender["y"] - y_med_blender
    z_house_min = df_house_blender["z"].min()
    df_house_blender["z"] = df_house_blender["z"] + elevate
    df_house_blender["z"] = df_house_blender['z'].where(df_house_blender['polygon_plot'] == True, other=0)

    df_house_blender.to_csv(final_building_csv, sep=',', index=False)
    print("")
    print(f"The total livable area is: {buildingarea}m²")
print(f"The total size of the plot is: {plotarea}m²")
print("")

blender_startfile = os.path.join(downloadfolder, "blender.py")

open_blender = input("Press Enter to open in blender: ")
if open_blender == "":
    os.system(f"blender --python {blender_startfile}")
