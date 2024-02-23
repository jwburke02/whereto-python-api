from services.park import ParkAPI
from core import app, api

api.add_resource(ParkAPI, '/park')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7001, debug=True)

