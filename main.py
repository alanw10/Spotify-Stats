import requests
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, session, render_template  # Add this line for importing render_template
import json


app = Flask(__name__)
app.secret_key = '' # Set this yourself!

CLIENT_ID = '' #Get from Spotify API
CLIENT_SECRET = 'f7a36fba12ce4b8d992e98524aa3cd30' #Get from Spotify API
REDIRECT_URI = 'http://127.0.0.1:5000/callback' #Match your Spotify App's URI

AUTH_URL = 'https://accounts.spotify.com/authorize' 
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

@app.route('/')
def index():
   
    access_token = session.get('access_token')

    return render_template('home.html', access_token=access_token)


@app.route('/login')
def login():
    scope = 'user-read-private user-read-email user-read-recently-played user-top-read'

    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.clear()  
        return redirect('/')
    else:
        
        return render_template('home.html')  

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        return redirect('/stats')  



@app.route('/stats')
def default_stats():
    
    return redirect('/stats/long_term')

@app.route('/stats/<time_range>')
def options(time_range):
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    try:
        
        response_tracks = requests.get(API_BASE_URL + 'me/top/tracks', headers=headers, params={'limit': 50, 'time_range': time_range})
        response_tracks.raise_for_status()
        track_data = response_tracks.json().get('items', [])

        
        track_names = [item['name'] for item in track_data]
        track_artists = [', '.join(artist['name'] for artist in item['artists']) for item in track_data]
        track_ids = [item['id'] for item in track_data]
        album_images = [item['album']['images'][0]['url'] for item in track_data]

        
        response_artists = requests.get(API_BASE_URL + 'me/top/artists', headers=headers, params={'limit': 50, 'time_range': time_range})
        response_artists.raise_for_status()
        artists_data = response_artists.json().get('items', [])
        artist_names = [item['name'] for item in artists_data]
        artist_ids = [item['id'] for item in artists_data]
        artist_images = [item['images'][0]['url'] for item in artists_data]

        
        zipped_tracks = zip(track_names, track_artists, track_ids, album_images)
        zipped_artists = zip(artist_names, artist_ids, artist_images)

        return render_template('stats.html', zipped_tracks=zipped_tracks, zipped_artists=zipped_artists, time_range=time_range)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return jsonify({"error": f"Error fetching data: {e}"})





@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/topartists')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
