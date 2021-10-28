import requests
import pandas as pd
import geopandas as gpd
from bs4 import BeautifulSoup

class HorizonVF:
    def __init__(self, departement:int, l_villes:list, l_annees:list, l_biens:list, l_mutations:list):
        """
            L'initialisation d'un objet HorizonVF requiert un département, une liste de villes, une
            liste d'années.
        """
        self.departement = departement
        self.l_villes = l_villes
        self.l_annees = l_annees
        self.l_biens = l_biens
        self.l_mutations = l_mutations

    def selec_dep(self, annee:int):
        DF = pd.read_csv(r"https://files.data.gouv.fr/geo-dvf/latest/csv/"+str(annee)+"/full.csv.gz", encoding="UTF-8", low_memory=False)
        DF = DF[['id_mutation', 'nature_mutation', 'code_commune', 'nom_commune', 'code_departement',
                   'id_parcelle', 'ancien_id_parcelle', 'code_type_local', 'type_local',
                   'valeur_fonciere','surface_reelle_bati', 'surface_terrain', 'longitude', 'latitude']]
        DF.drop_duplicates(subset="id_mutation",keep=False,inplace=True,ignore_index=True)
        DF["code_commune"] = DF["code_commune"].astype(str).str.rjust(5,"0")
        DF["code_departement"] = DF["code_departement"].astype(str).str.rjust(2,"0")
        DF = DF[DF["code_departement"] == str(self.departement)]
        DF = DF[(DF["nature_mutation"].isin(self.l_mutations)) & (DF["type_local"].isin(self.l_biens))]
        DF = DF.reset_index()
        DF.drop(columns="index",inplace=True)
        return DF

    def selec_villes(self, annee:int):
        """
            Cette fonction renvoie une DataFrame qui contient toutes les données relatives aux
            biens scrutés pour une ville présente dans la liste soumise lors de l'initialisation
            d'un HorizonDF.
        """
        DF = self.selec_dep(annee)
        DF = DF[(DF["code_commune"].isin(self.l_villes))]
        DF.dropna(subset=["valeur_fonciere","surface_reelle_bati"], inplace=True)
        return DF

    def prix_annee(self,DF):
        """
            Cette fonction renvoie une DataFrame avec les prix et décomptes de chaque type
            de bien retenu, colonnes respectivement nommées p_type et d_type
        """
        DF.dropna(subset=["valeur_fonciere","surface_reelle_bati"], inplace=True)
        DF["prix_m2"]=round(DF["valeur_fonciere"].astype(float)/DF["surface_reelle_bati"].astype(float)).astype(int)
        DF["decompte"]=1
        types=list(DF["type_local"].unique())
        DF1 = DF.groupby(["nom_commune","code_commune","type_local"]).agg({"prix_m2":lambda x: round(x.median(),2)}).reset_index()
        DF1 = DF1.pivot(index=["code_commune","nom_commune"], columns="type_local", values="prix_m2").reset_index()
        DF1.rename(columns={t:"p_"+str(t).split(" ")[0].lower() for t in types}, inplace=True)
        DF1.fillna(0, inplace=True)
        for t in types:
            DF1["p_"+str(t).split(" ")[0].lower()]=DF1["p_"+str(t).split(" ")[0].lower()].astype(int)
        DF2 =  DF.groupby(["code_commune","nom_commune","type_local"]).agg({"decompte":lambda x: sum(x)}).reset_index()
        DF2 = DF2.pivot(index=["code_commune","nom_commune"], columns="type_local", values="decompte").reset_index()
        DF2.rename(columns={t:"d_"+str(t).split(" ")[0].lower() for t in types}, inplace=True)
        DF2.fillna(0, inplace=True)
        for t in types:
            DF2["d_"+str(t).split(" ")[0].lower()]=DF2["d_"+str(t).split(" ")[0].lower()].astype(int)
        DF = DF1.merge(DF2, on=["code_commune","nom_commune"])
        return DF

    def prix_dico(self,x):
        """
            Cette fonction renvoie, à partir de la liste de biens renseignée par l'utilisateur,
            un dico avec prix médian et décompte de chaque type. Objectif : rassembler ces
            informations par année
        """
        liste_types = [u.split(" ")[0].lower() for u in self.l_biens]
        dic = {}
        for t in liste_types:
            dic["p_"+t]=int(x["p_"+t].iloc[0])
            dic["d_"+t]=int(x["d_"+t].iloc[0])
        return dic

    def histo_prix(self):
        """
            Cette fonction renvoie un dictionnaire qui agrège des colonnes correspondant
            à des années. Objectif : agréger toutes les années et chiffres de biens
            dans une seule colonne
        """
        DF=self.selec_villes(self.l_annees[0])
        DF=self.prix_annee(DF)
        DF=DF.groupby(by=["code_commune","nom_commune"]).apply(self.prix_dico).reset_index(name=self.l_annees[0])
        if len(self.l_annees)>1:
            for i in range(self.l_annees[0]-1,self.l_annees[1],-1):
                DF_trans=self.selec_villes(i)
                DF_trans=self.prix_annee(DF_trans)
                DF_trans=DF_trans.groupby(by=["code_commune","nom_commune"]).apply(self.prix_dico).reset_index(name=i)
                DF= DF.merge(DF_trans, on=["code_commune","nom_commune"])
        DF = DF.set_index(["code_commune","nom_commune"])
        DF=DF.apply(lambda x: {f'{col}':x[col] for col in range(self.l_annees[0],self.l_annees[1],-1)}, 1).reset_index(name="histo_prix")
        return DF


