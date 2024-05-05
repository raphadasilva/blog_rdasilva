Ce dossier contient la documentation et fichiers nécessaires à l'élabortion d'une cartographie satellite des prochaines éclipses solaires totales et annulaires attendues sur la péninsule ibérique.

![tres_eclipses](https://github.com/raphadasilva/blog_rdasilva/blob/master/geographie/tres_eclipses/data/eclipses_espana.jpg)

Ce travail a nécessité de jongler entre beaucoup de modules, j'ai en conséquence préféré le scinder en deux.

## [Partie 1 : préparer un fond de carte personnalisé à partir de raster et d'un extrait de film](https://github.com/raphadasilva/blog_rdasilva/blob/master/geographie/tres_eclipses/fond-carte_rasterio-cv2-kmeans.ipynb)

L'enjeu de cette partie se résume à passer de ceci :

![ir_espana](https://github.com/raphadasilva/blog_rdasilva/blob/master/geographie/tres_eclipses/data/espagne_r.jpg)

A cela :

![espana_pi](https://github.com/raphadasilva/blog_rdasilva/blob/master/geographie/tres_eclipses/data/espagne_16pi_r.jpg)

En prenant un détour par ceci :

![planete_interdite](https://github.com/raphadasilva/blog_rdasilva/blob/master/geographie/tres_eclipses/data/forbidden_planet.jpg)

Cela est rendu possible en utilisant l'algorithme des K-moyennes depuis le module OpenCV. Quelques manipulations avec rasterio sont aussi requises afin d'enregistrer les fichiers géographiques en images.

## [Partie 2 : récupérer les trajets d'éclipses et ajouter quelques villes en repères](https://github.com/raphadasilva/blog_rdasilva/blob/master/geographie/tres_eclipses/data-eclipse_astropy-geopandas.ipynb)

Le moment est venu de faire feu de tout bois, avec :
* **la récupération du trajet des éclipses** à partir des dates connues. Cela est rendu possible grâce au travail récent [d'Erik Bernhardsson](https://erikbern.com/2024/04/07/predicting-solar-eclipses-with-python), articulé autour du module Astropy
* de la dentelle, **avec des largeurs personnalisées en fonction des éclipses**. Pour cela , un seul acronyme : NASA.
* 
