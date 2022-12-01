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
        self.reset_pos = False
        self.prev_pos = []
        self.is_first_car = False

    def put_traffic_lights(self):
        for traffic_light in self.model.traffic_lights:
            if np.array_equal(traffic_light.direction, self.direction):
                self.my_traffic_lights.append(traffic_light)

    def put_car_ahead(self):
        cars_around = []
        self.position = self.model.avenue.positions[self]
        min_dist = 999999

        for car in self.model.cars:
            if car == self:
                continue

            # Car is going left or right
            if self.direction[0] != 0:
                # Check if car is in the same y position (get cars on left and right)
                if self.model.avenue.positions[car][1] == self.position[1]:
                    # Going left
                    if self.direction[0] == -1:
                        if self.model.avenue.positions[car][0] < self.position[0]:
                            cars_around.append(car)
                    # Going Right
                    elif self.direction[0] == 1:
                        if self.model.avenue.positions[car][0] > self.position[0]:
                            cars_around.append(car)
            else:
                # Check if car is in the same x position (get cars in front and back)
                if self.model.avenue.positions[car][0] == self.position[0]:
                    # Going down
                    if self.direction[1] == -1:
                        if self.model.avenue.positions[car][1] < self.position[1]:
                            cars_around.append(car)
                    # Going up
                    elif self.direction[1] == 1:
                        if self.model.avenue.positions[car][1] > self.position[1]:
                            cars_around.append(car)

        for car in cars_around:
            # Car is going left or right
            if self.direction[0] != 0:
                distance = abs(self.model.avenue.positions[car][0] - self.position[0])
            else:
                distance = abs(self.model.avenue.positions[car][1] - self.position[1])

            if distance < min_dist:
                min_dist = distance
                self.car_ahead = car
                self.has_car_ahead = True

    def update_position(self):
        self.model.avenue.move_by(self, np.multiply(self.direction, self.velocity))
        self.position = self.model.avenue.positions[self]

        if len(self.prev_pos) == 2:
            if abs(self.prev_pos[0] - self.position[0]) > 0.5 * self.p.size or abs(
                    self.prev_pos[1] - self.position[1]) > 0.5 * self.p.size:
                self.reset_pos = False

        if not self.reset_pos:
            if self.direction[0] == -1 and self.position[0] > self.model.p.size - 100:
                self.put_car_ahead()
                self.reset_pos = True
            elif self.direction[0] == 1 and self.position[0] < 100:
                self.put_car_ahead()
                self.reset_pos = True
            elif self.direction[1] == -1 and self.position[1] > self.model.p.size - 100:
                self.put_car_ahead()
                self.reset_pos = True
            elif self.direction[1] == 1 and self.position[1] < 100:
                self.put_car_ahead()
                self.reset_pos = True

    def update_velocity(self):
        self.position = self.model.avenue.positions[self]
        stopped_by_car = False
        stopped_by_traffic_light = False
        if self.has_car_ahead:

            car_ahead_pos = self.model.avenue.positions[self.car_ahead]

            if self.direction[0] != 0:
                distance = abs(car_ahead_pos[0] - self.position[0])
            else:
                distance = abs(car_ahead_pos[1] - self.position[1])

            if distance < self.model.p.car_gap :
                stopped_by_car = True
                if self.velocity > 0:
                    self.velocity -= 4
            elif distance < self.model.p.car_gap * 3:
                stopped_by_car = True
                if self.velocity > 0:
                    self.velocity -= 2

        if not stopped_by_car:
            for traffic_light in self.my_traffic_lights:

                if not traffic_light.is_car_inside_stop_range(self):
                    continue

                traffic_light_pos = self.model.avenue.positions[traffic_light]
                if self.direction[0] == -1:
                    traffic_light_is_behind = not (self.position[0] > traffic_light_pos[0])
                elif self.direction[0] == 1:
                    traffic_light_is_behind = not (self.position[0] < traffic_light_pos[0])
                elif self.direction[1] == -1:
                    traffic_light_is_behind = not (self.position[1] > traffic_light_pos[1])
                elif self.direction[1] == 1:
                    traffic_light_is_behind = not (self.position[1] < traffic_light_pos[1])

                # if traffic light is behind, ignore conditionals
                if not traffic_light_is_behind:

                    # Red
                    if traffic_light.state == 2:
                        stopped_by_traffic_light = True
                        if self.velocity > 0:
                            self.velocity -= 1.5

                    # Yellow
                    elif traffic_light.state == 1:
                        stopped_by_traffic_light = True
                        if self.velocity > 0:
                            self.velocity -= 1

        if self.velocity < self.max_velocity and not stopped_by_traffic_light and not stopped_by_car:
            self.velocity += 0.5

        if self.velocity < 0:
            self.velocity = 0

    def set_prev_pos(self):
        self.prev_position = self.model.avenue.positions[self]

    def save_to_json(self):
        self.position = self.model.avenue.positions[self]
        data = self.model.data
        data["steps"][self.model.t]["cars"].append({"position": [self.position[0], self.position[1]]})

