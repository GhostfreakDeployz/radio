from flask import Flask, render_template
import requests
import yt_dlp
import random
import os
import time
import pygame
import subprocess
from threading import Thread
from datetime import datetime, timedelta

app = Flask(__name__)

# Variáveis globais para controle do estado da rádio
is_radio_running = False

LASTFM_API_KEY = '9d7d79a952c5e5805a0decb0ccf1c9fd'
vinhetas = [
    "./static/vinhetas/vinheta_milenio.mp3",
    "./static/vinhetas/vinheta_rock.mp3",
    "./static/vinhetas/uma_hora.mp3"
]

@app.route('/')
def index():
    return render_template('index.html')  # Renderiza a página HTML inicial

# Função para buscar músicas populares de um estilo na API do Last.fm
def buscar_musicas_por_estilo(estilo):
    url = f'http://ws.audioscrobbler.com/2.0/?method=tag.gettoptracks&tag={estilo}&api_key={LASTFM_API_KEY}&format=json'
    response = requests.get(url)
    data = response.json()
    if 'tracks' in data:
        tracks = data['tracks']['track']
        return [(track['name'], track['artist']['name']) for track in tracks]
    else:
        print("Erro ao buscar músicas.")
        return []

# Função para baixar música do YouTube, verificando se já existe
def download_music(music_name, artist_name, result_container):
    sanitized_name = f"{artist_name} - {music_name}".replace("/", "_").replace("\\", "_").replace(":", "_")
    output_path = f"./musicas/{sanitized_name}.mp3"
    
    # Verifica se a música já está baixada
    if os.path.exists(output_path):
        print(f"Música '{output_path}' já existe, pulando download.")
        result_container["path"] = output_path
        return

    ydl_opts = {
        'quiet': True,
        'extract_audio': True,
        'format': 'bestaudio/best',
        'outtmpl': './musicas/%(title)s.%(ext)s',
        'noplaylist': True,
    }
    search_query = f"{music_name} {artist_name} official music video"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            search_results = ydl.extract_info(f"ytsearch:{search_query}", download=True)
            if 'entries' in search_results:
                music_entries = [entry for entry in search_results['entries'] if 'official music video' in entry['title'].lower()]
                if not music_entries:
                    music_entries = search_results['entries']
                if music_entries:
                    random_result = random.choice(music_entries)
                    video_url = f"https://www.youtube.com/watch?v={random_result['id']}"
                    ydl.download([video_url])
                    temp_file = f"./musicas/{random_result['title']}.webm"
                    # Converte para MP3
                    result_container["path"] = convert_to_mp3(temp_file)
            else:
                print("Nenhum resultado encontrado.")
                result_container["path"] = None
        except Exception as e:
            print(f"Erro ao baixar música: {e}")
            result_container["path"] = None

# Função para converter música para MP3
def convert_to_mp3(input_file):
    output_file = f"{os.path.splitext(input_file)[0]}.mp3"
    if os.path.exists(output_file):
        os.remove(output_file)
    subprocess.run(['ffmpeg', '-i', input_file, '-vn', '-acodec', 'libmp3lame', output_file])
    os.remove(input_file)
    return output_file

# Função para tocar música usando o pygame
def play_music(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# Função para tocar vinheta
def tocar_vinheta(vinheta_path):
    pygame.mixer.init()
    pygame.mixer.music.load(vinheta_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# Função para rodar a rádio com vinhetas entre as músicas
def rodar_programa(estilo, duracao):
    fim = datetime.now() + timedelta(minutes=duracao)
    while datetime.now() < fim:
        print(f"\nBuscando músicas de {estilo}...")
        musicas = buscar_musicas_por_estilo(estilo)
        if musicas:
            musica, artista = random.choice(musicas)
            print(f"Música escolhida: {musica} - {artista}")

            # Escolhe uma vinheta aleatória
            vinheta = random.choice(vinhetas)
            print(f"Tocando vinheta enquanto baixa a música '{musica}' de {artista}...")

            # Container para o resultado do download
            result_container = {"path": None}

            # Inicia o download em uma thread separada
            download_thread = Thread(target=download_music, args=(musica, artista, result_container))
            download_thread.start()

            # Reproduz a vinheta
            tocar_vinheta(vinheta)

            # Aguarda o término do download
            download_thread.join()

            # Verifica se o download foi concluído
            music_path = result_container["path"]
            if music_path:
                print(f"Música '{music_path}' pronta para tocar!")
                play_music(music_path)
            else:
                print(f"Erro ao baixar a música '{musica}' de {artista}.")
        else:
            print(f"Não foram encontradas músicas para o estilo {estilo}.")
        print("\nAguardando próxima música...")
        time.sleep(5)

# Função para rodar a rádio
def rodar_radio():
    cronograma = [
        {"estilo": "nu-metal", "duracao": 60},
        {"estilo": "grunge", "duracao": 60},
        {"estilo": "metalcore", "duracao": 60},
        {"estilo": "alt-rock", "duracao": 60},
        {"estilo": "indie rock", "duracao": 60},
        {"estilo": "brazilian rock", "duracao": 60},
    ]
    global is_radio_running
    while is_radio_running:
        for programa in cronograma:
            print(f"\nIniciando programa: {programa['estilo']} por {programa['duracao']} minutos.")
            rodar_programa(programa["estilo"], programa["duracao"])

# Rota para iniciar a rádio em uma thread separada
@app.route('/rodar_radio')
def rodar_radio_route():
    global is_radio_running
    if not is_radio_running:
        is_radio_running = True
        radio_thread = Thread(target=rodar_radio)  # Cria a thread para rodar a rádio
        radio_thread.start()  # Inicia a execução da rádio em segundo plano
        return "Rádio iniciada!", 200  # Retorna uma resposta para o navegador
    else:
        return "Rádio já está tocando!", 200  # Retorna uma resposta indicando que a rádio já está rodando

# Exemplo de uso
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)  # Inicia o servidor Flask
