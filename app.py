from flask import Flask, request, send_file
import edge_tts
import asyncio
import tempfile
import os

app = Flask(__name__)

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
