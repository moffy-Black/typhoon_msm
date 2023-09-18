from datetime import datetime,timedelta
import requests
import math
import xarray as xr

from firebase import DB

def generate_url(date):
    date_str = date.strftime("%Y%m%d")
    url = f"http://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/latest/{date_str}/MSM{date_str}15S.nc"
    return url

def get_netcdf(url):
    response = requests.get(url)
    if response.status_code == 200:
        ds = xr.open_dataset(response.content)
        return ds
    else:
        return None

def get_event_by_date(date_str):
    try:
        event_subcollection_ref = DB.collection_group(date_str)
        docs = event_subcollection_ref.get()
        return True, docs
    except Exception as e:
        return False, e

def extract_rainfall_windspeed(ds,lon,lat):
    rainfall1h = ds.r1h.sel(lon=lon, lat=lat, method='nearest')[9:].values.tolist()
    eastward_wind = ds.u.sel(lon=lon, lat=lat, method='nearest')[9:].values.tolist()
    northward_wind = ds.v.sel(lon=lon, lat=lat, method='nearest')[9:].values.tolist()
    windspeed1h = [math.sqrt(u**2+v**2) for u,v in zip(eastward_wind,northward_wind)]
    return rainfall1h,windspeed1h

def set_rainfall_windspeed(docs,ds):
    for doc in docs:
        doc_data = doc.to_dict();path = doc.reference.path;event_ref = DB.document(path)
        event_type = doc_data.get('eventtype')
        event_location =  doc_data.get('location')
        event_longitude = event_location.longitude;event_latitude = event_location.latitude
        _rainfall1h,_windspeed1h = extract_rainfall_windspeed(ds,event_longitude,event_latitude)
        event_ref.set({"rainfall1h":_rainfall1h,"windspeed1h":_windspeed1h},merge=True)


if __name__ == "__main__":
    utc_now = datetime.utcnow();jst_offset = timedelta(hours=9);jst_now = utc_now + jst_offset
    target_date = jst_now - timedelta(days=1)
    print(jst_now.strftime("%Y-%m-%d %H:%M:%S"))
    url = generate_url(target_date)
    ds = get_netcdf(url)
    if ds is None:
        print("Not Found NetCDF file on website.")
    else:
        get_flag, docs = get_event_by_date(jst_now.strftime("%Y-%m-%d"))
        if get_flag:
            set_rainfall_windspeed(docs,ds)
        else:
            print(docs)