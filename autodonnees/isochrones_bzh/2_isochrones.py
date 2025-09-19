import json
import requests
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon

def filter_voro_points(i:int,
                       polygdf:gpd.geodataframe.GeoDataFrame,
                       ptgdf:gpd.geodataframe.GeoDataFrame,
                       comcol:str) -> list:
    """
        Cette fonction renvoie une liste de deux GeoDataFrames :
            - une DF d'une ligne de polygones Voronoï
            - le centre correspondant
    """
    try:
        row_voro = polygdf.iloc[[i]].reset_index(drop=True)
        row_point = ptgdf[ptgdf[comcol].astype(str)==str(row_voro.iloc[0][comcol])].reset_index(drop=True)
        return [row_voro,row_point]
    except Exception as e:
        print(f"La fonction filter_voro_points a planté en raison d'une {e}")

def lat_lon_voropoint(row_point:gpd.geodataframe.GeoDataFrame) -> tuple:
    """
        Cette fonction retourne les latitudes et longitude formatées en chaîne de caractères depuis une GeoDataFrame 
        à une ligne (un point)
    """
    try:
        lat, lon = str(row_point.iloc[0]["geometry"].x),str(row_point["geometry"].iloc[0].y)
        return lat, lon
    except Exception as e:
        print(f"La fonction lat_lon_voropoint a planté en raison d'une {e}")

def gdf_isochrone(pointgdf:gpd.geodataframe.GeoDataFrame,
                  col_ref:str,
                  coord:tuple,
                  durations:list,
                  profile="car") -> gpd.geodataframe.GeoDataFrame:
    """
        Cette fonction renvoie des zones isochrones calculées grâce à une API fournie par une plateforme fournie par l'IGN.
        Elle se base sur des points d'arrivées, considère des durées exprimées en minutes, et par défaut considère des trajets en voiture
        Documentation : https://geoservices.ign.fr/documentation/services/services-geoplateforme/itineraire#72786
    """
    try:
        isochrones = pd.DataFrame()
        for cvalue in durations:
            r = requests.get(f"https://data.geopf.fr/navigation/isochrone?point={coord[0]}%2C{coord[1]}&resource=bdtopo-valhalla&costValue={cvalue}&costType=time&profile={profile}&direction=arrival&constraints=%7B%22constraintType%22%3A%22banned%22%2C%22key%22%3A%22wayType%22%2C%22operator%22%3A%22%3D%22%2C%22value%22%3A%22autoroute%22%7D&geometryFormat=geojson&distanceUnit=meter&timeUnit=minute&crs=EPSG%3A4326")
            df = pd.json_normalize(r.json())
            df[col_ref] = pointgdf.iloc[0][col_ref]
            df["geometry"] = [Polygon(coords) 
                              for l 
                              in df["geometry.coordinates"] 
                              for coords in l]
            df = df[[col_ref,"costValue","geometry"]]
            isochrones = pd.concat([isochrones,df],
                                   ignore_index=True)
        return gpd.GeoDataFrame(isochrones,
                                geometry=isochrones["geometry"])
    except Exception as e:
        print(f"La fonction gdf_isochrone a planté en raison d'une {e}")

def poly_puzzle(gdf:gpd.geodataframe.GeoDataFrame) -> gpd.geodataframe.GeoDataFrame:
    """
        Cette fonction découpe des GeoDataFrames qui se superposent afin de bien distinguer leurs géométries.
    """
    try:
        geo_sub = [gdf.iloc[[i]].symmetric_difference(gdf.iloc[i-1]["geometry"]).iloc[0]
                   for i in range(len(gdf)-1,0,-1)]
        geo_sub = [gdf.iloc[0]["geometry"]]+list(reversed(geo_sub))
        gdf["geometry"] = geo_sub
        return gdf
    except Exception as e:
        print(f"La fonction poly_puzzle a planté en raison d'une {e}")

def diff_poly(largegdf:gpd.geodataframe.GeoDataFrame,
              minorgdf:gpd.geodataframe.GeoDataFrame) -> gpd.geodataframe.GeoDataFrame:
    """
        Cette fonction fait la différence entre une "grande" GeoDataFrame et une plus petite pour en proposer la différence.
    """
    try:
        geo_intersection = [largegdf.iloc[[i]].intersection(minorgdf.iloc[0]["geometry"]).iloc[0]
                            for i in range(0,len(largegdf))]
        largegdf["geometry"] = geo_intersection
        largegdf = largegdf[~largegdf["geometry"].is_empty].reset_index(drop=True)
        return largegdf
    except Exeption as e:
        print(f"La fonction diff_poly a planté en raison d'une {e}")

# et maintenant, application avec des variables
maternites = gpd.read_file("data/mat.json")
maternites = maternites[maternites["2023"]!=0].reset_index(drop=True)
voro_mat = gpd.read_file("data/voro_mat23_bzh.shp")
voro_def = maternites.sjoin(voro_mat, how="right")

iso_bzh = pd.DataFrame()
for i in range(len(voro_def)):
    voro_point = filter_voro_points(i,
                                    voro_def,
                                    maternites,
                                    "NOM")
    coords = lat_lon_voropoint(voro_point[1])
    trajets_voro = gdf_isochrone(voro_point[1],
                                 "NOM",
                                 coords,
                                 ["10",
                                  "20",
                                  "30",
                                  "50",
                                  "70",
                                  "90"])
    print(trajets_voro["NOM"].unique()[0])
    trajets_voro = poly_puzzle(trajets_voro)
    trajets_voro = diff_poly(trajets_voro,
                             voro_point[0])
    iso_bzh = pd.concat([iso_bzh,trajets_voro],
                        ignore_index=True)

iso_bzh = iso_bzh[["costValue","geometry"]].dissolve(by="costValue").reset_index()

iso_bzh.to_file("data/dvoro_mat23.shp")