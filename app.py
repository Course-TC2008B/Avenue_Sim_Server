import time

import avenue_sim
from flask import Flask, request

app = Flask(__name__)

parameters = {
    "size": 1000,
    "seed": 100,
    "steps": 400,
    "population": 36,  # Amount of cars in simulation
    "green_duration": 30,
    "yellow_duration": 20,
    "red_duration": 60,
    "traffic_lights_x_offset": 15,
    "traffic_lights_y_offset": 40,
    "car_velocity_counted_as_stopped": 0.55,
    # This is used for traffic lights to count a car as stopped (if current car velocity is lower than this value, it's stopped)
    "car_gap": 25,
    "road_lines": 2,
    "distance_to_stop_in_traffic_light": 100,
    "distance_to_skip_traffic_light": 40,
    "traffic_lights_evaluate_traffic": True,
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
	evaluate_traffic = request.args.get('evaluate_traffic')

	if seed is not None:
		parameters['seed'] = int(seed)

	if road_lines is not None:
		parameters['road_lines'] = int(road_lines)

	if population is not None:
		parameters['population'] = int(population)

	if evaluate_traffic is not None:
		parameters['evaluate_traffic'] = bool(evaluate_traffic)

	model = avenue_sim.Model(parameters)
	model.run()

	while True:
		if model.res_json != None:
			break

		time.sleep(1)

	return model.res_json

if __name__ == '__main__':
	app.run()
