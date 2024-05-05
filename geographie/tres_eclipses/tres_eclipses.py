import math, pyproj,rasterio
import cv2 as cv
import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from astropy.coordinates import AltAz, EarthLocation, get_body
from astropy.time import Time
from astropy.units import deg, m
from datetime import datetime, timedelta, timezone
from matplotlib import patches
from matplotlib import text as mtext
from PIL import Image, ImageOps, ImageTk
from rasterio.enums import Resampling
from scipy.optimize import minimize
from shapely.geometry import LineString


# cette classe a été codée par Thomas Kühn afin de répondre à un ticket StackOverflow
# https://stackoverflow.com/questions/19353576/curved-text-rendering-in-matplotlib

class CurvedText(mtext.Text):
    """
    A text object that follows an arbitrary curve.
    """
    def __init__(self, x, y, text, axes, **kwargs):
        super(CurvedText, self).__init__(x[0],y[0],' ', **kwargs)

        axes.add_artist(self)

        ##saving the curve:
        self.__x = x
        self.__y = y
        self.__zorder = self.get_zorder()

        ##creating the text objects
        self.__Characters = []
        for c in text:
            if c == ' ':
                ##make this an invisible 'a':
                t = mtext.Text(0,0,'a')
                t.set_alpha(0.0)
            else:
                t = mtext.Text(0,0,c, **kwargs)

            #resetting unnecessary arguments
            t.set_ha('center')
            t.set_rotation(0)
            t.set_zorder(self.__zorder +1)

            self.__Characters.append((c,t))
            axes.add_artist(t)


    ##overloading some member functions, to assure correct functionality
    ##on update
    def set_zorder(self, zorder):
        super(CurvedText, self).set_zorder(zorder)
        self.__zorder = self.get_zorder()
        for c,t in self.__Characters:
            t.set_zorder(self.__zorder+1)

    def draw(self, renderer, *args, **kwargs):
        """
        Overload of the Text.draw() function. Do not do
        do any drawing, but update the positions and rotation
        angles of self.__Characters.
        """
        self.update_positions(renderer)

    def update_positions(self,renderer):
        """
        Update positions and rotations of the individual text elements.
        """

        #preparations

        ##determining the aspect ratio:
        ##from https://stackoverflow.com/a/42014041/2454357

        ##data limits
        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()
        ## Axis size on figure
        figW, figH = self.axes.get_figure().get_size_inches()
        ## Ratio of display units
        _, _, w, h = self.axes.get_position().bounds
        ##final aspect ratio
        aspect = ((figW * w)/(figH * h))*(ylim[1]-ylim[0])/(xlim[1]-xlim[0])

        #points of the curve in figure coordinates:
        x_fig,y_fig = (
            np.array(l) for l in zip(*self.axes.transData.transform([
            (i,j) for i,j in zip(self.__x,self.__y)
            ]))
        )

        #point distances in figure coordinates
        x_fig_dist = (x_fig[1:]-x_fig[:-1])
        y_fig_dist = (y_fig[1:]-y_fig[:-1])
        r_fig_dist = np.sqrt(x_fig_dist**2+y_fig_dist**2)

        #arc length in figure coordinates
        l_fig = np.insert(np.cumsum(r_fig_dist),0,0)

        #angles in figure coordinates
        rads = np.arctan2((y_fig[1:] - y_fig[:-1]),(x_fig[1:] - x_fig[:-1]))
        degs = np.rad2deg(rads)


        rel_pos = 10
        for c,t in self.__Characters:
            #finding the width of c:
            t.set_rotation(0)
            t.set_va('center')
            bbox1  = t.get_window_extent(renderer=renderer)
            w = bbox1.width
            h = bbox1.height

            #ignore all letters that don't fit:
            if rel_pos+w/2 > l_fig[-1]:
                t.set_alpha(0.0)
                rel_pos += w
                continue

            elif c != ' ':
                t.set_alpha(1.0)

            #finding the two data points between which the horizontal
            #center point of the character will be situated
            #left and right indices:
            il = np.where(rel_pos+w/2 >= l_fig)[0][-1]
            ir = np.where(rel_pos+w/2 <= l_fig)[0][0]

            #if we exactly hit a data point:
            if ir == il:
                ir += 1

            #how much of the letter width was needed to find il:
            used = l_fig[il]-rel_pos
            rel_pos = l_fig[il]

            #relative distance between il and ir where the center
            #of the character will be
            fraction = (w/2-used)/r_fig_dist[il]

            ##setting the character position in data coordinates:
            ##interpolate between the two points:
            x = self.__x[il]+fraction*(self.__x[ir]-self.__x[il])
            y = self.__y[il]+fraction*(self.__y[ir]-self.__y[il])

            #getting the offset when setting correct vertical alignment
            #in data coordinates
            t.set_va(self.get_va())
            bbox2  = t.get_window_extent(renderer=renderer)

            bbox1d = self.axes.transData.inverted().transform(bbox1)
            bbox2d = self.axes.transData.inverted().transform(bbox2)
            dr = np.array(bbox2d[0]-bbox1d[0])

            #the rotation/stretch matrix
            rad = rads[il]
            rot_mat = np.array([
                [math.cos(rad), math.sin(rad)*aspect],
                [-math.sin(rad)/aspect, math.cos(rad)]
            ])

            ##computing the offset vector of the rotated character
            drp = np.dot(dr,rot_mat)

            #setting final position and rotation:
            t.set_position(np.array([x,y])+drp)
            t.set_rotation(degs[il])

            t.set_va('center')
            t.set_ha('center')

            #updating rel_pos to right edge of character
            rel_pos += w-used

