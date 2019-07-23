import numpy as np
from collections import Counter
import os

MAX_PATH_LEN = 99

NORTH = np.array((0, -1))
SOUTH = np.array((0, 1))
EAST = np.array((1, 0))
WEST = np.array((-1, 0))
directions = [NORTH, EAST, SOUTH, WEST]

def dir_array_to_idx(dir_array):
    return [np.all(dir == dir_array) for dir in directions].index(True)

def ending_side(end_location):
    if end_location[0] == -1: return 3 # West
    if end_location[1] == -1: return 0 # North
    if end_location[0] == 5: return 1 # East
    if end_location[1] == 5: return 2 # South

def direction_str(i):
    if i % 4 == 0: return "^"
    if i % 4 == 1: return ">"
    if i % 4 == 2: return "v"
    if i % 4 == 3: return "<"

class BREAKIN_VALUE():
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

class Room():
    def __init__(self, size=5, mirror_prob=0.6):
        self.size = size
        self.array = np.array(
            [[Room._new_cell(mirror_prob)
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
        # Only called in __init__
        if np.random.random() > mirror_prob:
            return Terrain.FLAT
        else:
            return np.random.choice((Terrain.UL, Terrain.UR))

    def display(self):
        """
        Prints a pretty grid of the mirrors.
        """
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

    @property
    def heuristic_breakin_score(self):
        return np.sum(self.breakin_heuristic_grid)

    @property
    def heuristic_midgame_score(self):
        return len([p for p in self.paths if 5 < len(p) < 12])

    def launch_lotsa_lasers(self, max_lasers, valid_puzzle_found_callback=None,
                            only_extract_after_all_visited=True, min_heuristic_breakin_score=6, min_heuristic_midgame_score=4,
                            stop_after_complete=False):
        """

        :param max_lasers: launch up to this many lasers (but maybe stop early if valid_puzzle_found_callback() returns True).
        :param valid_puzzle_found_callback: a function which takes a Room and returns True if this is a valid final grid,
            and False otherwise. The room's `paths` list will contain the final (to-be-solved-for) path in the -1 slot.
            If None, no constraints will be applied.
        :param only_extract_after_all_visited: if True, we will only end the room if every cell in the grid has been visited by a path.
        :param min_heuristic_breakin_score: only accept rooms which have at least this many cells that can be determined
            entirely right at the start.
        :param stop_after_complete: If True, stop after finding a valid room.
        :return:
        """
        if valid_puzzle_found_callback is None:
            valid_puzzle_found_callback = lambda x: True
        for i in range(max_lasers):
            all_sites_visited_before_this_laser = self.all_sites_visited
            path = self.launch_laser()

            # Can't end the puzzle before all cells which are used in the final (unknown to solver) path
            # have been visited earlier in the puzzle
            if not path.all_locations_already_visited: continue
            # If only_extract_after_all_visited, we can't finish until all cells in the grid
            # have been visited earlier in the puzzle. (This is a stricter criterion than path.all_locations_already_visited)
            if only_extract_after_all_visited and not all_sites_visited_before_this_laser: continue
            # If the heuristic_breakin_score is less than min_heuristic_breakin_score, it won't be possible.
            if self.heuristic_breakin_score < min_heuristic_breakin_score: continue
            if self.heuristic_midgame_score < min_heuristic_midgame_score: continue

            valid_room_puzzle = valid_puzzle_found_callback(self)
            if valid_room_puzzle and stop_after_complete:
                return

    def pretty_print_puzzle(self):
        result = "="*16
        result += f"\nLasercats puzzle (easiness {self.heuristic_breakin_score})"
        for p in self.paths[:-1]:
            result += "\n\n"
            result += p.pretty_print_puzzle()
        return result

    def dump_puzzle(self, dir):
        name = "-".join([str(len(p)) for p in self.paths[:-1]]) + '.txt'
        name = f"H={self.heuristic_breakin_score}_" + name
        with open(os.path.join(dir, name), 'w') as f:
            f.write(self.pretty_print_puzzle())

class Path():
    def __init__(self, room, start_direction):
        self.room = room
        self.locations = []
        self.launch_dir_idx = dir_array_to_idx(start_direction)
        self.cursor_direction = start_direction
        self.cursor_location = room.human_location
        self.done = False
        self.all_locations_already_visited = True

    def __len__(self):
        return len(self.locations)

    def __repr__(self):
        return "<Path  of length {} now at {} pointing {}>".format(len(self), self.cursor_location, self.cursor_direction)

    def advance(self):
        # Return whether we're done.
        self.cursor_location = tuple(np.array(self.cursor_location) + self.cursor_direction)
        if not self.room.location_inside(self.cursor_location):
            # We've hit the wall. This path is done.
            self.done = True
            return
        # print("Cursor at {}".format(self.cursor_location))
        self.all_locations_already_visited = self.all_locations_already_visited and self.room.visited_locs[self.cursor_location]
        self.room.visited_locs[self.cursor_location] = True
        terrain = self.room.array[self.cursor_location]
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
            self.room.flip_mirror(self.cursor_location)
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
            if v > 1 and self.room.array[k] in (Terrain.UL, Terrain.UR):
                return True
        return False

    def fillin_breakin_heuristic_grid(self):
        end_side = ending_side(self.cursor_location)
        if end_side is None: return
        is_same_side = self.launch_dir_idx == end_side
        is_opposite_side = (self.launch_dir_idx - end_side) % 4 == 2
        is_perpendicular_side = (self.launch_dir_idx - end_side) % 2 == 1
        lands_in_middle = 2 in set(self.cursor_location)

        if len(self) == 2:
            for loc in self.locations:
                self.room.breakin_heuristic_grid[loc] = True
        elif len(self) == 3:
            if is_perpendicular_side:
                for loc in self.locations:
                    self.room.breakin_heuristic_grid[loc] = True
        elif len(self) == 4:
            if is_same_side and lands_in_middle:
                self.room.breakin_heuristic_grid[self.locations[0]] = True
                self.room.breakin_heuristic_grid[self.locations[3]] = True
            if is_perpendicular_side and lands_in_middle:
                self.room.breakin_heuristic_grid[self.locations[0]] = True
        elif len(self) == 5:
            if is_same_side:
                self.room.breakin_heuristic_grid[self.locations[0]] = True
                self.room.breakin_heuristic_grid[self.locations[4]] = True
                # print(self.room.breakin_heuristic_grid)
            elif is_opposite_side:
                for loc in self.locations:
                    self.room.breakin_heuristic_grid[loc] = True
            elif is_perpendicular_side:
                pass
                # TODO
        elif len(self) == 6:
            if is_opposite_side and lands_in_middle:
                self.room.breakin_heuristic_grid[self.locations[0]] = True
                self.room.breakin_heuristic_grid[self.locations[1]] = True
                self.room.breakin_heuristic_grid[self.locations[2]] = True
            if is_opposite_side and not lands_in_middle:
                self.room.breakin_heuristic_grid[self.locations[0]] = True

    def pretty_print_puzzle(self):
        result = ""
        len_str = '%02d' % len(self)
        end_location = self.cursor_location
        if end_location[1] == -1:
            x_coord = end_location[0]
            result += "\n" + "   " + "  "*x_coord + len_str + "  "*(self.room.size - x_coord - 1) +"   "
        result += "\n" + "  +" + "--" * self.room.size + "+  "
        for i in range(self.room.size):
            row_str = "|" + "  " * self.room.size + "|"
            if i == 2:
                row_str = row_str[:5] + direction_str(self.launch_dir_idx)*2 + row_str[7:]
            left = len_str if end_location[0] == -1 and end_location[1] == i else "  "
            right = len_str if end_location[0] == self.room.size and end_location[1] == i else "  "
            result += "\n" + left + row_str + right
        result += "\n" + "  +" + "--" * self.room.size + "+  "
        if end_location[1] == 5:
            x_coord = end_location[0]
            result += "\n" + "   " + "  "*x_coord + len_str + "  "*(self.room.size - x_coord - 1) +"   "
        return result
    
def make_room(max_paths, valid_puzzle_found_callback, min_difficulty=6, retry_until_successful=False):
    """
    Makes a room and runs it forwards. May or may not result in a valid puzzle.
    """
    r = Room()
    r.launch_lotsa_lasers(max_paths, valid_puzzle_found_callback, min_heuristic_breakin_score=min_difficulty)
    return r

def run_lots(num_rooms, max_paths, valid_puzzle_found_callback, min_difficulty=6):
    """
    valid_puzzle_found_callback has to include outputting the room somewhere, or the data will fall into a void.
    """
    for _ in range(num_rooms):
        make_room(max_paths, valid_puzzle_found_callback, min_difficulty=min_difficulty)
        
def make_puzzle(min_difficulty=8, max_paths=12, ntries=1000):
    done = False
    def valid_puzzle_found_callback(*args):
        nonlocal done
        done = True

    for _ in range(ntries):
        r = make_room(max_paths, valid_puzzle_found_callback, min_difficulty=min_difficulty)
        if done:
            return r
        else:
            print("Puzzle construction failed; trying again.")

if __name__ == "__main__":
    r = make_puzzle()
    print(r.pretty_print_puzzle())