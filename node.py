from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from wallet import Wallet
from blockchain import Blockchain

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def get_node_ui():
    return send_from_directory("ui", "node.html")


@app.route("/network", methods=["GET"])
def get_network_ui():
    return send_from_directory("ui", "network.html")


@app.route("/wallet", methods=["POST"])
def create_keys():
    wallet.create_keys()
    if wallet.save_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            "public_key": wallet.public_key,
            "private_key": wallet.private_key,
            "funds": blockchain.get_balance(),
        }
        return jsonify(response), 201
    response = {"message": "Saving the keys failed."}
    return jsonify(response), 500


@app.route("/wallet", methods=["GET"])
def load_keys():
    if wallet.load_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            "public_key": wallet.public_key,
            "private_key": wallet.private_key,
            "funds": blockchain.get_balance(),
        }
        return jsonify(response), 201
    else:
        response = {"message": "Loading the keys failed."}
        return jsonify(response), 500


@app.route("/balance", methods=["GET"])
def get_balance():
    balance = blockchain.get_balance()
    if balance is not None:
        response = {
            "message": "Fetched balance successfully.",
            "funds": balance,
        }
        return jsonify(response), 200
    else:
        response = {
            "message": "Loading response failed.",
            "wallet_set_up": wallet.public_key is not None,
        }
        return jsonify(response), 500


@app.route("/broadcast_block", methods=["POST"])
def broadcast_block():
    values = request.get_json()
    if not values:
        response = {"message": "No data found."}
        return jsonify(response), 400
    if "block" not in values:
        response = {"message": "Some data is missing."}
        return jsonify(response), 400
    block = values["block"]
    if block["index"] == blockchain.chain[-1].index + 1:
        if blockchain.add_block(block):
            response = {"message": "Block added."}
            return jsonify(response), 201
        else:
            response = {"message": "Block seems invalid."}
            return jsonify(response), 409
    elif block["index"] > blockchain.chain[-1].index:
        response = {
            "message": """Blockchain is different from local blockchain.
            Block not added."""
        }
        blockchain.resolve_conflicts = True
        return jsonify(response), 200
    else:
        response = {"message": "Blockchain is shorter. Block not added."}
        return jsonify(response), 409


@app.route("/broadcast_transaction", methods=["POST"])
def broadcast_transaction():
    values = request.get_json()
    if not values:
        response = {"message": "No data found."}
        return jsonify(response), 400
    required = ["sender", "receiver", "amount", "signature"]
    if not all(key in values for key in required):
        response = {"message": "No data found."}
        return jsonify(response), 400
    success = blockchain.add_transaction(
        values["receiver"],
        values["sender"],
        values["signature"],
        values["amount"],
        is_receiving=True,
    )
    if success:
        response = {
            "message": "Successfully added transaction.",
            "transaction": {
                "sender": values["sender"],
                "receiver": values["receiver"],
                "amount": values["amount"],
                "signature": values["amount"],
            },
        }
        return jsonify(response), 201
    response = {"message": "Creating a transaction failed."}
    return jsonify(response), 500


@app.route("/transaction", methods=["POST"])
def add_transaction():
    if wallet.public_key is None:
        response = {"message": "No wallet found."}
        return jsonify(response), 400
    values = request.get_json()
    if not values:
        response = {"message": "No data found."}
        return jsonify(response), 400
    required_fields = ["receiver", "amount"]
    if not all(field in values for field in required_fields):
        response = {"message": "Required data is missing."}
        return jsonify(response), 400
    receiver = values["receiver"]
    amount = values["amount"]
    signature = wallet.sign_transaction(wallet.public_key, receiver, amount)
    success = blockchain.add_transaction(
        receiver, wallet.public_key, signature, amount
    )
    if success:
        response = {
            "message": "Successfully added transaction.",
            "transaction": {
                "sender": wallet.public_key,
                "receiver": receiver,
                "amount": amount,
                "signature": signature,
            },
            "funds": blockchain.get_balance(),
        }
        return jsonify(response), 201
    response = {"message": "Creating a transaction failed."}
    return jsonify(response), 500


@app.route("/mine", methods=["POST"])
def mine():
    if blockchain.resolve_conflicts:
        response = {
            "message": "Resolve outstandng conflicts. Block not added."
        }
        return jsonify(response), 409
    block = blockchain.mine_block()
    if block is not None:
        dict_block = block.__dict__.copy()
        dict_block["transactions"] = [
            tx.__dict__ for tx in dict_block["transactions"]
        ]
        response = {
            "message": "Block successfully mined.",
            "block": dict_block,
            "funds": blockchain.get_balance(),
        }
        return jsonify(response), 201
    response = {
        "message": "Mining a block failed.",
        "wallet_set_up": wallet.public_key is not None,
    }
    return jsonify(response), 500


@app.route("/resolve_conflicts", methods=["POST"])
def resolve_conflicts():
    replaced = blockchain.resolve()
    if replaced:
        response = {"message": "Chain was replaced."}
    else:
        response = {"message": "Local chain kept."}
    return jsonify(response), 200


@app.route("/transactions", methods=["GET"])
def open_transactions():
    transactions = blockchain.get_open_transactions()
    dict_transactions = [tx.__dict__ for tx in transactions]
    return jsonify(dict_transactions), 200


@app.route("/chain", methods=["GET"])
def get_chain():
    chain = blockchain.chain
    dict_chain = [
        [tx.__dict__ for tx in block.__dict__.copy()["transactions"]]
        for block in chain
    ]
    return jsonify(dict_chain), 200


@app.route("/node", methods=["POST"])
def add_node():
    """Add node to the blockchain."""
    values = request.get_json()
    if not values:
        response = {"message": "No data attached."}
        return jsonify(response), 400
    if "node" not in values:
        response = {"message": "No no data found."}
        return jsonify(response), 400
    node = values.get("node")
    blockchain.add_peer_node(node)
    response = {
        "message": "Node added successfully.",
        "all_nodes": blockchain.get_peer_nodes(),
    }
    return jsonify(response), 201


@app.route("/node/<node_url>", methods=["DELETE"])
def remove_node(node_url):
    """Remove node from the blockchain."""
    if node_url in ("", None):
        response = {"message": "No node found."}
        return jsonify(response), 400
    blockchain.remove_peer_node(node_url)
    response = {
        "message": "Node removed.",
        "all_nodes": blockchain.get_peer_nodes(),
    }
    return jsonify(response), 200


@app.route("/nodes", methods=["GET"])
def get_node():
    """Get all nodes."""
    nodes = blockchain.get_peer_nodes()
    response = {"message": nodes}
    return jsonify(response), 200


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=5000)
    args = parser.parse_args()
    port = args.port
    wallet = Wallet(port)
    blockchain = Blockchain(wallet.public_key, port)
    app.run(port=port)
