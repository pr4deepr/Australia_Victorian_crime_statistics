
import folium
import json
import pandas as pd
import numpy as np
from matplotlib import colors, cm
from matplotlib.colors import rgb2hex


#function for removing duplicates and preserving order
def de_dup(seq): 
   # order preserving
   check = []
   for i in seq:
       if i not in check:
           check.append(i)
   return check

# mask is created using np.in1d; create a mask with condition, are values in change present in compared; create a mask based on this and apply to 'change'
def masker(change,compared):
    mask=np.in1d(change,compared)
    change=change[mask]
    return change

df_post=pd.read_csv("CrimebyPostcode.csv",encoding = "cp1252")
df_post.head()
df_post=df_post.set_index('Postcode')
df_post=df_post.filter(regex='y_')
crime_zip=df_post.mean(axis=1) #average of crimes (could do an animation slider for each year)
crime_zip.max()

# set the value range (Crime number range)
vmin = 0
vmax = 24000

with open('victoria.json') as f:
    data = json.load(f)

postcodes=[]

#get council names according to postcode
council_name=pd.read_excel('Postcode_council name.xls',skiprows=2,parse_cols=[1,5])
#convert to dictionary, which eliminates duplicate postcodes (different wards under the same postcode)
#set postcode as id, transpose it as to_dict use columns name as dictionary key, if there is more than one value, use list instead of 'records' can store more info
council_name=council_name.set_index('Post\r\nCode').T.to_dict('list')

for i,j in enumerate(data['features']):
    postcode=int(j['properties']['POSTCODE']) 
    postcodes.append(postcode)
    
#remove duplicate postcodes from list using de_dup function defined earlier
postcodes=de_dup(postcodes)   

#convert to np array for use with masks
postcodes=np.array(postcodes) 

council_zip=list(council_name.keys())
council_zip=np.array(council_zip)

temp=council_zip #cannot iterate over keys and delete key:value pairs in dict, so creating an array of keys

#deleting values not shared between arrays

crimes1=crime_zip.index.values #zip codes from the crime data file stored as a list

#Inorder to account for differences in postcodes (deletions or additions), function masker is used a mask is created using np.in1d
#create a mask with condition, is values in crimes1 present in postcodes
crimes_match=masker(crimes1,postcodes)

#Do it the otherway around
crimes_match=de_dup(crimes_match)
postcodes=masker(postcodes,crimes_match)

council_zip=masker(council_zip,crimes_match)

#using council_zip to delete the postcode keys in council_name, so it matches postcdes and crimes_match
for i in temp:
    if i not in council_zip:
        del council_name[i]

logmin=0.1 #account for log-scaling,as log 0 is undefined and gives an error

#Define the colours to be used based on the crime number
#colours need to be normalized to the minimum and max value of the crime number
#Log Normalisation as it gives a better distribution across uneven ranges
norm=colors.LogNorm(vmin=max(crime_zip.values.min(),logmin),vmax=vmax)

#SCalarmappable makes use of data normalisation and converts scalar data (0-1) to RGBA values for a colour map (Greys, in this instant)
mapper=cm.ScalarMappable(norm=norm,cmap=cm.hot_r) #use this for scale

#dictionary to store postcode as key and the crime number will determine the RGB value, stored as corresponding value
niram={}

for i, v in enumerate(crime_zip):
    niram[crime_zip.index[i]]=mapper.to_rgba(v)[:3]  #returns rgba, where a is alpha. Do not need alpha so slicing it; );3, means only rgb
    niram[crime_zip.index[i]]=rgb2hex(niram[crime_zip.index[i]])

#create a json file with colour values based on the log scale created above; could add names as well

i=0
while i<len(data['features']):
    map_code=int(data['features'][i]['properties']['POSTCODE'])
    if map_code in niram:
        data['features'][i]['properties']['colour']=niram[map_code]
        data['features'][i]['properties']['district']=council_name[map_code][0]
        data['features'][i]['properties']['crime_avg']=crime_zip[map_code]
        i+=1
    else:
        i+=1

filename='new_vic.json'
with open(filename, 'w') as f:
        json.dump(data, f)
        
'''
import branca.colormap as bcm

log_colormap=bcm.LinearColormap(
    ['yellow','orange','red'],
    index=[0,crime_zip.values.mean(),vmax],
   vmin=0,
    vmax=vmax
)
'''

for i in range(len(data['features'])):
    data['features'][i]['properties']['POSTCODE']=int(data['features'][i]['properties']['POSTCODE'])
    
oz=folium.Map(location=[-37.81,144.96],
             zoom_start=6
             )
'''
used choropleth first, key_on needs to be the value in data that we are mapping to from ad
but then used folium.GeoJson to fillcolor

ad=crime_zip.reset_index()
ad=ad.rename(index=str, columns={0: "crimes"})


oz.choropleth(
 geo_data=data,
 name='choropleth',
 data=ad,
 columns=['Postcode','crimes'],
 key_on='feature.properties.POSTCODE',
 threshold_scale=numbers,
 fill_color='YlOrRd',
 fill_opacity=0.5,
 line_opacity=0.2,
 legend_name='Average Number of Crimes',
 reset=True,
 highlight=True
)
'''

#using folium.GeoJson to fill colour based on the colours from niram[postcode] which we defined earlier and to avoid keyerror we add the 

folium.GeoJson(
    data,
    style_function=lambda feature: {
        'fillColor': niram[feature['properties']['POSTCODE']] if             
        (feature['properties']['POSTCODE'] in crime_zip.index.values) else
        '#00ff00',
        'fillOpacity': 0.5,
        'color' : 'black',
        'weight' : 2,
        'dashArray' : '5, 5'
        }
    ).add_to(oz)
        
      

geojson = [{'type': data['type'], 'features': [f]} for f in data['features']]

#Got this idea from: https://github.com/python-visualization/folium/pull/376 
for gj in map(lambda gj: folium.GeoJson(gj), geojson):
    try:
        district = gj.data['features'][0]['properties']['district']
        crimess=str(round(gj.data['features'][0]['properties']['crime_avg'],2))
        props='District= '+district+ '; Avg no. of crimes= '+crimess
        gj.add_child(folium.Popup(str(props)))
        gj.add_to(oz)
    except KeyError:
        continue

#folium.LayerControl().add_to(oz)

colourmap=bcm.LinearColormap(['yellow','orange', 'red'],index=[1,1000,10000],vmin=0,vmax=24000)
colourmap.caption='Average No. of Crimes (2012-2016)'
oz.add_child(colourmap)
oz
oz.save('VIC_crimes1.html')
