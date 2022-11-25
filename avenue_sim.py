import agentpy as ap
import numpy as np
import random
import json

res_json = None
class Car(ap.Agent):
	def setup(self):
		self.direction = np.array([0, 0])  # x | y
		self.velocity = 0.0  # float
		self.max_velocity = 10.0
		self.my_traffic_lights = []
		self.has_car_ahead = False

	def put_traffic_lights(self):
		for traffic_light in self.model.traffic_lights:
			if np.array_equal(traffic_light.direction, self.direction):
				self.my_traffic_lights.append(traffic_light)

	def put_car_ahead(self):
		cars_around = []
		self.position = self.model.avenue.positions[self]
		min_dist = 999999
		for car in self.model.cars:
			if self.model.avenue.positions[car][0] == self.position[0]:
				if self.direction[1] == -1 and self.position[1] > self.model.avenue.positions[car][1]:
					cars_around.append(car)
				elif self.direction[1] == 1 and self.position[1] < self.model.avenue.positions[car][1]:
					cars_around.append(car)
		for car in cars_around:
			distance = abs(self.model.avenue.positions[car][1] - self.position[1])
			if distance < min_dist:
				min_dist = distance
				self.car_ahead = car
				self.has_car_ahead = True

	def update_position(self):
		self.model.avenue.move_by(self, np.multiply(self.direction, self.velocity))
		self.position = self.model.avenue.positions[self]
		reset_pos = False
		if not reset_pos:
			if self.direction[1] == -1 and self.position[1] > self.model.p.size - 20:
				self.put_car_ahead()
				reset_pos = True
			elif self.direction[1] == 1 and self.position[1] < 20:
				self.put_car_ahead()
				reset_pos = True

	def update_velocity(self):
		self.position = self.model.avenue.positions[self]
		stopped_by_car = False
		if self.has_car_ahead:
			car_ahead_pos = self.model.avenue.positions[self.car_ahead]
			distance = abs(car_ahead_pos[1] - self.position[1])
			if distance < self.model.p.car_gap * 3:
				stopped_by_car = True
				if self.velocity > 0:
					self.velocity -= 1.8
			else:
				if self.velocity < self.max_velocity:
					self.velocity += 0.5
		if not stopped_by_car:
			for traffic_light in self.my_traffic_lights:
				traffic_light_pos = self.model.avenue.positions[traffic_light]

				if self.direction[1] == -1:
					traffic_light_is_behind = self.position[1] > traffic_light_pos[1]
				elif self.direction[1] == 1:
					traffic_light_is_behind = self.position[1] < traffic_light_pos[1]

				distance = abs(traffic_light_pos[1] - self.position[1])
				if distance < self.p.traffic_lights_y_offset * 3.2 and traffic_light.state == 2 and traffic_light_is_behind and distance > self.p.traffic_lights_y_offset * 1.8:
					if self.velocity > 0:
						self.velocity -= 1
				elif distance < self.p.traffic_lights_y_offset * 3.2 and traffic_light.state == 1 and traffic_light_is_behind and distance > self.p.traffic_lights_y_offset * 1.8:
					if self.velocity > 0:
						self.velocity -= 0.5
				else:
					if self.velocity < self.max_velocity:
						self.velocity += 0.5
		if self.velocity < 0:
			self.velocity = 0

	def save_to_json(self):
		self.position = self.model.avenue.positions[self]
		data = self.model.data
		id = "c_" + str(self.id)
		data["steps"][self.model.t]["cars"].append({ "position": [self.position[0], self.position[1]] })

class Traffic_Light(ap.Agent):
	def setup(self):
		self.direction = np.array([0, 0])  # x | y
		self.state = 0  # 0: green | 1: yellow | 2: red
		self.green_duration = 0
		self.yellow_duration = 0
		self.red_duration = 0

	def update_state(self, t):
		if t < self.green_duration:
			self.state = 0
		elif t < self.green_duration + self.yellow_duration:
			self.state = 1
		else:
			self.state = 2

	def save_to_json(self):
		data = self.model.data
		id = "tl_" + str(self.id)
		data["steps"][self.model.t]["traffic_lights"].append({ "state": self.state })

class Model(ap.Model):
	def setup(self):
		## Archivo json
		self.data = { }
		self.data["steps"] = []

		# Init Space
		self.avenue = ap.Space(self, shape = (self.p.size, self.p.size), torus = True)

		# Init Agents
		self.cars = ap.AgentList(self, self.p.population, Car)
		self.traffic_lights = ap.AgentList(self, 2, Traffic_Light)

		# Set traffic lights duration on each state
		self.traffic_lights.green_duration = self.p.green_duration
		self.traffic_lights.yellow_duration = self.p.yellow_duration
		self.traffic_lights.red_duration = self.p.red_duration

		# This variable is used to change the traffic lights state
		self.traffic_lights_max_cycle = self.p.green_duration + self.p.yellow_duration + self.p.red_duration

		# Add agent to model
		self.avenue.add_agents(self.traffic_lights)
		self.avenue.add_agents(self.cars)

		## Set position of Traffic_Light
		self.avenue.move_to(self.traffic_lights[0],
		                    [self.p.size * 0.5 - (self.p.traffic_lights_x_offset * (self.p.road_lines / 2)),
		                     self.p.size * 0.5 - self.p.traffic_lights_y_offset]
		                    )
		self.avenue.move_to(self.traffic_lights[1],
		                    [self.p.size * 0.5 + (self.p.traffic_lights_x_offset * (self.p.road_lines / 2)),
		                     self.p.size * 0.5 + self.p.traffic_lights_y_offset]
		                    )

		## Set Traffic_Light direction
		self.traffic_lights[0].direction = np.array([0, -1])
		self.traffic_lights[1].direction = np.array([0, 1])

		## Set position of Car
		for i in range(len(self.cars)):
			car = self.cars[i]
			random_line = random.randint(0, self.p.road_lines - 1)
			# Right
			if (i % 2 == 0):
				car.direction = np.array([0, 1])
				self.avenue.move_by(car,
				                    [self.p.size * 0.5 + self.p.traffic_lights_x_offset + (
							                    random_line * self.p.car_gap),
				                     (i * self.p.car_gap)
				                     ]
				                    )
			# Left
			else:
				car.direction = np.array([0, -1])
				self.avenue.move_by(car,
				                    [self.p.size * 0.5 - self.p.traffic_lights_x_offset - (
							                    random_line * self.p.car_gap),
				                     self.p.size - (i * self.p.car_gap)
				                     ]
				                    )
		self.cars.put_traffic_lights()
		self.cars.put_car_ahead()

		self.save_to_json()

	def step(self):
		traffic_lights_cycle_t = self.t % self.traffic_lights_max_cycle
		self.traffic_lights.update_state(traffic_lights_cycle_t)
		self.cars.update_velocity()
		self.cars.update_position()

		self.save_to_json()

	def end(self):
		print("endl")
		self.res_json = json.dumps(self.data, indent = 2)

	def save_to_json(self):
		self.data["steps"].append({ })

		self.data["steps"][self.model.t]["cars"] = []
		self.cars.save_to_json()

		self.data["steps"][self.model.t]["traffic_lights"] = []
		self.traffic_lights.save_to_json()