# les fonctions suivantes sont directement tirées du projet d'Erik Bernhardsson
# source : https://erikbern.com/2024/04/07/predicting-solar-eclipses-with-python

def gen_dts(dt_a: datetime, dt_b: datetime, sec_delta: float) -> list[datetime]:
  """
      Cette fonction retourne une liste de dates (AAAA,MM,JJ,HH,MM,SS) à partir de la différence de deux dates (une de départ, une d'arrivée) et d'un delta exprimé en secondes.
  """
    return [dt_a+timedelta(seconds=x) for x in range(0,(dt_b-dt_a).seconds,sec_delta)]

def sun_moon_separation(lat: float, lon: float, t: float) -> float:
    """
        Cette fonction renvoie, à une date de données la séparation en degrés entre la lune et le soleil depuis un plan horizontal ayant son origine sur Terre.
        Si cette séparation est égale ou très proche de zéro, une éclipse solaire a lieu.
    """
    loc = EarthLocation(lat=lat * deg, lon=lon * deg, height=0 * m)
    time = Time(t, format="unix")
    moon = get_body("moon", time, loc)
    sun = get_body("sun", time, loc)

    az = AltAz(obstime=time, location=loc)
    sun_az = sun.transform_to(az)
    moon_az = moon.transform_to(az)
    if sun_az.alt < 0 or moon_az.alt < 0:
        return 180

    sep = moon.separation(sun)
    return sep.deg

def find_eclipse_location(dt: datetime) -> tuple[datetime, float, float] | None:
  """
     A une date donnée, cette fonction renvoie un tuple composée d'une date, d'une latitude et d'une longitude (CRS 2346)
     si une éclipse solaire totale ou annulaire a lieu sur Terre.
     Si aucune éclipse n'a lieu, elle renvoie None.
  """
    t = datetime.timestamp(dt)
    fun = lambda x: sun_moon_separation(x[0], x[1], t)

    x0s = [
        (lat, lon)
        for lat in [-75, -45, -15, 15, 45, 75]
        for lon in [-150, -90, -30, 30, 90, 150]
        ]
    x0 = min(x0s, key=fun)

    ret = minimize(fun, bounds=[(-90, 90), (-180, 180)], x0=x0)

    if ret.fun < 1e-3:
        lat, lon = ret.x
        return (dt, lat, lon)
    else:
        return None

def data_eclipse(dt_min: datetime, dt_max: datetime,td_sec:int) -> dict:
    """
        Entre deux dates données (Temps universel coordonné largement conseillé), cette fonction renvoie un dictionnaire suivant le format :
        {date:[latitude,longitude],...} (coordonnées géographiques) si une éclipse se déroule aux dates considérées
    """
    dt_a = dt_min - timedelta(seconds=td_sec)
    dt_b = dt_max + timedelta(seconds=td_sec)
    print(f"Finding path of eclipse from {dt_a} to {dt_b}")
    el = [e for e in (find_eclipse_location(d) for d in gen_dts(dt_a, dt_b, td_sec)) if e is not None]
    dts = [t[0] for t in el]
    lats = [t[2] for t in el]
    lons = [t[1] for t in el]
    return {d:[lat,lon] for d, lon, lat in zip(dts, lons, lats)}


