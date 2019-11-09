#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests, re, csv
from bs4 import BeautifulSoup

depart ="https://fr.wikipedia.org/wiki/Liste_des_monuments_historiques_d"
villes = ["e_Reims", "e_Chaumont", "e_Charleville-Mézières", "e_Toul", "e_Pont-à-Mousson", "e_Haguenau", "e_Châlons-en-Champagne", "e_Troyes", "e_Verdun", "e_Bar-le-Duc", "'Épinal", "e_Nancy", "e_Metz", "e_Colmar", "e_Sélestat", "e_Mulhouse", "e_Strasbourg"]
ficsv = open('livraisons/monuments_histo_ge.csv','w+')

try:
	majcsv = csv.writer(ficsv)
	majcsv.writerow(('Monument','Adresse','Longitude','Latitude','Source'))
	for ville in villes:
		url_ville = depart+ville # une simple addition de chaînes de cara' nous donne nos URL complètes
		url = requests.get(url_ville) # et on ouvre l'URL actuelle
		print("Lien : "+url_ville)
		soupe = BeautifulSoup(url.text, "lxml")
		tableau = soupe.find("table", {"class":"wikitable sortable"})
		lignes = tableau.findAll("tr")
		for ligne in lignes:
			monuments = ligne.findAll("td")
			carto = ligne.find("a", {"class":"mw-kartographer-maplink"})
			source = ligne.findAll("a", {"href":re.compile("^https://www.pop.culture.gouv")}) 
			if monuments and carto and source:
				monument = monuments[0].get("data-sort-value")
				adresse = monuments[1].get_text()
				longitude = float(carto.get('data-lat'))
				latitude = float(carto.get('data-lon'))
				lien = source[0].get('href')
				majcsv.writerow((monument, adresse, longitude, latitude, lien))
finally:
	ficsv.close()