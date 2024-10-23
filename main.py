from flask import Flask, request, jsonify
import os
import json
import requests  # Asegúrate de tener importado requests para las notificaciones
from dotenv import load_dotenv
from epaycosdk.epayco import Epayco

load_dotenv()

app = Flask(__name__)

# Instancia la clase Epayco con las credenciales de la cuenta
epayco = Epayco({
    'apiKey': os.getenv('PUBLIC_KEY'),
    'privateKey': os.getenv('PRIVATE_KEY'),
    'lenguage': 'ES',  # lenjuage de los mensajes
    'test': os.getenv('EPAYCO_TEST') == 'true'
})

# Método para crear un token de la tarjeta
def create_token(data):
    try:
        card_info = {
            "card[number]": data['card_number'],
            "card[exp_year]": data['exp_year'],
            "card[exp_month]": data['exp_month'],
            "card[cvc]": data['cvc'],
            "hasCvv": True  # hasCvv: validar código de seguridad en la transacción
        }
        token = epayco.token.create(card_info)
        return token
    except Exception as e:
        return {'error': str(e)}

# Método para crear un cliente
def create_customer(token, data):
    customer_info = {
        'name': data['name'],
        'last_name': data['last_name'],
        'email': data['email'],
        'phone': data['phone'],
        'default': True
    }
    customer_info['token_card'] = token

    try:
        customer = epayco.customer.create(customer_info)
        return customer
    except Exception as e:
        return {'error': str(e)}

# Método para procesar el pago
def process_payment(data, customer_id, token_card):
    try:
        payment_info = {
            'token_card': token_card,
            'customer_id': customer_id,
            'doc_type': 'CC',  # Incluye 'doc_type' aquí
            'doc_number': data['doc_number'],
            'name': data['name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'city': data['city'],
            'address': data['address'],
            'phone': data['phone'],
            'cell_phone': data['cell_phone'],
            'bill': data['bill'],
            'description': 'Pago de servicios',
            'value': data['value'],
            'tax': '0',
            'tax_base': data['value'],
            'currency': 'COP'
        }
        print(f"Payment Info: {json.dumps(payment_info, indent=4)}")  # Imprime los datos de la solicitud

        response = epayco.charge.create(payment_info)
        return response
    except Exception as e:
        return {'error': str(e)}

# Método para enviar notificación del pago
def send_payment_notification(data):
    try:
        notification_data = {
            "recipient": data['email'],  # Correo del usuario
            "username": data['name'],  # Nombre del usuario
            "amount": data['value'],  # Monto del pago
            "description": 'Pago recibido con éxito'
        }
        response = requests.post('http://localhost:5000/paymentNotification', json=notification_data)
        return response.json()
    except Exception as e:
        return {'error': str(e)}

# Endpoint para manejar todo el flujo de pago
@app.route('/process_payment', methods=['POST'])
def handle_process_payment():
    data = request.json

    # Crea el token de la tarjeta
    token_response = create_token(data)
    print("Token response", json.dumps(token_response))

    # Verificar si hubo error al crear el token
    if token_response["status"] is False:
        return jsonify(token_response), 500

    token_card = token_response['id']  # Extrae el id del token

    # Crear cliente
    customer_response = create_customer(token_card, data)
    print("Customer response", json.dumps(customer_response))

    # Verificar si hubo error al crear el cliente
    if 'error' in customer_response:
        return jsonify(customer_response), 500

    customer_id = customer_response['data']['customerId']

    # Procesar el pago
    payment_response = process_payment(data, customer_id, token_card)
    print("Payment response", json.dumps(payment_response))

    # Verificar si hubo error en el pago
    if 'error' in payment_response:
        return jsonify(payment_response), 500

    # Enviar notificación del pago
    notification_response = send_payment_notification(data)
    print("Notification response", json.dumps(notification_response))

    return jsonify(payment_response), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)