def gdf_eclipse(eclipses:dict) -> gpd.geodataframe.GeoDataFrame:
  """
    Cette fonction renvoie, sous réserve d'avoir mis en unique attribut un dictionnaire valide renvoyé par data_eclipse(),
    une ligne géographique à partir des différents points contenus dans le dictionnaire.
  """
  try:
    eclipse_date = str(list(eclipses.keys())[0].day)+"/"+str(list(eclipses.keys())[0].month)+"/"+str(list(eclipses.keys())[0].year)
    DF = pd.DataFrame()
    DF["latitude"] = [v[0] for v in eclipses.values()]
    DF["longitude"] = [v[1] for v in eclipses.values()]
    GDF = gpd.GeoDataFrame(columns=["date"],crs='epsg:4326', geometry=[LineString(DF.to_numpy())])
    GDF["date"] = eclipse_date
    return GDF
  except:
    print("Attention au format du dictionnaires d'éclipses ! Elle doit respecter la configuration suivante : {date0:[longitude0,latitude0],date1:[longitude1,latitude1],...}")


def buffer_meters(GDF:gpd.geodataframe.GeoDataFrame,buffer_m:int) -> gpd.geodataframe.GeoDataFrame:
    """
        Cette fonction renvoie la géométrie d'une GeoDataFrame déformée suivant un tampon exprimée en mètre.
        Si jamais la DataFrame  de référence n'est pas inscrite dans des coordonnées dont l'unité est le mètre, on la convertit d'abord avant d'appliquer le tampon et de la reprojeter 
        au système de coordonnées initial. 
    """
    try:
        crs_ref = gdf_esp_0826.crs
        if crs_ref.axis_info[0].unit_name=="metre":
            GDF["geometry"] = GDF["geometry"].buffer(buffer_m)
        else:
            GDF = GDF.to_crs("EPSG:25830")
            GDF["geometry"] = GDF["geometry"].buffer(buffer_m)
            GDF = GDF.to_crs(crs_ref)
        return GDF
    except:
        print("Veillez à renseigner un ordre de grandeur en mètre valide et/ou à bien pointer une GeoDataFrame")


def composite_png(img_start:np.ndarray,png:str) -> np.ndarray:
    """
        Cette fonction renvoie la superposition de deux images à partir de la bibliothèque OpenCV.
        ATTENTION : pour qu'elle marche, les deux images doivent impérativement être aux mêmes dimensions.
    """
    try:
        img_png = cv.imread(png, cv.IMREAD_UNCHANGED)
        alpha_png = img_png[:, :, 3]/255
        colors_png = img_png[:, :, :3]
        alpha_mask = np.dstack((alpha_png, alpha_png, alpha_png))
        h, w = img_png.shape[:2]
        img_trans = img_start[0:h, 0:w]
        composite = img_trans * (1 - alpha_mask) + colors_png * alpha_mask
        img_start[0:h, 0:w] = composite
        return img_start
    except:
        print("Attention à votre chemin et fichier et/ou format d'image et/ou taille d'images")


# d'abord, on réduit la palette de l'extrait de film à 16 couleurs
img = cv.imread("data\\forbidden_planet.jpg")
img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
Z = img.reshape((-1,3))
Z = np.float32(Z)
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 10, 1.0)
K = 16
ret,label,center = cv.kmeans(Z,K,None,criteria,10,cv.KMEANS_PP_CENTERS)
center = np.uint8(center)
res = center[label.flatten()]
res2 = res.reshape((img.shape))

# ensuite, on lit nos deux rasters qu'on reformate et enregistre en png
# (ces derniers sont très lourds et donc absents du sous-dossier data, vous pouvez trouver le chemin de téléchargement sur le calepin dédié au fond de carte)
norte = rasterio.open("data\\pnt_sentinel2_2024_invierno_mosaico_peninsula_illes-balears_b843_hu30_8bits_norte.tif")
sur = rasterio.open("data\\pnt_sentinel2_2024_invierno_mosaico_peninsula_illes-balears_b843_hu30_8bits_sur.tif")
for r,n in zip([norte,sur],["norte_red","sur_red"]):
    data = r.read(out_shape=(r.count,int(r.height*.1),int(r.width*.1)),resampling=Resampling.bilinear)
    with rasterio.open("data\\"+n+".png", 'w', driver='PNG', height=data.shape[1], width=data.shape[2], count=r.count, dtype=data.dtype) as dst:
        dst.write(data)

