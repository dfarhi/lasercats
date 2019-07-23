import numpy as np
from collections import Counter
import os

ANSWER = "LIVIDFELID"
WORKING_GRIDS = [[] for _ in ANSWER]

MAX_PATH_LEN = 50

NORTH = np.array((0, -1))
SOUTH = np.array((0, 1))
EAST = np.array((1, 0))
WEST = np.array((-1, 0))
directions = [NORTH, EAST, SOUTH, WEST]
def dir_array_to_idx(dir_array):
    return [np.all(dir == dir_array) for dir in directions].index(True)

# np.random.seed(10)

OUTPUT_DIR = "/Users/dfarhi/Desktop/LaserCats"

class HEURISTC():
    SAME_SIDE_2 = 2
    SAME_SIDE_3 = 1 # 2 options for 3.
    SAME_SIDE_4_CENTER = 3 # guarantees 2, 2 choices for 2.
    SAME_SIDE_4_EDGE = 0.5 # 3 options for 4
    TURNED_3 = 3
    TURNED_4_CENTER = 2 # guarantees 1, 2 options for 3.
    TURNED_4_EDGE = 0.5 # 3 options for 4.
    TURNED_FAR_5 = 1.5 # guarantees 1, 3 options for 3
    BACK_5 = 5
    BACK_6_CENTER = 4 # guarantees 3, 2 options for 3 more.
    BACK_6_EDGE = 1 # guarantees 1, 4 options for 5.

class Terrain():
    FLAT = 0
    UL = 1
    UR = 2
    HUMAN = 3

    @staticmethod
    def display_string(terrain):
        if terrain == Terrain.FLAT: return "."
        if terrain == Terrain.UL: return "\\"
        if terrain == Terrain.UR: return "/"
        if terrain == Terrain.HUMAN: return "H"
        raise ValueError("Invalid Terrain {}".format(terrain))

class Grid():
    def __init__(self, size=5, mirror_prob=0.6):
        self.size = size
        self.array = np.array(
            [[Grid._new_cell(mirror_prob)
            for _ in range(size)] for _ in range(size)]
        )
        midpt = int((self.size - 1) / 2)
        self.human_location = (midpt, midpt)
        self.array[(midpt, midpt)] = Terrain.HUMAN

        self.start_array = np.array(self.array)

        self.paths = []
        self.next_direction_dx = 0
        self.visited_locs = np.zeros(shape=(self.size, self.size), dtype=np.bool)
        self.possible_extractions = [] # tuple of path index, path length, answer index
        self.breakin_heuristic_grid = np.zeros(shape=(self.size, self.size), dtype=np.bool)

    @classmethod
    def _new_cell(self, mirror_prob):
        if np.random.random() > mirror_prob:
            return Terrain.FLAT
        else:
            return np.random.choice((Terrain.UL, Terrain.UR))

    def display(self):
        print ("+" + "-"*self.size + "+")
        for i in range(self.size):
            terrain_strs = [Terrain.display_string(self.array[j, i]) for j in range(self.size)]
            print("|" + "".join(terrain_strs) + "|")
        print ("+" + "-"*self.size + "+")

    def location_inside(self, location):
        assert len(location) == 2
        return 0 <= location[0] < self.size and 0 <= location[1] < self.size

    def flip_mirror(self, location):
        assert self.array[location] in (Terrain.UL, Terrain.UR)
        self.array[location] = Terrain.UL if self.array[location] == Terrain.UR else Terrain.UR

    def launch_laser(self):
        direction = directions[self.next_direction_dx]
        path = Path(self, direction)
        path.run()
        self.paths.append(path)
        self.next_direction_dx += 1
        self.next_direction_dx = self.next_direction_dx % len(directions)
        return path

    @property
    def all_sites_visited(self):
        return np.all(self.visited_locs)

    def launch_lotsa_lasers(self, max_lasers, only_extract_after_all_visited=True):
        short_paths_score = 0
        for i in range(max_lasers):
            possible_extract = self.all_sites_visited
            path = self.launch_laser()
            short_paths_score += path.short_path_score

            if not path.all_locations_already_visited: continue
            if path.heuristic_breakin_score < 6: continue
            if only_extract_after_all_visited and not possible_extract: continue

            path_idx = len(self.paths)
            letter = chr(len(path) + 64)
            end_location = path.cursor_location
            if end_location[1] == -1:
                answer_idx = end_location[0]
            elif end_location[1] == 5:
                answer_idx = end_location[0] + 5
            else:
                # Path ended due to horizontal wall. Forget about it.
                continue
            if ANSWER[answer_idx] == letter:
                print("Made a path of difficulty {} which would put a {} at position {}".format(path.heuristic_breakin_score, letter, answer_idx))
                WORKING_GRIDS[answer_idx].append((self, path_idx))
                self.dump_puzzle(answer_idx)

    def pretty_print_puzzle(self, path_idx):
        for i in range(path_idx):
            print(self.paths[i].pretty_print_puzzle())
            print()

    def dump_puzzle(self, answer_idx):
        name = "-".join([str(len(p)) for p in self.paths[:-1]]) + '.txt'
        name = f"H={self.paths[-1].heuristic_breakin_score}-" + name
        with open(os.path.join(OUTPUT_DIR, str(answer_idx), name), 'w') as f:
            for path in self.paths[:-1]:
                f.write(path.pretty_print_puzzle())
                f.write("\n")


