import imageio_ffmpeg
import os
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

from flask import Flask, request, send_file
import edge_tts
import asyncio
import tempfile
import subprocess
import urllib.request

app = Flask(__name__)

@app.route('/')
def home():
    return 'TTS + FFmpeg server is running!'

@app.route('/tts', methods=['POST'])
def tts():
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'en-US-AriaNeural')

    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        output_path = f.name

    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    asyncio.run(generate())

    return send_file(output_path, mimetype='audio/mpeg', as_attachment=True, download_name='voiceover.mp3')

@app.route('/render', methods=['POST'])
def render():
    data = request.json
    video_urls = data.get('videos', [])
    text = data.get('text', '')
    voice = data.get('voice', 'en-US-AriaNeural')

    tmp_dir = tempfile.mkdtemp()

    # Generate audio with Edge TTS
    audio_path = os.path.join(tmp_dir, 'audio.mp3')

    async def generate_audio():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_path)

    asyncio.run(generate_audio())

    # Download video clips
    video_paths = []
    for i, v in enumerate(video_urls):
        vpath = os.path.join(tmp_dir, f'clip_{i}.mp4')
        urllib.request.urlretrieve(v['url'], vpath)
        video_paths.append(vpath)

    # Create concat list for FFmpeg
    list_path = os.path.join(tmp_dir, 'list.txt')
    with open(list_path, 'w') as f:
        for vp in video_paths:
            f.write(f"file '{vp}'\n")

    # Concatenate all video clips into one
    concat_path = os.path.join(tmp_dir, 'concat.mp4')
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', list_path,
        '-c', 'copy',
        concat_path
    ], check=True)

    # Merge concatenated video with audio
    output_path = os.path.join(tmp_dir, 'final.mp4')
    subprocess.run([
        'ffmpeg',
        '-i', concat_path,
        '-i', audio_path,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ], check=True)

    return send_file(output_path, mimetype='video/mp4', as_attachment=True, download_name='final.mp4')

if __name__ == '__main__':
    app.run()
