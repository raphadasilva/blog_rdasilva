import geopandas as gpd
import numpy as np
import pandas as pd
from geovoronoi import voronoi_regions_from_coords

bzh = gpd.read_file("raw/contours_bzh.json")
mat = gpd.read_file("data/mat.json")
# pour avoir 2000, il suffit de mettre à jour le filtre sur la colonne "2000"
mat_23 = mat[mat["2023"]!=0].reset_index(drop=True)

coords = np.array([[x,y] 
                   for x,y 
                   in zip(list(mat_23["geometry"].x),
                          list(mat_23["geometry"].y))])

region_polys, region_pts = voronoi_regions_from_coords(coords, bzh.iloc[0]["geometry"])

polys = gpd.GeoDataFrame([k 
                          for k 
                          in region_polys.keys()],
                          geometry = [v 
                                      for v 
                                      in region_polys.values()])

polys.rename(columns={0:"index"},inplace=True)

polys.explode().to_file("raw/voro_mat23_bzh.shp")