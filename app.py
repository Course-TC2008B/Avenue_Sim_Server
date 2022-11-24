import time

from flask import Flask, request
import avenue_sim

app = Flask(__name__)

parameters = {
	"size": 1000,
	"steps": 500,
	"population": 10,
	"green_duration": 20,
	"yellow_duration": 10,
	"red_duration": 60,
	"traffic_lights_x_offset": 50,
	"traffic_lights_y_offset": 70,
	"car_gap": 20,
	"road_lines": 1,
	}

@app.route('/')
def home():
	return 'Hello World!'

# request example http://127.0.0.1:5000/run?seed=100&road_lines=2&population=20
@app.route('/run')
def run_sim():  # put application's code here
	seed = request.args.get('seed')
	road_lines = request.args.get('road_lines')
	population = request.args.get('population')

	if seed is not None:
		parameters['seed'] = int(seed)

	if road_lines is not None:
		parameters['road_lines'] = int(road_lines)

	if population is not None:
		parameters['population'] = int(population)

	model = avenue_sim.Model(parameters)
	model.run()

	while True:
		if model.res_json != None:
			break

		time.sleep(1)

	return model.res_json

if __name__ == '__main__':
	app.run()