# on crée un nouveau png, résultat de la fusion des faces nord et sud enregistrées précédemment
norte_png = Image.open("data/norte_red.png")
sur_png = Image.open("data/sur_red.png")
esp_png = Image.new(mode="RGB", size=(norte_png.width,norte_png.height+sur_png.height), color=(0,0,0))
esp_png.paste(norte_png, (0,0))
esp_png.paste(sur_png, (0,norte_png.height))
esp_png.save("data\\espagne.png",subsampling=0, quality=100)

# on refait mouliner un K-moyenne sur ce fond de carte
esp = cv.imread("data\\espagne.png")
esp = cv.cvtColor(esp, cv.COLOR_BGR2RGB)
Y = esp.reshape((-1,3))
Y = np.float32(Y)
ret,label,center = cv.kmeans(Y,K,None,criteria,10,cv.KMEANS_PP_CENTERS)
center = np.uint8(center)
res = center[label.flatten()]
res_esp = res.reshape(esp.shape)
cv.imwrite("data\\espagne_16.png", cv.cvtColor(res_esp, cv.COLOR_RGB2BGR)) 

# et enfin, on intervertit les couleurs avant d'enregistrer tout ça dans un png définitif
ord_target = [[0,0,0],[39,40,45],[97,54,51],[114,67,63],[121,63,60],[122,57,56],[127,82,69],[129, 66, 64],[133,52,54],[133,94,84],[141,65,65],[150,109,93],[172,134,111],[186,62,67],[198,169,135],[233,225,224]]
ord_ref = [[105,120,103],[129,138,130],[98,81,64],[120,100,80],[135,113,92],[149,127,106],[17,15,15],[9,8,8],[89,106,88],[76,58,44],[168,152,138],[73,91,73],[59,76,61],[48,59,50],[41,42,37],[28,27,28]]
for t,r in zip(ord_target,ord_ref):
    res_esp[np.where((res_esp==t).all(axis=2))] = r
cv.imwrite("data\\espagne_16pi.png", cv.cvtColor(res_esp, cv.COLOR_RGB2BGR))


#AVERTISSEMENT : décommentez les lignes suivantes uniquement si vous voulez refaire tourner Astropy (PS : ce n'est pas nécessaire)

#esp_0826 = data_eclipse(datetime(2026, 8, 12, 18, 24, 0, tzinfo=timezone.utc),datetime(2026, 8, 12, 18, 32, 15, tzinfo=timezone.utc),5)
#esp_0827 = data_eclipse(datetime(2027, 8, 2, 8, 43, 0, tzinfo=timezone.utc),datetime(2027, 8, 2, 9, 1, 15, tzinfo=timezone.utc),5)
#esp_0128 = data_eclipse(datetime(2028, 1, 26, 16, 54, 0, tzinfo=timezone.utc),datetime(2028, 1, 26, 16, 58, 50, tzinfo=timezone.utc),5)

#gdf_esp_0826 = gdf_eclipse(esp_0826)
#gdf_esp_0827 = gdf_eclipse(esp_0827)
#gdf_esp_0128 = gdf_eclipse(esp_0128)
#gdf_esp_0826.to_file("data\\eclipse_0826.json",driver="GeoJSON")
#gdf_esp_0827.to_file("data\\eclipse_0827.json",driver="GeoJSON")
#gdf_esp_0128.to_file("data\\eclipse_0128.json",driver="GeoJSON")


# La preuve : des geojson tout propres se trouvent ici
gdf_esp_0826 = gpd.read_file("data\\eclipse_0826.json")
gdf_esp_0827 = gpd.read_file("data\\eclipse_0827.json")
gdf_esp_0128 = gpd.read_file("data\\eclipse_0128.json")


# on les reprojette et on les transforme suivant la largeur calculée par la NASA
gdf_esp_0826 = gdf_esp_0826.to_crs("EPSG:25830")
gdf_esp_0827 = gdf_esp_0827.to_crs("EPSG:25830")
gdf_esp_0128 = gdf_esp_0128.to_crs("EPSG:25830")
gdf_esp_0826 = buffer_meters(gdf_esp_0826,135000)
gdf_esp_0827 = buffer_meters(gdf_esp_0827,122000)
gdf_esp_0128 = buffer_meters(gdf_esp_0128,178000)

