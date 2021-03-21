import numpy as np
import heapq
import random
from statistics import mean
import matplotlib.pylab as plt

THINK = 4
REQ = 5
IDLE = 6
BUSY = 7
ARR = 1
DEP = 2
SWCH = 3
TMT = 8
Q_LENGTH = 1000000
QUANTUM = 0.010
SERVICE_TIME = 0.05
THINK_TIME = 6
TIMEOUT = 1
np.random.seed(42)


# %%

class Queue:
    def __init__(self, leng):
        self.len = leng
        self.que = np.empty(self.len, Request)
        self.front = -1
        self.rear = -1

    def display(self):
        if self.front == -1:
            print("Underflow")
            return
        else:
            i = self.front
            while i != self.rear:
                print("user:", self.que[i].user)
                i = (i + 1) % self.len
            print("user:", self.que[i].user)
            return

    def isFull(self):
        return True if ((self.rear + 1) % self.len == self.front) else False

    def isEmpty(self):
        return True if (self.front == -1) else False

    def enqueue(self, req):
        if (self.rear + 1) % self.len == self.front:
            print("Overflow")
            return False
        if self.rear == -1:
            self.front += 1
            self.rear += 1
        else:
            self.rear = (self.rear + 1) % self.len
        self.que[self.rear] = req
        return True

    def dequeue(self):
        if self.front == -1:
            print("Underflow")
            return False
        req = self.que[self.front]
        if self.rear == self.front:
            self.front = -1
            self.rear = -1
        else:
            self.front = (self.front + 1) % self.len
        return req


# %%

class Simulation:
    def __init__(self, num_users, count):
        self.clock = 0.0
        self.event_pq = []
        self.req_num = 0
        heapq.heapify(self.event_pq)

        self.que = Queue(Q_LENGTH)
        self.s = Server(4)
        self.no_of_users = num_users

        self.count = count
        self.waitt_list = []
        self.response_list = []
        self.timedout_list = []
        self.dropped_list = []
        self.req_dropped = 0
        self.req_timedout = 0
        self.user = [Users(i, self) for i in range(self.no_of_users)]

    def arrival_handler(self, event):
        if not (self.user[event.req.user].put_in_queue()):
            return False
        self.s.serve(self, event)

    def depart_handler(self, event):
        self.s.serve(self, event)

    def switch_handler(self, event):
        self.s.serve(self, event)

    def advance_time(self):
        while len(self.event_pq) != 0:
            print(f"Request #{self.req_num}")
            event = heapq.heappop(self.event_pq)
            self.clock = event.timestamp

            if event.e_type == ARR:
                self.arrival_handler(event)

            elif event.e_type == DEP:
                self.depart_handler(event)

            elif event.e_type == SWCH:
                self.switch_handler(event)

            elif event.e_type == TMT:
                print(f"req id of user")
                print(f"TMT Event : user {event.req.user}, req {event.req.id} {event.timestamp}")
                self.user[event.req.user].timeout_handler(event.req.id)

    def display(self):
        print("===================================================")
        print("Clock :", self.clock)
        for i in range(self.no_of_users):
            self.user[i].display()
        print("---------------Event queue-------------------------")
        for eve in self.event_pq:
            eve.display()
        self.s.display()
        print("---------------Job queue-------------------------")
        self.s.job_que.display()
        print("===================================================")


# %%

class Request:
    def __init__(self, req_id, user_id, t_req, tp_timeout, tp_service):
        self.id = req_id
        self.user = user_id
        self.t_req = t_req
        self.tp_timeout = tp_timeout
        self.tp_service = tp_service
        self.tp_wait = 0
        self.core_num = -1
        self.start_wait_t = t_req

    def add_to_wait(self, clock):
        self.tp_wait = (clock - self.start_wait_t)

    def assign_core(self, core_num):
        self.core_num = core_num

    def dec_time(self, sw_time):
        self.tp_service = self.tp_service - sw_time


# %%

