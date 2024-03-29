from ParkAPI import ParkAPI
from DetailAPI import DetailAPI
from core import app, api

api.add_resource(ParkAPI, '/park')
api.add_resource(DetailAPI, '/detail')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7001, debug=True)

