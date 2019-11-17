#!/usr/bin/python
# -*- coding: utf-8 -*-
from urllib.request import urlopen
from lxml import etree
import json

departements = ["67", "68"]
exceptions = ["68224", "68006", "67482", "67372"]
partis = {"MDM": "MODEM","COM": "PC", "SOC" : "PS", "REM" : "LREM", "REG": "UL"}
liste_objets = []

for departement in departements:
	arbre = etree.parse(urlopen("https://elections.interieur.gouv.fr/telechargements/LG2017/resultatsT2/0"+departement+"/0"+departement+"com.xml"))
	print ("Department numero "+departement)
	for noeud in arbre.xpath("//Election/Departement/Communes/Commune"):
		objet = {}
		for circo in noeud.xpath("CodCirLg"):
			codecirco = circo.text[1]
		for insee in noeud.xpath("CodSubCom"):
			code_insee = departement+insee.text
			if (code_insee in exceptions):
				objet["insee"] = code_insee+codecirco
				print(objet["insee"])
			else:
				objet["insee"] = code_insee
		for resultats in noeud.xpath("Tours/Tour[NumTour=2]"):
			candidats = []
			for inscrits in resultats.xpath("Mentions/Inscrits/Nombre"):
				objet["ins"] = int(inscrits.text)
			for abstentions in resultats.xpath("Mentions/Abstentions/Nombre"):
				objet["abs"] = int(abstentions.text)
			for exprimes in resultats.xpath("Mentions/Exprimes/Nombre"):
				objet["exp"] = int(exprimes.text)
			for candidat in resultats.xpath("Resultats/Candidats/Candidat"):
				res_candidat = {}
				for famille in candidat.xpath("NomPsn"):
					mifa = famille.text
				for prenom in candidat.xpath("PrenomPsn"):
					preno = prenom.text
				res_candidat["nom"] = preno+" "+mifa.title()
				for codenu in candidat.xpath("CodNua"):
					nunu = codenu.text
					if nunu in partis.keys():
						nunu=partis[nunu]
					res_candidat["nuance"] = nunu
				for voix in candidat.xpath("NbVoix"):
					if voix == "":
						vox = 0
					else:
						vox = int(voix.text)
				res_candidat["voix"] = vox
				res_candidat["pourc"] = round((float(vox/objet["exp"]))*100,2)
				res_candidat["pourci"] = round((float(vox/objet["ins"]))*100,2)
				candidats.append(res_candidat)
				candidats = sorted(candidats, key=lambda d: d['voix'], reverse=True)
		objet["candidats"] = candidats
		liste_objets.append(objet)

ficjson = open('leg017_communes_alsace.json','w+')
ficjson.write(json.dumps(liste_objets))