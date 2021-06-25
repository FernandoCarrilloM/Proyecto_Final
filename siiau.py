import datetime
import hashlib
import json
from flask import Flask, jsonify, request, render_template, url_for
import requests
from uuid import uuid4
from urllib.parse import urlparse

from werkzeug.utils import redirect


class Blockchain:
    def __init__(self):
        self.chain = []
        self.materias = []
        self.create_block(proof=1, previous_hash='0', codigo='0', nombre='-', semestre='0')
        self.nodes = set()
        self.codigo = ''
        self.nombre = ''
        self.semestre = ''

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json(['length'])
                chain = response.json(['chain'])

                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain

            if longest_chain:
                self.chain = longest_chain
                return True
            return False

    def create_block(self, proof, previous_hash, codigo, nombre, semestre):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'materias': self.materias,
                 'codigo': codigo,
                 'nombre': nombre,
                 'semestre': semestre}
        self.materias = []
        self.chain.append(block)
        return block

    def add_materias(self, nombre, nrc, clave, seccion, dias, horas, edificio, aula, maestro):
        self.materias.append({'nombre': nombre,
                              'nrc': nrc,
                              'clave': clave,
                              'seccion': seccion,
                              'dias': dias,
                              'horas': horas,
                              'edificio': edificio,
                              'aula': aula,
                              'maestro': maestro})

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True

    def registro_previo(self, codigo):
        index = 1
        while index < len(self.chain):
            block = self.chain[index]
            if block['codigo'] == codigo:
                return False
        return True


app = Flask(__name__)

node_address = str(uuid4()).replace('-', '')

blockchain = Blockchain()


@app.route('/mine_block')
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    codigo = blockchain.codigo
    nombre = blockchain.nombre
    semestre = blockchain.semestre
    blockchain.create_block(proof, previous_hash, codigo, nombre, semestre)
    # response = {'message': 'Se ha realizado su registro de materias',
    # 'index': block['index'],
    # 'timestamp': block['timestamp'],
    # 'proof': block['proof'],
    # 'previous_hash': block['previous_hash'],
    # 'materias': block['materias'],
    #  'codigo': block['codigo'],
    #  'nombre': block['nombre'],
    #  'semestre': block['semestre']}
    return redirect(url_for('home'))


@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200


@app.route('/is_valid', methods=['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'Todo va bien'}
    else:
        response = {'message': 'Todo lo que pudo salir mal, salió mal'}

    return jsonify(response), 200


@app.route('/add_materias', methods=['GET', 'POST'])
def add_materias():
    if request.method == 'POST':
        nombre = request.form['materia']
        nrc = request.form['nrc']
        clave = request.form['clave']
        seccion = request.form['seccion']
        dias = request.form['dias']
        horas = request.form['horas']
        edificio = request.form['edificio']
        aula = request.form['aula']
        maestro = request.form['maestro']
        blockchain.add_materias(nombre, nrc, clave, seccion, dias, horas, edificio, aula, maestro)

        response = {'message': 'La materia ha sido agregada'}
        return render_template('Materias.html')


@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return 'No node', 401
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'Todos los nodos estan conectados. Franciiau contiene los nodos:',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201


@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'Los nodos tenian diferentes cadenas, por lo que sa cambio a la mas larga',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'Todo bien, la cadena es la mas larga',
                    'actual_chain': blockchain.chain}
    return jsonify(response), 200


@app.route('/home')
def home():
    blockchain.replace_chain()
    return render_template('index.html')


@app.route('/')
def root():
    return redirect(url_for('home'))


@app.route('/Registro_materias')
def registro_materias():
    return render_template('Materias.html')


@app.route('/Registro_usuario')
def registro_usuarios():
    return render_template('Usuarios.html')


@app.route('/validacion', methods=['POST'])
def validar_usuario():
    blockchain.codigo = ''
    blockchain.nombre = ''
    blockchain.semestre = ''

    codigo = request.form['codigo']
    nombre = request.form['nombre']
    semestre = request.form['semestre']

    blockchain.codigo = codigo
    blockchain.nombre = nombre
    blockchain.semestre = semestre

    return render_template('Materias.html')
    '''if blockchain.registro_previo(codigo):

        
    else:
        return '<h1> Hola <h1>'
'''


@app.route('/hola')
def hola():
    return render_template('Materias.html')


app.run(host='0.0.0.0', port='5000')