def ending_side(end_location):
    if end_location[0] == -1: return 3 # West
    if end_location[1] == -1: return 0 # North
    if end_location[0] == 5: return 1 # East
    if end_location[1] == 5: return 2 # South

class Path():
    def __init__(self, grid, start_direction):
        self.grid = grid
        self.locations = []
        self.launch_dir_idx = dir_array_to_idx(start_direction)
        self.cursor_direction = start_direction
        self.cursor_location = grid.human_location
        self.done = False
        self.all_locations_already_visited = True

    def __len__(self):
        return len(self.locations)

    def __repr__(self):
        return "<Path  of length {} now at {} pointing {}>".format(len(self), self.cursor_location, self.cursor_direction)

    def advance(self):
        # Return whether we're done.
        self.cursor_location = tuple(np.array(self.cursor_location) + self.cursor_direction)
        if not self.grid.location_inside(self.cursor_location):
            # We've hit the wall. This path is done.
            self.done = True
            return
        # print("Cursor at {}".format(self.cursor_location))
        self.all_locations_already_visited = self.all_locations_already_visited and self.grid.visited_locs[self.cursor_location]
        self.grid.visited_locs[self.cursor_location] = True
        terrain = self.grid.array[self.cursor_location]
        # print("Terrain is {}".format(terrain))
        if terrain == Terrain.UL or terrain == Terrain.UR:
            if terrain == Terrain.UL:
                # print("Hitting a UL mirror, flipping from {}".format(self.cursor_direction))
                self.cursor_direction = np.array((self.cursor_direction[1], self.cursor_direction[0]))
                # print("Now facing {}".format(self.cursor_direction))
            if terrain == Terrain.UR:
                # print("Hitting a UR mirror, flipping from {}".format(self.cursor_direction))
                self.cursor_direction = np.array((-self.cursor_direction[1], -self.cursor_direction[0]))
                # print("Now facing {}".format(self.cursor_direction))
            self.grid.flip_mirror(self.cursor_location)
        self.locations.append(self.cursor_location)

    def run(self):
        while not self.done:
            self.advance()
            if len(self) > MAX_PATH_LEN:
                self.done = True
        self.fillin_breakin_heuristic_grid()

    @property
    def contains_dups(self):
        # Untested in the positive case.
        assert self.done
        counter = Counter(self.locations)
        for k, v in counter.items():
            if v > 1 and self.grid.array[k] in (Terrain.UL, Terrain.UR):
                return True
        return False

    @property
    def short_path_score(self):
        final_valid_loc = self.locations[-1]
        first_loc = self.locations[0]
        manhattan_distance = np.sum(np.abs(np.array(final_valid_loc) - np.array(first_loc)))
        min_path_len = manhattan_distance + 1
        return 2. ** (- (len(self) - min_path_len))

    def fillin_breakin_heuristic_grid(self):
        end_side = ending_side(self.cursor_location)
        if end_side is None: return
        is_same_side = self.launch_dir_idx == end_side
        is_opposite_side = (self.launch_dir_idx - end_side) % 4 == 2
        is_perpendicular_side = (self.launch_dir_idx - end_side) % 2 == 1
        lands_in_middle = 2 in set(self.cursor_location)

        if len(self) == 2:
            for loc in self.locations:
                self.grid.breakin_heuristic_grid[loc] = True
        elif len(self) == 3:
            if is_perpendicular_side:
                for loc in self.locations:
                    self.grid.breakin_heuristic_grid[loc] = True
        elif len(self) == 4:
            if is_same_side and lands_in_middle:
                self.grid.breakin_heuristic_grid[self.locations[0]] = True
                self.grid.breakin_heuristic_grid[self.locations[3]] = True
            if is_perpendicular_side and lands_in_middle:
                self.grid.breakin_heuristic_grid[self.locations[0]] = True
        elif len(self) == 5:
            if is_same_side:
                self.grid.breakin_heuristic_grid[self.locations[0]] = True
                self.grid.breakin_heuristic_grid[self.locations[4]] = True
                # print(self.grid.breakin_heuristic_grid)
            elif is_opposite_side:
                for loc in self.locations:
                    self.grid.breakin_heuristic_grid[loc] = True
            elif is_perpendicular_side:
                pass
                # TODO
        elif len(self) == 6:
            if is_opposite_side and lands_in_middle:
                self.grid.breakin_heuristic_grid[self.locations[0]] = True
                self.grid.breakin_heuristic_grid[self.locations[1]] = True
                self.grid.breakin_heuristic_grid[self.locations[2]] = True
            if is_opposite_side and not lands_in_middle:
                self.grid.breakin_heuristic_grid[self.locations[0]] = True
    @property
    def heuristic_breakin_score(self):
        return np.sum(self.grid.breakin_heuristic_grid)

    def pretty_print_puzzle(self):
        result = ""

        len_str = str(len(self)).ljust(2)
        end_location = self.cursor_location
        if end_location[1] == -1:
            x_coord = end_location[0]
            result += "\n" + "   " + "  "*x_coord + len_str + "  "*(self.grid.size - x_coord - 1) +"   "
        result += "\n" + "  +" + "--" * self.grid.size + "+  "
        for i in range(self.grid.size):
            row_str = "|" + "  " * self.grid.size + "|"
            if i == 2:
                row_str = row_str[:5] + direction_str(self.launch_dir_idx)*2 + row_str[7:]
            left = len_str if end_location[0] == -1 and end_location[1] == i else "  "
            right = len_str if end_location[0] == self.grid.size and end_location[1] == i else "  "
            result += "\n" + left + row_str + right
        result += "\n" + "  +" + "--" * self.grid.size + "+  "
        if end_location[1] == 5:
            x_coord = end_location[0]
            result += "\n" + "   " + "  "*x_coord + str(len(self)).ljust(2) + "  "*(self.grid.size - x_coord - 1) +"   "
        return result

def run(num_grids, max_paths):
    # for i in range(len(ANSWER)):
    #     for f in os.listdir(os.path.join(OUTPUT_DIR, str(i))):
    #         os.remove(os.path.join(OUTPUT_DIR, str(i), f))
    for _ in range(num_grids):
        g = Grid()
        g.launch_lotsa_lasers(max_paths)
    print([len(x) for x in WORKING_GRIDS])

def direction_str(i):
    if i % 4 == 0: return "^"
    if i % 4 == 1: return ">"
    if i % 4 == 2: return "v"
    if i % 4 == 3: return "<"

run(10000, 12)

# g = Grid()
# g.display()
#
# # g.launch_laser()
# # g.launch_laser()
# # g.pretty_print_puzzle(2)
#
# g.launch_lotsa_lasers(10)
# g.pretty_print_puzzle(10)