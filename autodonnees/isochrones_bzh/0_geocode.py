import geopandas as gpd
import pandas as pd
from geopy.geocoders import Nominatim


def extract_coord(adress:str,
                  coord="latitude") -> float:
    """
        Cette fonction renvoie la latitude ou la longitude correspondant à une adresse type RUE/VILLE.
    """
    geolocator = Nominatim(user_agent="operation_python",timeout=10)
    try:
        if coord=="latitude":
            return geolocator.geocode(adress).latitude
        elif coord=="longitude":
            return geolocator.geocode(adress).longitude
    except Exception as e:
        print(f"Le géocodage de l'adresse {adress} a planté, on se rabat sur le centre de la ville")
        if coord=="latitude":
            return geolocator.geocode(adress.split(",")[1]).latitude
        elif coord=="longitude":
            return geolocator.geocode(adress.split(",")[1]).longitude


dep_bzh = ["22",
           "29",
           "35",
           "44",
           "56"]

corres_adresse = {" R ":" RUE ",
                  "^R ":"RUE ",
                  " CHE ":" CHEMIN ",
                  "^CHE ":"CHEMIN ",
                  " PL ":" PLACE ",
                  "^PL ":"PLACE ",
                  " RTE ":" ROUTE ",
                  "^RTE ":"ROUTE",
                  " BD ":" BOULEVARD ",
                  "^BD":"BOULEVARD ",
                  " AV ":" AVENUE ",
                  "^AV ":"AVENUE ",
                  " FG ":" FAUBOURG ",
                  "^FG ":"FAUBOURG ",
                  " ALL ":" ALLÉE ",
                  "^ALL ":"ALLÉE ",
                  " LD ":" LIEU-DIT ",
                  "^LD ":"LIEU-DIT "}

maternites_2000 = pd.read_excel("raw/Fichier_Maternites_122024.xlsx",
                                sheet_name="Maternités_2000",
                                skiprows=5)
bzh_2000 = maternites_2000[maternites_2000["COM"].str.slice(0,2).isin(dep_bzh)].reset_index(drop=True)

for k,v in corres_adresse.items():
    bzh_2000["ADRESSE"] = bzh_2000["ADRESSE"].str.replace(k,v,regex=True)

bzh_2000.at[4,"ADRESSE"] = "RUE DE TROROZEC"
bzh_2000.at[14,"ADRESSE"] = "RUE DU DOCTEUR MENGUY"
bzh_2000.at[16,"ADRESSE"] = "20 AVENUE DU GENERAL LECLERC"
bzh_2000.at[17,"ADRESSE"] = "RUE ERNESTINE DE TREMAUDAN"
bzh_2000.at[19,"ADRESSE"] = "4 PLACE SAINT GUENOLE"
bzh_2000.at[39,"ADRESSE"] = "27 RUE DU DOCTEUR LETTRY"

full_adress = bzh_2000["ADRESSE"]+","+bzh_2000["NOMCOM"]
bzh_2000["LATITUDE"] = full_adress.apply(extract_coord)
bzh_2000["LONGITUDE"] = full_adress.apply(extract_coord,coord="longitude")

maternites_2023 = pd.read_excel("raw/Fichier_Maternites_122024.xlsx",
                                sheet_name="Maternités_2023",
                                skiprows=5)
bzh_2023 = maternites_2023[maternites_2023["COM"].str.slice(0,2).isin(dep_bzh)].reset_index(drop=True)

bzh_2000.rename(columns={"NOM_MAT":"NOM",
                         "ACCTOT":"2000"},inplace=True)
bzh_2023.rename(columns={"NOM_MAT":"NOM",
                         "ACCTOT":"2023"},inplace=True)

bzh_2023 = bzh_2023[["NOM","STATUT","FI_ET","NOMCOM","ADRESSE","2023"]]

mat = bzh_2000.merge(bzh_2023[["FI_ET","2023"]],on="FI_ET",how="left")

mat["2023"].fillna(0,inplace=True)
mat["2023"] = mat["2023"].astype(int)

id_list = list(mat[mat["2023"]!=0]["FI_ET"])
reste = bzh_2023[~bzh_2023["FI_ET"].isin(id_list)].reset_index(drop=True)

for k,v in corres_adresse.items():
    reste["ADRESSE"] = reste["ADRESSE"].str.replace(k,v,regex=True)
reste.at[3,"ADRESSE"] = "11 RUE DU DOCTEUR JOSEPH AUDIC"

full_adress = reste["ADRESSE"]+","+reste["NOMCOM"]
reste["LATITUDE"] =  full_adress.apply(extract_coord)
reste["LONGITUDE"] =  full_adress.apply(extract_coord,
                                       coord="longitude")
reste["2000"] = 0
reste = reste[["NOM","STATUT","FI_ET","NOMCOM","ADRESSE","2000","2023","LATITUDE","LONGITUDE"]]

mat = mat[list(reste.columns)]
mat = pd.concat([mat,reste],ignore_index=True)

geo_mat = gpd.points_from_xy(mat["LONGITUDE"], mat["LATITUDE"], z=None, crs=None)

carto_mat = gpd.GeoDataFrame(mat[list(mat.columns)[:-2]],
	                         geometry=geo_mat)
carto_mat.sort_values(by=["2000","2023"],
	                  ascending=False,
	                  inplace=True)
carto_mat = carto_mat.reset_index(drop=True)

geo_bzh = gpd.read_file("data/contours.json")

geo_bzh["region"] = "Bretagne"
geo_bzh = geo_bzh[['region', 'geometry']].dissolve(by="region")

geo_bzh.to_file("raw/contours_bzh.json",driver="GeoJSON")
carto_mat.to_file("data/mat.json",driver="GeoJSON")
