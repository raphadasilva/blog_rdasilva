#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests, re, csv
from bs4 import BeautifulSoup

url = requests.get("https://fr.wikipedia.org/wiki/Liste_des_monuments_historiques_de_Nancy")
soupe = BeautifulSoup(url.text, "lxml")
tableau = soupe.find("table", {"class":"wikitable sortable"}) # on considère le premier tableau de classe "wikitable sortable"
lignes = tableau.findAll("tr") # puis toutes ses lignes

ficsv = open('monuments_histo_nancy.csv','w+')

try:
	majcsv = csv.writer(ficsv)
	majcsv.writerow(('Monument','Adresse','Longitude','Latitude','Source'))
	for ligne in lignes:
		info_monument = ligne.findAll("td") # on fait les premières sélections
		carto = ligne.find("a", {"class":"mw-kartographer-maplink"})
		notice = ligne.findAll("a", {"href":re.compile("^https://www.pop.culture.gouv")})
		if info_monument and carto and notice: # si les sélections existent, on enregistre les informations pour le csv
			monument = info_monument[0].get("data-sort-value")
			adresse = info_monument[1].getText()
			longitude = float(carto.get('data-lat'))
			latitude = float(carto.get('data-lon'))
			source = notice[0].get('href')
			print(monument, adresse, longitude, latitude, source)
			majcsv.writerow((monument, adresse, longitude, latitude, source))
finally:
	ficsv.close()