class Traffic_Light(ap.Agent):
    def setup(self):
        self.direction = np.array([0, 0])  # x | y
        self.state = 2  # 0: green | 1: yellow | 2: red
        self.time_offset = 0
        self.local_timer = 0
        self.green_duration = 0
        self.yellow_duration = 0
        self.red_duration = 0

    def is_car_inside_stop_range(self, car):
        car_position = self.model.avenue.positions[car]
        traffic_light_position = self.model.avenue.positions[self]
        distance_vector = [abs(car_position[0] - traffic_light_position[0]),
                           abs(car_position[1] - traffic_light_position[1])]

        if car.direction[0] != 0:
            return self.model.p.distance_to_skip_traffic_light < distance_vector[0] < self.model.p.distance_to_stop_in_traffic_light
        elif car.direction[1] != 0:
            return self.model.p.distance_to_skip_traffic_light < distance_vector[1] < self.model.p.distance_to_stop_in_traffic_light

    def update_state(self, t):

        if not self.model.p.traffic_lights_evaluate_traffic:
            t += self.time_offset
            t = t % (self.green_duration + self.yellow_duration + self.red_duration)

            if t < self.green_duration:
                self.state = 0
            elif t < self.green_duration + self.yellow_duration:
                self.state = 1
            else:
                self.state = 2
        elif self.model.p.traffic_lights_evaluate_traffic and self.state != 2:
            self.local_timer += 1

            if self.green_duration + self.yellow_duration < self.local_timer:
                self.local_timer = 0
                self.state = 2
            elif self.green_duration < self.local_timer:
                self.state = 1

    def count_stopped_cars(self, debug=False):
        count_of_stopped_cars = 0
        traffic_light_position = self.model.avenue.positions[self]

        for car in self.model.cars:

            # If car does not have same direction as traffic_light, continue
            if not np.array_equal(self.direction, car.direction):
                continue

            #Check if car is almost stopped, if not, continue
            if car.velocity > self.model.p.car_velocity_counted_as_stopped:
                continue

            # Traffic light manages a vertical flow (y axis)
            if self.direction[0] == 0:
                # Check if car has same direction axis, if not, continue
                if car.direction[1] == 0:
                    continue

                # If traffic light direction is -1 (controls cars going down)
                if self.direction[1] == -1:
                    # Check if car is above
                    if car.position[1] > traffic_light_position[1]:
                        count_of_stopped_cars += 1
                # If traffic light direction is 1 (controls cars going up)
                else:
                    # Check if car is below
                    if car.position[1] < traffic_light_position[1]:
                        count_of_stopped_cars += 1
            # Traffic light manages a horizontal flow (x axis)
            else:
                # Check if car has same direction axis, if not, continue
                if car.direction[0] == 0:
                    continue

                # If traffic light direction is -1 (controls cars going left)
                if self.direction[0] == -1:
                    # Check if car is after
                    if car.position[0] > traffic_light_position[0]:
                        count_of_stopped_cars += 1
                # If traffic light direction is 1 (controls cars going right)
                else:
                    # Check if car is before
                    if car.position[0] < traffic_light_position[0]:
                        count_of_stopped_cars += 1

        if debug and count_of_stopped_cars > 0:
            print("Frame: " + str(self.model.t) + "  |  Traffic light " + str(self.id) + " with direction " + str(
                self.direction[0]) + " | " + str(self.direction[1]) + " has " + str(
                count_of_stopped_cars) + " stopped cars")

        return count_of_stopped_cars

    def save_to_json(self):
        data = self.model.data
        data["steps"][self.model.t]["traffic_lights"].append({"state": self.state})

