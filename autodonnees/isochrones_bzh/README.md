J'ai eu le plaisir de réaliser mes premières pige pour Splann! cette année. Pour le dernier volet de l'enquête sur [l'état de l'hôpital dans la région](https://splann.org/enquete/hopital-destruction-programmee/), je me suis penché sur un type de cartographie particulièrement ambitieux : **une isochrone articulée autour des temps de trajet en voiture pour rejoindre la maternité la plus proche à vol d'oiseau** :
![Carte isochrone réalisée pour Splann!](pictures/carto_splann0.jpg)

La principale inspiration était [la carte dressée par Cédric Rossi](https://www.ign.fr/files/default/2024-09/Proximite_urgences_CRossi_0.png) sur les services d'urgences en France. Ce dernier était disposé à nous filer un coup de main sur les données qu'il avait utilisées, mais j'ai suggéré d'essayer de trouver notre propre chemin, afin de faire du sur mesure pour la cartographie finale. 

Des urgences, nous sommes finalement passés à l'implantation des maternités en Bretagne et Loire-Atlantique, pour les années 2000 et 2023. C'était un travail imposant avant d'aboutir à une cartographie interactive en JavaScript, que j'ai tenu à documenter de la façon que j'espère la plus complète possible (en tout cas en ce qui concerne la partie de données). Il y a donc **un calepin Jupyter à disposition** pour chaque partie de la recette, **ainsi que sa version scriptée** si jamais une personne désirant recycler ce travail ne voulait pas s'embarrasser de texte explicatif.

Pour toute remarque ou question, voici mon adresse courriel : raphadasilva\[at\]proton.me

# Partie 1 : géocoder les maternités

![Géocodage des maternités](pictures/geocode_bzh.jpg)