class Users:
    def __init__(self, user_id, sim):
        self.req = None
        self.sim = sim
        self.id = user_id
        self.state = THINK
        self.t_req = 0
        self.tp_timeout = 0
        self.tp_service = 0
        self.generate_request()

    def display(self):
        print("User", self.id, ":-", "State:", self.state, "Request time :", self.t_req, "Service time :",
              self.tp_service)

    def generate_thinktime(self):
        #         return random.uniform(0,1)
        #         return random.triangular(0)
        return np.random.exponential(THINK_TIME)

    def generate_service(self):
        #         return random.uniform(3,9)
        return np.random.exponential(SERVICE_TIME)

    def generate_timeout(self):
        return TIMEOUT

    def generate_request(self):
        if self.sim.req_num < self.sim.count:
            self.t_req = self.sim.clock + self.generate_thinktime()
            self.tp_timeout = self.generate_timeout()
            self.tp_service = self.generate_service()

            self.sim.req_num += 1
            self.req = Request(self.sim.req_num, self.id, self.t_req, self.tp_timeout, self.tp_service)
            event = Event(ARR, self.req, self.t_req)
            timeout_event = Event(TMT, self.req, self.t_req + self.tp_timeout)
            heapq.heappush(self.sim.event_pq, event)
            heapq.heappush(self.sim.event_pq, timeout_event)
        else:
            self.req = Request(None, self.id, None, None, None)

    def put_in_queue(self):
        if not (self.sim.que.isFull()):
            self.sim.que.enqueue(self.req)
            self.req.start_wait_t = self.sim.clock
            self.state = REQ
            self.t_req = float('inf')
            return True
        else:
            self.sim.req_dropped += 1
            self.sim.dropped_list.append(self.req.id)
            self.generate_request()
            return False

    def request_finish(self, clock, f_req):
        if f_req.id == self.req.id:
            self.sim.response_list.append((clock - self.req.t_req))
            self.sim.waitt_list.append(self.req.tp_wait)
            self.state = THINK
            self.generate_request()

    def timeout_handler(self, req_id):
        print("inside timeout handler", req_id, self.req.id)
        if req_id == self.req.id:
            self.sim.timedout_list.append(self.req.id)
            self.sim.req_timedout += 1
            self.state = THINK
            self.generate_request()


# %%

class Event:
    def __init__(self, e_type, req, timestamp):
        self.e_type = e_type
        self.req = req
        self.timestamp = timestamp

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def display(self):
        print("Event type", self.e_type, "Timestamp:", self.timestamp, "Req of user:", self.req.user)


# %%

class Core:
    def __init__(self, core_id, sw_time):
        self.req = None
        self.core_id = core_id
        self.state = IDLE
        self.switch_time = sw_time

    def display(self):
        print("Core:", self.core_id, "Core state:", self.state)

    def as_request(self, req):
        self.req = req
        self.state = BUSY

    def n_event(self, tstmp):
        if self.switch_time < self.req.tp_service:
            return Event(SWCH, self.req, tstmp + self.switch_time)
        else:
            return Event(DEP, self.req, tstmp + self.req.tp_service)


# %%

class Server:
    def __init__(self, cores):
        self.state = IDLE
        self.no_of_cores = cores
        self.cores_list = [Core(i, QUANTUM) for i in range(self.no_of_cores)]
        self.job_que = Queue(15)
        self.n_reqs = 0
        self.max_reqs = 10

    def display(self):
        print("No of request in server:", self.n_reqs)
        print("No of cores:", len(self.cores_list))
        print("-----------Cores--------------------")
        for c in self.cores_list:
            c.display()

    def serve(self, sim, event):
        if event.e_type == DEP:
            print("------Serving DEP event------")
            sim.user[event.req.user].request_finish(sim.clock, event.req)
            self.n_reqs -= 1

            core = self.cores_list[event.req.core_num]
            if not (sim.que.isEmpty()):
                req = sim.que.dequeue()
                self.n_reqs += 1
                req.add_to_wait(sim.clock)
                self.job_que.enqueue(req)

            if self.job_que.isEmpty():
                core.state = IDLE
                print(f"Core {core.core_id} is idle.")
                return

            ass_req = self.job_que.dequeue()
            core.as_request(ass_req)
            ass_req.assign_core(core.core_id)

            n_event = core.n_event(sim.clock)
            heapq.heappush(sim.event_pq, n_event)
            return

        elif event.e_type == ARR:
            print("---Serving ARR event----")
            if self.n_reqs < self.max_reqs:
                req = sim.que.dequeue()
                self.n_reqs += 1
                req.add_to_wait(sim.clock)
                self.job_que.enqueue(req)
                if self.n_reqs <= self.no_of_cores:
                    for c in self.cores_list:
                        if c.state == IDLE:
                            print(f"Core {c.core_id} found idle.")
                            ass_req = self.job_que.dequeue()
                            c.as_request(ass_req)
                            ass_req.assign_core(c.core_id)

                            n_event = c.n_event(sim.clock)
                            heapq.heappush(sim.event_pq, n_event)
                            break
                else:
                    print("All cores busy.")
            return

        elif event.e_type == SWCH:
            #             print("---Serving SWITCH event----")
            core = self.cores_list[event.req.core_num]
            event.req.dec_time(core.switch_time)
            self.job_que.enqueue(event.req)

            ass_req = self.job_que.dequeue()
            core.as_request(ass_req)
            ass_req.assign_core(core.core_id)

            n_event = core.n_event(sim.clock)
            heapq.heappush(sim.event_pq, n_event)
            return


# %%



response_matrix = {}

for num_users in range(10, 1000, 10):
    num_req = num_users * 50
    sim = Simulation(num_users, num_req)
    sim.advance_time()
    avg_response = mean(sim.response_list)
    response_matrix[num_users] = avg_response
    print("avg_response =", avg_response)

print(response_matrix)

lists = sorted(response_matrix.items())

x, y = zip(*lists) # unpack a list of pairs into two tuples

plt.plot(x, y)
plt.show()
plt.savefig('response_time.png')