# on recharge les trajets d'éclipses précédents, qui serviront de référence à la légende
l_0826 = gpd.read_file("data\\eclipse_0826.json")
l_0827 = gpd.read_file("data\\eclipse_0827.json")
l_0128 = gpd.read_file("data\\eclipse_0128.json")
l_0826 = l_0826.to_crs("EPSG:25830")
l_0827 = l_0827.to_crs("EPSG:25830")
l_0128 = l_0128.to_crs("EPSG:25830")
dl_0826 = np.vstack(l_0826.iloc[0].geometry.coords.xy)[:,47:]
dl_0827 = np.vstack(l_0827.iloc[0].geometry.coords.xy)[:,39:]
dl_0128 = np.vstack(l_0128.iloc[0].geometry.coords.xy)[:,23:]

# on rassemble ces lignes et ces légndes dans deux listes dédiées
l_eclipses = [dl_0826,dl_0827,dl_0128]
t_eclipses = ["Eclipse total del 12 de agosto de 2026","Eclipse total del 2 de agosto de 2027","Eclipse anular del 26 de enero de 2028"]


# et on fait tourner tout ça pour avoir un calque
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Consolas'] + plt.rcParams['font.serif']
plt.rcParams['mathtext.default']

fig, ax = plt.subplots(figsize=(12.058, 10.128), dpi=100,constrained_layout=True)

ax.set_ylim(3870655.0131369503,4883505.01313695)
ax.set_xlim(-74125.16131267,1131704.83868733)
for d,t in zip(l_eclipses,t_eclipses):
    t_def = CurvedText(x = d[0],y = d[1],text=t, color="#A8988A", va = 'bottom',axes = ax,fontsize=18)
gdf_esp_0826.plot(ax=ax, color="#090808", alpha=.5,zorder=0)
gdf_esp_0827.plot(ax=ax, color="#090808", alpha=.5,zorder=0)
gdf_esp_0128.plot(ax=ax, color="#090808", alpha=.3,zorder=0)

ax.axis('off')
plt.savefig('data\\eclipsesp.png', dpi=1000, transparent=True);

# on prépare quelques repère géographiques à partir d'un shp des communes espagnoles
ciudades = gpd.read_file("data\\recintos_municipales_inspire_peninbal_etrs89.shp")
l_ciudades = ["València","Palma","Cádiz","Madrid"]
ecl_ciudades = ciudades.copy()
ecl_ciudades = ecl_ciudades[ecl_ciudades["NAMEUNIT"].isin(l_ciudades)]
ecl_ciudades = ecl_ciudades.to_crs("EPSG:25830")
ecl_ciudades["geometry"] = ecl_ciudades["geometry"].centroid

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Osaka'] + plt.rcParams['font.serif']
plt.rcParams['mathtext.default']

# on enregistre un nouveau calque de ces villes, avec la source
fig, ax = plt.subplots(figsize=(12.058, 10.128), dpi=100,constrained_layout=True)

ax.set_ylim(3870655.0131369503,4883505.01313695)
ax.set_xlim(-74125.16131267,1131704.83868733)

for x, y, label in zip(ecl_ciudades.geometry.x, ecl_ciudades.geometry.y, ecl_ciudades.NAMEUNIT):
    ax.annotate(label, xy=(x, y), xytext=(3, 3), textcoords="offset points",fontsize=13,color="white")

ax.text(850000, 3900000, "Fuente : CNIG + NASA + Astropy",  color="#A8988A", fontsize=13);
ax.axis('off')
plt.savefig('data\\ciudades.png', dpi=1000, transparent=True)


# on superpose les  trois calques dans le bon ordre (si les villes sont masquées c'est sans doute mieux ,vu le sujet de l'infog)
#res_esp = cv.imread("data\\espagne_16pi.png")
#res_esp = cv.cvtColor(res_esp, cv.COLOR_BGR2RGB)
res_esp = composite_png(res_esp,"data\\ciudades.png")
res_esp = composite_png(res_esp,"data\\eclipsesp.png")

# et on enregistre le résultat final
fig, ax = plt.subplots(figsize=(22, 20),constrained_layout=True)
ax.set_title("Antes de 2029, dos eclipses solares pasarán cerca de Cádiz, Palma o València",fontsize=30)
ax.get_xaxis().set_visible(False)
ax.get_yaxis().set_visible(False)
ax.imshow(res_esp)
plt.savefig('data\\eclipses_espana.jpg', dpi=300, bbox_inches = 'tight');
