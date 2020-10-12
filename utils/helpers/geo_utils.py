import requests
import json
import pandas as pd
import numpy as np

def mapbox_geocode(place, secs):
    token = secs['mapbox_access_token']
    base_url = 'https://api.mapbox.com/geocoding/v5/mapbox.places'
    query = f"{base_url}/{place}.json?access_token={token}"

    r = requests.get(query)
    return json.loads(r.content)


def get_city_and_loc(mapbox_resp):
    text = np.nan
    lng = np.nan
    lat = np.nan
    country = np.nan
    if ('features' in mapbox_resp) and (len(mapbox_resp['features']) > 0):

        result = mapbox_resp['features'][0]
        text = result['text']
        lng = result['center'][0]
        lat = result['center'][1]
        if 'context' in result and len(result['context'])>0:
            country = result['context'][-1]['text']

    return pd.Series({'city': text,
                      'lng': lng,
                      'lat': lat,
                      'country': country})