class Model(ap.Model):
    # direction: 0 - Horizontal  1 - Vertical  2 - Random
    def enable_line_of_traffic_lights(self, direction, debug=False):
        if direction == 2:
            direction = random.randint(0, 1)

        for traffic_light in self.traffic_lights:
            if direction == 0 and traffic_light.direction[0] != 0:
                traffic_light.state = 0
            elif direction == 1 and traffic_light.direction[1] != 0:
                traffic_light.state = 0

        if debug:
            print("Step: " + str(self.model.t) + " direction " + str(direction) + " won")

    def evaluate_traffic_lights(self, debug=False):
        all_traffic_lights_are_red = True
        for traffic_light in self.traffic_lights:
            if traffic_light.state != 2:
                all_traffic_lights_are_red = False

        if all_traffic_lights_are_red:
            left_right_sum = self.traffic_lights[0].count_stopped_cars() + self.traffic_lights[
                1].count_stopped_cars()
            up_down_sum = self.traffic_lights[2].count_stopped_cars() + self.traffic_lights[3].count_stopped_cars(
            )

            if left_right_sum + up_down_sum > 0:
                if debug:
                    print("Step: " + str(self.model.t) + " total cars stopped in left-right: " + str(
                        left_right_sum) + "\n total cars stopped in up-down: " + str(up_down_sum))

                if left_right_sum > up_down_sum:
                    self.enable_line_of_traffic_lights(0)  # Horizontal
                elif up_down_sum > left_right_sum:
                    self.enable_line_of_traffic_lights(1)  # Vertical
                else:
                    self.enable_line_of_traffic_lights(2)  # Random

    def setup(self):
        ## Archivo json
        self.data = {}
        self.data["steps"] = []

        # Init Space
        self.avenue = ap.Space(self, shape=(self.p.size, self.p.size), torus=True)

        # Init Agents
        self.cars = ap.AgentList(self, self.p.population, Car)
        self.traffic_lights = ap.AgentList(self, 4, Traffic_Light)

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
        # down-left
        self.avenue.move_to(self.traffic_lights[0],
                            [self.avenue.shape[0] * 0.5 - (self.p.traffic_lights_x_offset),
                             # * (self.p.road_lines / 2)),
                             self.avenue.shape[1] * 0.5 - self.p.traffic_lights_y_offset])
        # up-right
        self.avenue.move_to(self.traffic_lights[1],
                            [self.p.size * 0.5 + (self.p.traffic_lights_x_offset),  # * (self.p.road_lines / 2)),
                             self.p.size * 0.5 + self.p.traffic_lights_y_offset])
        # down-right
        self.avenue.move_to(self.traffic_lights[2],
                            [self.p.size * 0.5 + (self.p.traffic_lights_x_offset),
                             self.p.size * 0.5 - (self.p.traffic_lights_y_offset)])  # * (self.p.road_lines / 2))])
        # up-left
        self.avenue.move_to(self.traffic_lights[3],
                            [self.p.size * 0.5 - (self.p.traffic_lights_x_offset),
                             self.p.size * 0.5 + (self.p.traffic_lights_y_offset)])  # * (self.p.road_lines / 2))])

        ## Set Traffic_Light direction
        self.traffic_lights[0].direction = np.array([1, 0])
        self.traffic_lights[1].direction = np.array([-1, 0])
        self.traffic_lights[2].direction = np.array([0, 1])
        self.traffic_lights[3].direction = np.array([0, -1])

        if not self.p.traffic_lights_evaluate_traffic:
            # Offset traffic_lights
            self.traffic_lights[0].time_offset = self.p.green_duration + self.p.yellow_duration
            self.traffic_lights[1].time_offset = self.p.green_duration + self.p.yellow_duration

        ## Set position of Car
        for i in range(len(self.cars)):
            index = i % 4
            car = self.cars[i]
            random_line = random.randint(0, self.p.road_lines - 1)
            # Top-Down
            if (index == 0):
                car.direction = np.array([0, 1])
                self.avenue.move_by(car, [
                    self.p.size * 0.5 + self.p.traffic_lights_x_offset + (random_line * self.p.car_gap),
                    (i * (self.p.car_gap / 2))
                ]
                                    )
            # Down-Top
            elif (index == 1):
                car.direction = np.array([0, -1])
                self.avenue.move_by(car, [
                    self.p.size * 0.5 - self.p.traffic_lights_x_offset - (random_line * self.p.car_gap),
                    self.p.size - (i * (self.p.car_gap / 2))
                ]
                                    )
            # Right-Left
            elif (index == 2):
                car.direction = np.array([-1, 0])
                self.avenue.move_by(car, [self.p.size - (i * (self.p.car_gap / 2)),
                                          self.p.size * 0.5 + self.p.traffic_lights_y_offset - (
                                                  random_line * self.p.car_gap)
                                          ]
                                    )

            # Left-Right
            elif (index == 3):
                car.direction = np.array([1, 0])
                self.avenue.move_by(car, [(i * (self.p.car_gap / 2)),
                                          self.p.size * 0.5 - self.p.traffic_lights_y_offset + (
                                                  random_line * self.p.car_gap)
                                          ]
                                    )

        self.cars.put_traffic_lights()
        self.cars.put_car_ahead()

        self.save_to_json()

    def step(self):
        self.cars.set_prev_pos()
        self.traffic_lights.update_state(self.t)

        self.cars.update_velocity()
        self.cars.update_position()

        if self.p.traffic_lights_evaluate_traffic:
            self.evaluate_traffic_lights()

        self.save_to_json()

    def end(self):
        print("endl")
        self.res_json = json.dumps(self.data, indent = 2)

    def save_to_json(self):
        self.data["steps"].append({})

        self.data["steps"][self.model.t]["cars"] = []
        self.cars.save_to_json()

        self.data["steps"][self.model.t]["traffic_lights"] = []
        self.traffic_lights.save_to_json()
