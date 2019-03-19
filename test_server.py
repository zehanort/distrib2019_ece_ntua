from block import *
from wallet import *
from transaction import *
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

address = '127.0.0.1'
port = 5000

app = Flask(__name__)
CORS(app)

@app.route('/test/', methods=['POST'])
def test():
	print(request.get_json())
	print(request.json)
	t = Transaction(**request.json)
	print(t.to_dict())
	return 'got transaction', 200

app.run(host=address, port=port, threaded=True)