metropole_lyon=[]
url = "https://fr.wikipedia.org/wiki/M%C3%A9tropole_de_Lyon"
url = requests.get(url)

soupe = BeautifulSoup(url.text, "lxml")
tableau = soupe.find("table", {"class":"wikitable sortable"})
lignes = tableau.findAll("tr")

for ligne in lignes:
    info_ville = ligne.findAll("td")
    if info_ville:
        metropole_lyon.append(info_ville[1].get_text().replace("\n",""))

com_mlyon = metropole_lyon[:]

insee_lyon = []
for i in range(1,10):
    insee_lyon.append("6938"+str(i))

metropole_lyon.remove("69123")
metropole_lyon.extend(insee_lyon)

foncierateur = HorizonVF(69, metropole_lyon, [2020,2015], ["Maison","Appartement"],["Vente"])
transac_mlyon = foncierateur.histo_prix()
transac_mlyon.rename(columns={"code_commune":"insee","nom_commune":"nom"}, inplace=True)


# tout ceci est l'aspect géo avec exports, que je mets en commentaires


# communes_mlyon = gpd.read_file("C:/Users/Rapha/Documents/Data/Geographie/France/Rhone/Lyon/Métropole/metropole_lyon.json")
#communes_mlyon.drop(columns=["nom"], inplace=True)
#geo_immo_lyon = transac_mlyon.merge(communes_mlyon, on="insee")
#geo_immo_lyon = gpd.GeoDataFrame(geo_immo_lyon, geometry=geo_immo_lyon["geometry"])
#geo_immo_lyon.to_file("data/immo_lyon.json", driver="GeoJSON")

#communes = gpd.read_file("https://osm13.openstreetmap.fr/~cquest/openfla/export/communes-20210101-shp.zip")
#communes.drop(columns=["wikipedia","surf_ha"], inplace=True)
#communes_mylon=communes[communes["insee"].isin(com_mlyon)].reset_index()
#communes_mylon.drop(columns="index",inplace=True)
#communes_mylon["geometry"]=communes_mylon["geometry"].simplify(.00003)
#contours = communes_mylon.boundary
#contours.to_file("data/contours.json", driver="GeoJSON")

#lyon = communes[communes["nom"]=="Lyon"].copy()
#lyon.drop(columns="insee",inplace=True)
#lyon["geometry"]=lyon["geometry"].centroid
#lyon.to_file("data/villes.json", driver="GeoJSON")
